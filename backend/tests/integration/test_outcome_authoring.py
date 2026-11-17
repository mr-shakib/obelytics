"""
Outcome authoring through the AI gateway: drafting COs, refining a statement, and
CO-PO mapping suggestions that must follow the K, CEP and CEA rules.

The model is the fake backend from tests/ai_fakes.py: each test says what it returns.
"""
import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.modules.ai.gateway import get_backend_factory
from app.modules.ai.models import AICall
from app.modules.audit.models import AuditLog
from app.modules.authoring.models import OutcomeSuggestion
from app.modules.curriculum.models import Course, CourseBloomDomain, Curriculum
from app.modules.obe.models import (
    COKPMapping,
    COPOMappingEntry,
    COPOMappingSet,
    CourseOutcome,
    CourseOutcomeBloomLevel,
    POKnowledgeProfile,
    ProgramOutcome,
)
from app.modules.org.models import Department, Program
from app.modules.ref_data.models import (
    BloomDomain,
    BloomLevel,
    ComplexActivity,
    ComplexProblem,
    CourseCategory,
    KnowledgeProfile,
)
from tests.ai_fakes import FakeBackend, use_fake_ai
from tests.conftest import TEST_ORG_ID

BASE = "/api/v1/authoring"
DRAFT_NEEDLE = "for the university course below"
REFINE_NEEDLE = "Improve this course outcome statement"
MAPPING_NEEDLE = "Suggest which program outcomes"


# ── Scenario ──────────────────────────────────────────────────────────────────

async def _scenario(db: AsyncSession) -> dict:
    """
    An Operating Systems course in the test organization with:
    - CO1 (C2, already mapped to K3) and CO2 (C6, no knowledge profiles yet),
    - PO1 (needs K3 or K4), PO3 (needs K5), PO9 (affective, no K), PO10 (no K).
    Codes of knowledge profiles and CEP/CEA carry a suffix: the test org is shared.
    """
    s = uuid.uuid4().hex[:6]
    dept = Department(organization_id=TEST_ORG_ID, name=f"Authoring Dept {s}", short_name=f"AD{s}")
    db.add(dept)
    await db.flush()
    program = Program(
        organization_id=TEST_ORG_ID, department_id=dept.id, title=f"Authoring Program {s}",
        acronym=f"AP{s}", program_type="UNDERGRADUATE", minimum_duration_semesters=8,
        total_credits=160, study_mode="FULL_TIME",
    )
    db.add(program)
    await db.flush()
    curriculum = Curriculum(organization_id=TEST_ORG_ID, program_id=program.id,
                            name=f"Authoring Curriculum {s}", code=f"AC{s}", effective_year=2026)
    category = CourseCategory(organization_id=TEST_ORG_ID, name=f"Authoring Core {s}")
    cognitive = BloomDomain(organization_id=TEST_ORG_ID, name=f"Cognitive {s}")
    affective = BloomDomain(organization_id=TEST_ORG_ID, name=f"Affective {s}")
    db.add_all([curriculum, category, cognitive, affective])
    await db.flush()

    course = Course(
        organization_id=TEST_ORG_ID, course_category_id=category.id, course_type="THEORY",
        code=f"OS{s}", title="Operating Systems", credits=3, theory_hours=3,
        description="Processes, CPU scheduling, memory management, file systems and deadlocks.",
    )
    db.add(course)
    await db.flush()
    db.add(CourseBloomDomain(course_id=course.id, bloom_domain_id=cognitive.id))

    levels = {}
    for order, (code, name) in enumerate([("C1", "Remember"), ("C2", "Understand"), ("C3", "Apply"),
                                          ("C4", "Analyze"), ("C5", "Evaluate"), ("C6", "Create")], 1):
        level = BloomLevel(organization_id=TEST_ORG_ID, bloom_domain_id=cognitive.id,
                           code=code, name=name, order_index=order)
        db.add(level)
        levels[code] = level
    db.add(BloomLevel(organization_id=TEST_ORG_ID, bloom_domain_id=affective.id,
                      code="A3", name="Valuing", order_index=3))

    kp = {n: KnowledgeProfile(organization_id=TEST_ORG_ID, code=f"K{n}-{s}",
                              description=f"Knowledge profile {n}") for n in (3, 4, 5)}
    cep = ComplexProblem(organization_id=TEST_ORG_ID, code=f"CEP1-{s}", name="Depth of knowledge",
                         description="Needs in-depth engineering knowledge")
    cea = ComplexActivity(organization_id=TEST_ORG_ID, code=f"CA1-{s}", name="Range of resources",
                          description="Uses diverse resources")
    db.add_all([*kp.values(), cep, cea])
    await db.flush()

    pos = {}
    for order, (code, domain) in enumerate([("PO1", None), ("PO3", None), ("PO9", affective.id),
                                            ("PO10", None)]):
        po = ProgramOutcome(organization_id=TEST_ORG_ID, program_id=program.id, code=code,
                            statement=f"Program outcome {code}", order_index=order,
                            bloom_domain_id=domain)
        db.add(po)
        pos[code] = po
    await db.flush()
    db.add_all([
        POKnowledgeProfile(program_outcome_id=pos["PO1"].id, knowledge_profile_id=kp[3].id),
        POKnowledgeProfile(program_outcome_id=pos["PO1"].id, knowledge_profile_id=kp[4].id),
        POKnowledgeProfile(program_outcome_id=pos["PO3"].id, knowledge_profile_id=kp[5].id),
    ])

    co1 = CourseOutcome(organization_id=TEST_ORG_ID, curriculum_id=curriculum.id, course_id=course.id,
                        code="CO1", statement="Explain how an operating system schedules processes.")
    co2 = CourseOutcome(organization_id=TEST_ORG_ID, curriculum_id=curriculum.id, course_id=course.id,
                        code="CO2", statement="Design a memory allocator for given workload constraints.")
    db.add_all([co1, co2])
    await db.flush()
    db.add_all([
        CourseOutcomeBloomLevel(course_outcome_id=co1.id, bloom_level_id=levels["C2"].id),
        CourseOutcomeBloomLevel(course_outcome_id=co2.id, bloom_level_id=levels["C6"].id),
        COKPMapping(organization_id=TEST_ORG_ID, course_outcome_id=co1.id,
                    knowledge_profile_id=kp[3].id, justification="Uses OS fundamentals."),
    ])
    await db.commit()
    return {
        "suffix": s,
        "curriculum_id": str(curriculum.id),
        "course_id": str(course.id),
        "co": {"CO1": co1.id, "CO2": co2.id},
        "po": {code: po.id for code, po in pos.items()},
        "kp": {n: k for n, k in kp.items()},
        "cep": cep,
        "cea": cea,
        "levels": levels,
    }


def _ids(s: dict) -> dict:
    return {"curriculum_id": s["curriculum_id"], "course_id": s["course_id"]}


# ── Drafting COs ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_draft_returns_checked_drafts_and_saves_nothing(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session)
    backend = use_fake_ai(FakeBackend(verdicts={DRAFT_NEEDLE: {"outcomes": [
        {"statement": "Students will be able to analyze page replacement algorithms for a given "
                      "memory reference string", "bloom_codes": ["C4"], "rationale": "Memory topics."},
        {"statement": "Understand deadlocks.", "bloom_codes": ["C2", "ZZ9"], "rationale": "Deadlocks."},
        {"statement": "Explain how the operating system schedules processes.", "bloom_codes": ["C2"],
         "rationale": "Scheduling."},
        {"statement": "", "bloom_codes": [], "rationale": "empty"},
    ]}}))

    resp = await client.post(f"{BASE}/course-outcomes/draft", headers=auth_headers,
                             json={**_ids(s), "count": 3, "instruction": "Focus on memory."})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["model"] == "fake-text" and body["prompt_version"] == "co-draft-v2"
    first, vague, repeat = body["outcomes"]
    assert first["statement"] == (
        "Analyze page replacement algorithms for a given memory reference string."
    )
    assert [b["code"] for b in first["bloom_levels"]] == ["C4"] and first["warnings"] == []
    assert [b["code"] for b in vague["bloom_levels"]] == ["C2"]  # unknown code dropped
    assert any("understand" in w for w in vague["warnings"])
    assert "Very similar to CO1." in repeat["warnings"]

    prompt = backend.prompts[0]
    assert "Write 3 course outcomes" in prompt and "Operating Systems" in prompt
    assert "Explain how an operating system schedules processes." in prompt  # existing CO
    assert "<teacher_request>Focus on memory.</teacher_request>" in prompt
    assert "A3" not in prompt.split("Bloom levels you may tag")[1].split("\n\n")[0]  # course domain only

    suggestion = await db_session.get(OutcomeSuggestion, uuid.UUID(body["suggestion_id"]))
    assert (suggestion.kind, suggestion.model) == ("CO_DRAFT", "fake-text")
    assert len(suggestion.result["outcomes"]) == 3
    calls = (await db_session.execute(select(AICall).where(
        AICall.feature == "authoring", AICall.purpose == "draft_course_outcomes"))).scalars().all()
    assert calls and calls[-1].prompt_version == "co-draft-v2"
    audit = (await db_session.execute(select(AuditLog).where(
        AuditLog.action == "AI_CO_DRAFTED", AuditLog.entity_id == uuid.UUID(s["course_id"])))).scalar_one()
    assert json.loads(audit.extra)["suggestion_id"] == body["suggestion_id"]
    co_count = await db_session.scalar(select(func.count()).select_from(CourseOutcome).where(
        CourseOutcome.course_id == uuid.UUID(s["course_id"])))
    assert co_count == 2


@pytest.mark.asyncio
async def test_teacher_records_a_decision_on_their_suggestion(
    client: AsyncClient, auth_headers: dict, teacher_auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session)
    use_fake_ai(FakeBackend(verdicts={DRAFT_NEEDLE: {"outcomes": [
        {"statement": "Analyze CPU scheduling algorithms using waiting and turnaround time.",
         "bloom_codes": ["C4"], "rationale": "Scheduling."},
    ]}}))
    draft = await client.post(f"{BASE}/course-outcomes/draft", headers=teacher_auth_headers,
                              json={**_ids(s), "count": 1})
    assert draft.status_code == 200, draft.text
    suggestion_id = draft.json()["suggestion_id"]

    other = await client.post(f"{BASE}/suggestions/{suggestion_id}/decision", headers=auth_headers,
                              json={"decision": "REJECTED"})
    assert other.status_code == 404  # only the teacher who asked records the outcome

    resp = await client.post(f"{BASE}/suggestions/{suggestion_id}/decision", headers=teacher_auth_headers,
                             json={"decision": "EDITED", "detail": {"accepted": [0], "edited": [0]}})
    assert resp.status_code == 200, resp.text
    suggestion = await db_session.get(OutcomeSuggestion, uuid.UUID(suggestion_id))
    await db_session.refresh(suggestion)
    assert suggestion.decision == "EDITED" and suggestion.decision_detail == {"accepted": [0], "edited": [0]}


# ── Refining a CO ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refine_returns_an_improved_statement_with_both_sets_of_warnings(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session)
    backend = use_fake_ai(FakeBackend(verdicts={REFINE_NEEDLE: {
        "statement": "Explain the role of the CPU scheduler in a multiprogramming operating system",
        "bloom_codes": ["C2"],
        "changes": ["Replaced the vague verb 'understand' with 'explain'.", ""],
    }}))
    resp = await client.post(f"{BASE}/course-outcomes/refine", headers=auth_headers, json={
        **_ids(s), "statement": "Understand scheduler",
        "bloom_level_ids": [str(s["levels"]["C2"].id)],
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["statement"].endswith("operating system.")
    assert [b["code"] for b in body["bloom_levels"]] == ["C2"]
    assert body["changes"] == ["Replaced the vague verb 'understand' with 'explain'."]
    assert any("understand" in w for w in body["original_warnings"])
    assert not any("understand" in w for w in body["warnings"])
    assert "<statement>Understand scheduler</statement>" in backend.prompts[0]
    assert "currently tagged: C2" in backend.prompts[0]


@pytest.mark.asyncio
async def test_unavailable_ai_and_model_failures(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session)
    payload = {**_ids(s), "statement": "Explain paging in virtual memory systems."}

    app.dependency_overrides[get_backend_factory] = lambda: (lambda provider: None)
    resp = await client.post(f"{BASE}/course-outcomes/refine", headers=auth_headers, json=payload)
    assert resp.status_code == 503 and "not configured" in resp.json()["detail"]

    use_fake_ai(FakeBackend(fail=True))
    resp = await client.post(f"{BASE}/course-outcomes/refine", headers=auth_headers, json=payload)
    assert resp.status_code == 502
    error = (await db_session.execute(select(AICall).where(
        AICall.feature == "authoring", AICall.status == "ERROR"
    ).order_by(AICall.created_at.desc()))).scalars().first()
    assert error is not None and "offline" in error.error


# ── CO-PO mapping suggestions ─────────────────────────────────────────────────

def _mapping_reply(s: dict) -> dict:
    sx = s["suffix"]

    def link(co, po, weight=3, kps=(), ceps=(), ceas=(), why="Clear link."):
        return {
            "co": co, "po": po, "weight": weight, "justification": why, "confidence": 0.8,
            "knowledge_profiles": [{"code": f"K{n}-{sx}", "justification": f"Uses K{n}."} for n in kps],
            "complex_problems": [{"code": f"CEP{n}-{sx}", "justification": "Open-ended."} for n in ceps],
            "complex_activities": [{"code": f"CA{n}-{sx}", "justification": "Many tools."} for n in ceas],
        }

    return {"mappings": [
        link("CO1", "PO1", kps=[4], ceps=[1]),        # CO1 already has K3: nothing to add for K
        link("CO2", "PO3", kps=[5], ceps=[1]),        # adds K5 and CEP1
        link("CO2", "PO1", weight=2, kps=[5], ceps=[1]),  # K5 is not one of PO1's: K rule broken
        link("CO1", "PO10"),                          # no CEA named: CEA rule broken
        link("CO1", "PO9", weight=1),                 # affective PO, cognitive CO: a warning only
        link("CO9", "PO1"),                           # unknown CO: dropped
        link("CO1", "PO1", weight=1),                 # duplicate: dropped
    ]}


@pytest.mark.asyncio
async def test_mapping_suggestions_are_checked_against_the_rules(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session)
    backend = use_fake_ai(FakeBackend(verdicts={MAPPING_NEEDLE: _mapping_reply(s)}))
    resp = await client.post(f"{BASE}/co-po/suggest", headers=auth_headers, json=_ids(s))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    links = {(link["co_code"], link["po_code"]): link for link in body["links"]}
    assert list(links) == [("CO1", "PO1"), ("CO1", "PO9"), ("CO1", "PO10"), ("CO2", "PO1"), ("CO2", "PO3")]
    assert [link["index"] for link in body["links"]] == [0, 1, 2, 3, 4]

    co1_po1 = links[("CO1", "PO1")]
    assert co1_po1["can_apply"] and co1_po1["weight"] == 3
    assert [(k["code"], k["already_mapped"]) for k in co1_po1["knowledge_profiles"]] == [
        (f"K3-{s['suffix']}", True)]
    assert [(c["code"], c["already_mapped"]) for c in co1_po1["complex_problems"]] == [
        (f"CEP1-{s['suffix']}", False)]

    co2_po3 = links[("CO2", "PO3")]
    assert co2_po3["can_apply"]
    assert [(k["code"], k["already_mapped"]) for k in co2_po3["knowledge_profiles"]] == [
        (f"K5-{s['suffix']}", False)]

    co2_po1 = links[("CO2", "PO1")]
    assert not co2_po1["can_apply"] and co2_po1["knowledge_profiles"] == []
    assert co2_po1["issues"][0].startswith("K rule: PO1 needs one of")

    co1_po10 = links[("CO1", "PO10")]
    assert not co1_po10["can_apply"] and co1_po10["issues"][0].startswith("CEA rule")

    co1_po9 = links[("CO1", "PO9")]
    assert co1_po9["can_apply"] and "Affective" in co1_po9["warnings"][0]

    assert body["pos_without_knowledge_profiles"] == ["PO9", "PO10"]
    prompt = backend.prompts[0]
    assert f"Required knowledge profiles: K3-{s['suffix']}, K4-{s['suffix']}" in prompt
    assert f"Already mapped to: K3-{s['suffix']}" in prompt


@pytest.mark.asyncio
async def test_applying_suggestions_adds_links_and_the_mappings_they_need(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session)
    use_fake_ai(FakeBackend(verdicts={MAPPING_NEEDLE: _mapping_reply(s)}))
    body = (await client.post(f"{BASE}/co-po/suggest", headers=auth_headers, json=_ids(s))).json()
    index = {(link["co_code"], link["po_code"]): link["index"] for link in body["links"]}
    apply_url = f"{BASE}/co-po/suggestions/{body['suggestion_id']}/apply"

    broken = await client.post(apply_url, headers=auth_headers,
                               json={"items": [{"index": index[("CO2", "PO1")]}]})
    assert broken.status_code == 422 and "CO2 → PO1 needs one of" in broken.json()["detail"]

    resp = await client.post(apply_url, headers=auth_headers, json={"items": [
        {"index": index[("CO1", "PO1")]},
        {"index": index[("CO2", "PO3")], "weight": 2, "justification": "CO2's design work is PO3."},
    ]})
    assert resp.status_code == 200, resp.text
    applied = resp.json()
    assert applied["applied"] == [index[("CO1", "PO1")], index[("CO2", "PO3")]]
    assert (applied["added_knowledge_profiles"], applied["added_complex_problems"]) == (1, 2)

    entries = (await db_session.execute(select(COPOMappingEntry).join(COPOMappingSet).where(
        COPOMappingSet.course_id == uuid.UUID(s["course_id"])))).scalars().all()
    weights = {(e.course_outcome_id, e.program_outcome_id): (e.weight, e.justification) for e in entries}
    assert weights[(s["co"]["CO1"], s["po"]["PO1"])] == (3, "Clear link.")
    assert weights[(s["co"]["CO2"], s["po"]["PO3"])] == (2, "CO2's design work is PO3.")
    kp = (await db_session.execute(select(COKPMapping).where(
        COKPMapping.course_outcome_id == s["co"]["CO2"]))).scalar_one()
    assert kp.knowledge_profile_id == s["kp"][5].id and kp.justification == "Uses K5."

    validation = await client.get(f"/api/v1/mappings/co-po/{applied['mapping_set_id']}/validate",
                                  headers=auth_headers)
    assert validation.json() == {"is_valid": True, "issues": []}

    again = await client.post(apply_url, headers=auth_headers,
                              json={"items": [{"index": index[("CO1", "PO1")]}]})
    assert again.status_code == 200 and again.json()["already_mapped"] == [index[("CO1", "PO1")]]

    suggestion = await db_session.get(OutcomeSuggestion, uuid.UUID(body["suggestion_id"]))
    await db_session.refresh(suggestion)
    assert suggestion.decision == "EDITED"
    assert suggestion.decision_detail["edited"] == [index[("CO2", "PO3")]]
    audit = (await db_session.execute(select(AuditLog).where(
        AuditLog.action == "AI_CO_PO_APPLIED",
        AuditLog.entity_id == uuid.UUID(applied["mapping_set_id"])))).scalars().first()
    assert json.loads(audit.extra)["suggestion_id"] == body["suggestion_id"]


@pytest.mark.asyncio
async def test_validator_reports_knowledge_profile_gaps(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session)
    mapping_set = COPOMappingSet(organization_id=TEST_ORG_ID, curriculum_id=uuid.UUID(s["curriculum_id"]),
                                 course_id=uuid.UUID(s["course_id"]))
    db_session.add(mapping_set)
    await db_session.flush()
    db_session.add_all([
        COPOMappingEntry(mapping_set_id=mapping_set.id, course_outcome_id=s["co"]["CO2"],
                         program_outcome_id=s["po"]["PO3"], weight=3, justification="Design."),
        COPOMappingEntry(mapping_set_id=mapping_set.id, course_outcome_id=s["co"]["CO1"],
                         program_outcome_id=s["po"]["PO9"], weight=1, justification="Values."),
    ])
    await db_session.commit()

    resp = await client.get(f"/api/v1/mappings/co-po/{mapping_set.id}/validate", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_valid"] is False
    [issue] = body["issues"]
    assert issue["course_outcome_code"] == "CO2" and issue["missing_cep"] is True
    assert issue["missing_kp"] == [{
        "program_outcome_id": str(s["po"]["PO3"]), "program_outcome_code": "PO3",
        "required_kp_codes": [f"K5-{s['suffix']}"],
    }]


@pytest.mark.asyncio
async def test_section_teacher_cannot_change_mappings_with_ai(
    client: AsyncClient, teacher_auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session)
    use_fake_ai(FakeBackend(verdicts={MAPPING_NEEDLE: _mapping_reply(s)}))
    resp = await client.post(f"{BASE}/co-po/suggest", headers=teacher_auth_headers, json=_ids(s))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_course_from_another_organization_is_not_found(
    client: AsyncClient, auth_headers: dict
):
    use_fake_ai(FakeBackend())
    resp = await client.post(f"{BASE}/course-outcomes/draft", headers=auth_headers, json={
        "curriculum_id": str(uuid.uuid4()), "course_id": str(uuid.uuid4()),
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_suggestions_for_one_new_co_leave_the_others_alone(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session)
    backend = use_fake_ai(FakeBackend(verdicts={MAPPING_NEEDLE: _mapping_reply(s)}))
    resp = await client.post(f"{BASE}/co-po/suggest", headers=auth_headers, json={
        **_ids(s), "course_outcome_ids": [str(s["co"]["CO2"])],
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["course_outcome_codes"] == ["CO2"]
    assert {link["co_code"] for link in body["links"]} == {"CO2"}  # CO1 links from the model dropped

    prompt = backend.prompts[0]
    assert "Suggest which program outcomes CO2 of this course should map to" in prompt
    assert "Design a memory allocator" in prompt
    assert "Explain how an operating system schedules processes." not in prompt

    suggestion = await db_session.get(OutcomeSuggestion, uuid.UUID(body["suggestion_id"]))
    assert suggestion.request == {"course_outcome_ids": [str(s["co"]["CO2"])]}

    other = await client.post(f"{BASE}/co-po/suggest", headers=auth_headers, json={
        **_ids(s), "course_outcome_ids": [str(uuid.uuid4())],
    })
    assert other.status_code == 422 and "not part of this course" in other.json()["detail"]


# ── Course outline import ─────────────────────────────────────────────────────

OUTLINE_NEEDLE = "text of a university course outline"


def _outline_docx(lines: list[str]) -> bytes:
    import io
    import zipfile
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    body = "".join(f'<w:p><w:r><w:t xml:space="preserve">{line}</w:t></w:r></w:p>' for line in lines)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", f"<w:document {ns}><w:body>{body}</w:body></w:document>")
    return buffer.getvalue()


OUTLINE_LINES = [
    "Course Outline — OS101 Operating Systems",
    "Rationale: This course covers how operating systems manage processes, memory and storage, "
    "and how to reason about their performance and correctness in practice.",
    "Course Objectives: Introduce process and memory management. Develop skills to analyze "
    "scheduling and synchronization.",
    "Course Outcomes:",
    "CO1 Explain how an operating system schedules processes. (C2)",
    "CO3 Analyze deadlock conditions in a given resource allocation graph. (C4)",
    "CO4 Implement a page replacement algorithm and compare its fault rate. (C3)",
    "Week 1: Introduction and system calls. Week 2: Processes and threads. Week 3: CPU scheduling. "
    "Week 4: Synchronization. Week 5: Deadlocks. Week 6: Memory management and paging.",
]


def _outline_reply(s: dict) -> dict:
    return {
        "course_code": "OS101",
        "course_title": "Operating Systems",
        "description": "This course covers how operating systems manage processes, memory and storage.",
        "objectives": ["Introduce process and memory management.",
                       "Develop skills to analyze scheduling and synchronization."],
        "outcomes": [
            {"code": "CO1", "statement": "Explain how an operating system schedules processes.",
             "bloom_codes": ["C2"], "bloom_stated": True},
            {"code": "CO3", "statement": "Analyze deadlock conditions in a given resource allocation graph.",
             "bloom_codes": ["C4"], "bloom_stated": True},
            {"code": "CO 4", "statement": "Students will be able to implement a page replacement algorithm "
                                          "and evaluate its performance on real workloads",
             "bloom_codes": ["C3"], "bloom_stated": False},
        ],
        "topics": [{"week": 1, "topic": "Introduction and system calls"},
                   {"week": 2, "topic": "Processes and threads"},
                   {"week": None, "topic": "CPU scheduling"}],
    }


@pytest.mark.asyncio
async def test_outline_import_previews_then_applies_without_touching_existing_cos(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session)
    backend = use_fake_ai(FakeBackend(verdicts={OUTLINE_NEEDLE: _outline_reply(s)}))
    resp = await client.post(
        f"{BASE}/course-outline/read", headers=auth_headers,
        data=_ids(s),
        files={"file": ("os-outline.docx", _outline_docx(OUTLINE_LINES),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert resp.status_code == 200, resp.text
    preview = resp.json()
    assert preview["prompt_version"] == "outline-v1" and preview["filename"] == "os-outline.docx"
    assert "<outline>" in backend.prompts[0] and "CO3 Analyze deadlock" in backend.prompts[0]
    outcomes = {o["code"]: o for o in preview["outcomes"]}
    assert set(outcomes) == {"CO1", "CO3", "CO4"}  # "CO 4" normalised
    assert outcomes["CO1"]["exists"] is True and "will not be changed" in outcomes["CO1"]["warnings"][0]
    assert outcomes["CO3"]["exists"] is False and outcomes["CO3"]["warnings"] == []
    assert outcomes["CO4"]["statement"].startswith("Implement a page replacement")
    assert any("word for word" in w for w in outcomes["CO4"]["warnings"])  # the model changed it
    assert any("chose this one" in w for w in outcomes["CO4"]["warnings"])
    assert "The outline is for OS101" in preview["warnings"][0]
    assert preview["current"]["outcome_codes"] == ["CO1", "CO2"]

    applied = await client.post(
        f"{BASE}/course-outline/suggestions/{preview['suggestion_id']}/apply", headers=auth_headers,
        json={
            "description": preview["description"],
            "objectives": preview["objectives"],
            "outcomes": [{"code": o["code"], "statement": o["statement"],
                          "bloom_level_ids": [b["id"] for b in o["bloom_levels"]]}
                         for o in preview["outcomes"]],
            "topics": preview["topics"],
        },
    )
    assert applied.status_code == 200, applied.text
    result = applied.json()
    assert result["outcomes_added"] == ["CO3", "CO4"] and result["outcomes_skipped"] == ["CO1"]
    assert (result["objectives"], result["lesson_items"], result["description"]) == (2, 3, True)

    course_id = uuid.UUID(s["course_id"])
    cos = (await db_session.execute(select(CourseOutcome).where(
        CourseOutcome.course_id == course_id).order_by(CourseOutcome.code))).scalars().all()
    assert [co.code for co in cos] == ["CO1", "CO2", "CO3", "CO4"]
    assert cos[0].statement == "Explain how an operating system schedules processes."  # unchanged
    course = await db_session.get(Course, course_id)
    await db_session.refresh(course)
    assert course.syllabus_content.startswith("1. Introduction and system calls")
    suggestion = await db_session.get(OutcomeSuggestion, uuid.UUID(preview["suggestion_id"]))
    await db_session.refresh(suggestion)
    assert suggestion.kind == "OUTLINE_IMPORT" and suggestion.decision == "ACCEPTED"
    assert len(suggestion.request["sha256"]) == 64


@pytest.mark.asyncio
async def test_outline_import_rejects_unreadable_files(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session)
    use_fake_ai(FakeBackend())
    resp = await client.post(f"{BASE}/course-outline/read", headers=auth_headers, data=_ids(s),
                             files={"file": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 422 and "Word" in resp.json()["detail"]
    resp = await client.post(f"{BASE}/course-outline/read", headers=auth_headers, data=_ids(s),
                             files={"file": ("short.docx", _outline_docx(["Too short."]),
                                             "application/vnd.openxmlformats-officedocument."
                                             "wordprocessingml.document")})
    assert resp.status_code == 422
