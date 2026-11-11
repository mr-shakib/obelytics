"""Integration tests for the integrity auditor.

Covers reading a question paper, saving question wording, running the audit
and reviewing its judgments. The AI backend is replaced by a fake and jobs run
synchronously, so these tests need no model server and no worker.
"""
import io
import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assessment.models import MarksheetQuestion
from app.modules.curriculum.models import (
    AcademicTerm,
    Batch,
    Course,
    Curriculum,
    FacultyAssignment,
    Section,
    SectionOffering,
)
from app.modules.iam.models import User
from app.modules.integrity.auditing import judge_alignment
from app.modules.integrity.documents import normalize_label
from app.modules.integrity.models import QuestionAudit, QuestionPaper
from app.modules.integrity.reading import fold_stems as _fold_stems
from app.modules.integrity.reading import repair_latex as _repair_latex
from app.modules.obe.models import CourseOutcome
from app.modules.org.models import Department, Program
from app.modules.ref_data.models import BloomDomain, BloomLevel, CourseCategory
from tests.ai_fakes import FakeBackend, use_fake_ai
from tests.ai_fakes import verdict as _verdict
from tests.conftest import TEST_ORG_ID, TEST_TEACHER_EMAIL

BASE = "/api/v1/integrity"


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (40, 60), "white").save(buffer, format="PNG")
    return buffer.getvalue()


# ── Scenario builder ──────────────────────────────────────────────────────────

async def _cognitive_levels(db: AsyncSession) -> dict[str, uuid.UUID]:
    """C1–C6 in the test organization's shared Cognitive domain."""
    domain = (await db.execute(select(BloomDomain).where(
        BloomDomain.organization_id == TEST_ORG_ID, BloomDomain.name == "Cognitive"
    ))).scalar_one_or_none()
    if domain is None:
        domain = BloomDomain(organization_id=TEST_ORG_ID, name="Cognitive")
        db.add(domain)
        await db.flush()
    levels = {}
    for order, (code, name) in enumerate([("C1", "Remember"), ("C2", "Understand"), ("C3", "Apply"),
                                          ("C4", "Analyze"), ("C5", "Evaluate"), ("C6", "Create")], 1):
        level = (await db.execute(select(BloomLevel).where(
            BloomLevel.bloom_domain_id == domain.id, BloomLevel.code == code
        ))).scalar_one_or_none()
        if level is None:
            level = BloomLevel(organization_id=TEST_ORG_ID, bloom_domain_id=domain.id,
                               code=code, name=name, order_index=order)
            db.add(level)
            await db.flush()
        levels[code] = level.id
    return levels


async def _scenario(db: AsyncSession, questions: list[tuple[str, str, str]]) -> dict:
    """A section offering in the test org with CO1, CO2 and FINAL questions (label, CO, Bloom)."""
    suffix = uuid.uuid4().hex[:8]
    full = int(uuid.uuid4().hex, 16)
    levels = await _cognitive_levels(db)

    dept = Department(organization_id=TEST_ORG_ID, name=f"IA Dept {suffix}", short_name=f"IA{suffix}")
    db.add(dept)
    await db.flush()
    program = Program(
        organization_id=TEST_ORG_ID, department_id=dept.id, title=f"IA Program {suffix}",
        acronym=f"IAP{suffix}", program_type="UNDERGRADUATE", minimum_duration_semesters=8,
        total_credits=136, study_mode="FULL_TIME",
    )
    db.add(program)
    await db.flush()
    curriculum = Curriculum(organization_id=TEST_ORG_ID, program_id=program.id,
                            name=f"IA Curriculum {suffix}", code=f"IAC{suffix}", effective_year=2026)
    category = CourseCategory(organization_id=TEST_ORG_ID, name=f"IA Theory {suffix}")
    db.add_all([curriculum, category])
    await db.flush()
    course = Course(organization_id=TEST_ORG_ID, course_category_id=category.id, course_type="THEORY",
                    code=f"NM{suffix}", title="Numerical Methods", credits=3)
    batch = Batch(organization_id=TEST_ORG_ID, curriculum_id=curriculum.id, name=f"Batch {suffix}")
    term = AcademicTerm(
        organization_id=TEST_ORG_ID, name=f"Term {suffix}", year=5000 + (full % 900),
        season=["FALL", "SPRING", "SUMMER", "WINTER"][(full >> 32) % 4],
        start_date=date(2026, 5, 1), end_date=date(2026, 8, 31),
    )
    section = Section(organization_id=TEST_ORG_ID, name=f"IA{suffix}")
    db.add_all([course, batch, term, section])
    await db.flush()
    offering = SectionOffering(
        organization_id=TEST_ORG_ID, curriculum_id=curriculum.id, batch_id=batch.id,
        course_id=course.id, academic_term_id=term.id, section_id=section.id,
    )
    co1 = CourseOutcome(organization_id=TEST_ORG_ID, curriculum_id=curriculum.id, course_id=course.id,
                        code="CO1", statement="Solve linear systems and ODEs with iterative methods.")
    co2 = CourseOutcome(organization_id=TEST_ORG_ID, curriculum_id=curriculum.id, course_id=course.id,
                        code="CO2", statement="Fit curves to data and integrate numerically.")
    db.add_all([offering, co1, co2])
    await db.flush()
    cos = {"CO1": co1.id, "CO2": co2.id}
    question_ids = {}
    for order, (label, co, bloom) in enumerate(questions):
        question = MarksheetQuestion(
            organization_id=TEST_ORG_ID, section_offering_id=offering.id, exam_type="FINAL",
            label=label, max_marks=Decimal("5"), course_outcome_id=cos[co],
            declared_bloom_level_id=levels[bloom], order_index=order,
        )
        db.add(question)
        await db.flush()
        question_ids[label] = question.id
    await db.commit()
    return {"offering_id": offering.id, "question_ids": question_ids, "levels": levels,
            "batch_id": batch.id, "program_id": program.id, "cos": cos}


async def _save_texts(client, headers, offering_id, texts: dict[uuid.UUID, str]):
    return await client.put(
        f"{BASE}/sections/{offering_id}/question-texts", params={"exam_type": "FINAL"},
        json={"items": [{"question_id": str(qid), "question_text": text} for qid, text in texts.items()]},
        headers=headers,
    )


# ── Pure helpers ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize(("ai_bloom", "declared_bloom", "ai_co", "declared_co", "confidence", "expected"), [
    ("C3", "C3", "a", "a", 0.9, "ALIGNED"),
    ("C3", "C6", "a", "a", 0.9, "PARTIAL"),
    ("C3", "C3", "b", "a", 0.9, "MISALIGNED"),
    ("C3", "C3", None, "a", 0.9, "MISALIGNED"),
    ("C3", "C3", "a", "a", 0.3, "ABSTAINED"),
    (None, "C3", "a", "a", 0.9, "ABSTAINED"),
    ("C4", None, "a", None, 0.9, "ALIGNED"),
])
def test_judge_alignment(ai_bloom, declared_bloom, ai_co, declared_co, confidence, expected):
    assert judge_alignment(
        abstain=False, confidence=confidence, ai_bloom_code=ai_bloom,
        declared_bloom_code=declared_bloom, ai_co_id=ai_co, declared_co_id=declared_co,
    ) == expected


def test_judge_alignment_respects_model_abstaining():
    assert judge_alignment(abstain=True, confidence=0.99, ai_bloom_code="C3", declared_bloom_code="C3",
                           ai_co_id="a", declared_co_id="a") == "ABSTAINED"


@pytest.mark.parametrize("label", ["Q1(a)", "1 (a)", "1.a", "q1a", "Question 1a", "1(A)"])
def test_normalize_label(label):
    assert normalize_label(label) == "1a"


def test_latex_broken_by_json_escapes_is_repaired():
    # "\frac" and "\times" written with one backslash decode to form feed and tab.
    assert _repair_latex("$\frac{dy}{dx} = 2 \times y$\n\nNext line") == (
        "$\\frac{dy}{dx} = 2 \\times y$\n\nNext line"
    )


def _q(label, text, context=None, figure=None):
    return {"label": label, "text": text, "context": context, "marks": None, "co": None,
            "figure": figure}


def test_shared_scenario_is_folded_into_its_parts():
    folded = _fold_stems([
        _q("1", "A campus cart service charges points.", figure="campus graph"),
        _q("1(a)", "Classify the graph."),
        _q("1(b)", "Construct the adjacency matrix.", context="Own context."),
        _q("10", "A standalone question."),
        _q("2", "Another standalone question."),
    ])
    assert [q["label"] for q in folded] == ["1(a)", "1(b)", "10", "2"]
    assert folded[0]["context"] == "A campus cart service charges points."
    assert folded[0]["figure"] == "campus graph"
    assert folded[1]["context"] == "Own context."


# ── Reading the paper ─────────────────────────────────────────────────────────

async def test_upload_reads_paper_and_matches_marksheet_labels(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1a", "CO1", "C3"), ("Q1b", "CO1", "C3"), ("Q3", "CO2", "C3")])
    use_fake_ai(FakeBackend(pages=[{"questions": [
        {"label": "1(a)", "text": "Apply Gauss-Seidel to the system.", "context": None,
         "marks": 6, "co": "CO1", "figure": None},
        {"label": "1(b)", "text": "Identify the local maximum.", "context": "Given the table below.",
         "marks": 4, "co": "CO1", "figure": "x/y table"},
        {"label": "2", "text": "Apply Runge-Kutta.", "context": None, "marks": 10, "co": None, "figure": None},
        {"label": "", "text": "dropped: no label", "context": None, "marks": None, "co": None, "figure": None},
    ]}]))

    resp = await client.post(
        f"{BASE}/sections/{s['offering_id']}/paper", params={"exam_type": "FINAL"},
        files={"file": ("paper.png", _png(), "image/png")}, headers=auth_headers,
    )

    assert resp.status_code == 202, resp.text
    assert resp.json()["job"]["status"] == "DONE"
    assert resp.json()["job"]["progress_done"] == 1
    paper = resp.json()["paper"]
    assert paper["extraction_status"] == "EXTRACTED"
    assert paper["extraction_method"] == "VISION"
    assert paper["extraction_model"] == "fake-vision"
    assert paper["page_count"] == 1
    matched = {q["label"]: q["matched_question_id"] for q in paper["questions"]}
    assert matched == {
        "1(a)": str(s["question_ids"]["Q1a"]),
        "1(b)": str(s["question_ids"]["Q1b"]),
        "2": None,
    }
    stored = (await db_session.execute(select(QuestionPaper).where(
        QuestionPaper.section_offering_id == s["offering_id"]
    ))).scalar_one()
    assert len(stored.file_sha256) == 64
    assert "1(a). Apply Gauss-Seidel" in stored.extracted_text


async def test_upload_rejects_unsupported_file_type(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    use_fake_ai(FakeBackend())
    resp = await client.post(
        f"{BASE}/sections/{s['offering_id']}/paper", params={"exam_type": "FINAL"},
        files={"file": ("paper.txt", b"hello", "text/plain")}, headers=auth_headers,
    )
    assert resp.status_code == 415


async def test_upload_records_failure_when_model_is_unavailable(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    use_fake_ai(FakeBackend(fail=True))
    resp = await client.post(
        f"{BASE}/sections/{s['offering_id']}/paper", params={"exam_type": "FINAL"},
        files={"file": ("paper.png", _png(), "image/png")}, headers=auth_headers,
    )
    assert resp.status_code == 202
    job = resp.json()["job"]
    assert (job["kind"], job["status"]) == ("READ_PAPER", "FAILED")
    assert "offline" in job["error"]
    stored = (await db_session.execute(select(QuestionPaper).where(
        QuestionPaper.section_offering_id == s["offering_id"]
    ).execution_options(populate_existing=True))).scalar_one()
    assert stored.extraction_status == "FAILED"
    assert "offline" in stored.extraction_error


# ── Auditing ──────────────────────────────────────────────────────────────────

async def test_audit_compares_ai_judgment_with_declared_mapping(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [
        ("Q1", "CO1", "C3"), ("Q2", "CO1", "C6"), ("Q3", "CO1", "C3"), ("Q4", "CO2", "C3"),
    ])
    ids = s["question_ids"]
    assert (await _save_texts(client, auth_headers, s["offering_id"], {
        ids["Q1"]: "Apply Gauss-Seidel iteration.",
        ids["Q2"]: "Develop the second degree polynomial by least squares.",
        ids["Q3"]: "Evaluate the integral with Simpson's rule.",
        ids["Q4"]: "Something vague.",
    })).status_code == 200
    provider = use_fake_ai(FakeBackend(verdicts={
        "Gauss-Seidel": _verdict("C3", "CO1"),
        "Develop": _verdict("C3", "CO2"),
        "Simpson": _verdict("C3", "CO2"),
        "vague": _verdict("C2", "CO2", confidence=0.2),
    }))

    resp = await client.post(f"{BASE}/sections/{s['offering_id']}/audit",
                             params={"exam_type": "FINAL"}, headers=auth_headers)

    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["job"]["status"] == "DONE"
    assert body["job"]["result"]["audited"] == 4
    alignment = {q["label"]: q["audit"]["alignment"] for q in body["questions"]}
    assert alignment == {"Q1": "ALIGNED", "Q2": "MISALIGNED", "Q3": "MISALIGNED", "Q4": "ABSTAINED"}
    q1 = next(q for q in body["questions"] if q["label"] == "Q1")
    assert q1["audit"]["ai_bloom_level"]["code"] == "C3"
    assert q1["audit"]["prompt_version"] == "audit-v3"
    assert (q1["audit"]["samples"], q1["audit"]["agreement"]) == (3, 1.0)
    q4 = next(q for q in body["questions"] if q["label"] == "Q4")
    assert q4["audit"]["ai_bloom_level"] is None  # abstained judgments are not stored
    summary = body["summary"]
    assert (summary["aligned"], summary["misaligned"], summary["abstained"]) == (1, 2, 1)
    assert summary["pending_review"] == 4
    # The teacher's declared level is never shown to the model.
    q2_prompt = next(p for p in provider.prompts if "Develop" in p)
    assert "Declared" not in q2_prompt and "declared" not in q2_prompt


async def test_bloom_only_difference_is_partial(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO2", "C6")])
    await _save_texts(client, auth_headers, s["offering_id"],
                      {s["question_ids"]["Q1"]: "Develop the polynomial by least squares."})
    use_fake_ai(FakeBackend(verdicts={"Develop": _verdict("C3", "CO2")}))
    resp = await client.post(f"{BASE}/sections/{s['offering_id']}/audit",
                             params={"exam_type": "FINAL"}, headers=auth_headers)
    assert resp.json()["questions"][0]["audit"]["alignment"] == "PARTIAL"


async def test_rerunning_audit_keeps_history_with_one_current_row(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    qid = s["question_ids"]["Q1"]
    await _save_texts(client, auth_headers, s["offering_id"], {qid: "Apply Gauss-Seidel iteration."})
    use_fake_ai(FakeBackend(verdicts={"Gauss-Seidel": _verdict("C3", "CO1")}))
    for _ in range(2):
        resp = await client.post(f"{BASE}/sections/{s['offering_id']}/audit",
                                 params={"exam_type": "FINAL"}, headers=auth_headers)
        assert resp.status_code == 202

    total = await db_session.scalar(select(func.count()).where(QuestionAudit.question_id == qid))
    current = await db_session.scalar(select(func.count()).where(
        QuestionAudit.question_id == qid, QuestionAudit.is_current.is_(True)
    ))
    assert (total, current) == (2, 1)


async def test_editing_question_text_retires_the_current_audit(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    qid = s["question_ids"]["Q1"]
    await _save_texts(client, auth_headers, s["offering_id"], {qid: "Apply Gauss-Seidel iteration."})
    use_fake_ai(FakeBackend(verdicts={"Gauss-Seidel": _verdict("C3", "CO1")}))
    await client.post(f"{BASE}/sections/{s['offering_id']}/audit",
                      params={"exam_type": "FINAL"}, headers=auth_headers)

    resp = await _save_texts(client, auth_headers, s["offering_id"], {qid: "Define Gauss-Seidel."})

    assert resp.status_code == 200
    assert resp.json()["questions"][0]["audit"] is None


async def test_audit_needs_question_text(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    use_fake_ai(FakeBackend())
    resp = await client.post(f"{BASE}/sections/{s['offering_id']}/audit",
                             params={"exam_type": "FINAL"}, headers=auth_headers)
    assert resp.status_code == 422


async def test_audit_reports_unavailable_model_without_writing(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    qid = s["question_ids"]["Q1"]
    await _save_texts(client, auth_headers, s["offering_id"], {qid: "Apply Gauss-Seidel iteration."})
    use_fake_ai(FakeBackend(fail=True))
    resp = await client.post(f"{BASE}/sections/{s['offering_id']}/audit",
                             params={"exam_type": "FINAL"}, headers=auth_headers)
    assert resp.status_code == 202
    assert resp.json()["job"]["status"] == "FAILED"
    assert "offline" in resp.json()["job"]["error"]
    assert await db_session.scalar(select(func.count()).where(QuestionAudit.question_id == qid)) == 0


# ── Review ────────────────────────────────────────────────────────────────────

async def test_teacher_review_accept_and_override(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C6")])
    await _save_texts(client, auth_headers, s["offering_id"],
                      {s["question_ids"]["Q1"]: "Develop the polynomial by least squares."})
    use_fake_ai(FakeBackend(verdicts={"Develop": _verdict("C3", "CO1")}))
    body = (await client.post(f"{BASE}/sections/{s['offering_id']}/audit",
                              params={"exam_type": "FINAL"}, headers=auth_headers)).json()
    audit_id = body["questions"][0]["audit"]["id"]

    no_reason = await client.post(f"{BASE}/audits/{audit_id}/review",
                                  json={"decision": "OVERRIDE", "reason": "  "}, headers=auth_headers)
    assert no_reason.status_code == 422

    overridden = await client.post(
        f"{BASE}/audits/{audit_id}/review",
        json={"decision": "OVERRIDE", "reason": "Students derive the normal equations themselves."},
        headers=auth_headers,
    )
    assert overridden.status_code == 200
    audit = overridden.json()["questions"][0]["audit"]
    assert audit["review_status"] == "OVERRIDDEN"
    assert audit["override_reason"].startswith("Students derive")

    accepted = await client.post(f"{BASE}/audits/{audit_id}/review",
                                 json={"decision": "ACCEPT"}, headers=auth_headers)
    audit = accepted.json()["questions"][0]["audit"]
    assert (audit["review_status"], audit["override_reason"]) == ("ACCEPTED", None)
    assert accepted.json()["summary"]["pending_review"] == 0


# ── Access ────────────────────────────────────────────────────────────────────

async def test_section_teacher_only_sees_assigned_sections(
    client: AsyncClient, teacher_auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    use_fake_ai(FakeBackend())
    url = f"{BASE}/sections/{s['offering_id']}"

    denied = await client.get(url, params={"exam_type": "FINAL"}, headers=teacher_auth_headers)
    assert denied.status_code == 403

    teacher_id = await db_session.scalar(select(User.id).where(User.email == TEST_TEACHER_EMAIL))
    db_session.add(FacultyAssignment(section_offering_id=s["offering_id"], user_id=teacher_id,
                                     role_in_course="SECTION_TEACHER"))
    await db_session.commit()

    allowed = await client.get(url, params={"exam_type": "FINAL"}, headers=teacher_auth_headers)
    assert allowed.status_code == 200
    listed = await client.get(f"{BASE}/sections", headers=teacher_auth_headers)
    assert str(s["offering_id"]) in {row["id"] for row in listed.json()}
