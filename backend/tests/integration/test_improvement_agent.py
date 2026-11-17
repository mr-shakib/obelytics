"""
The improvement agent: fixed tools, a short loop, and a plan whose evidence is checked.

The fake model picks tools by matching text in the step prompt, then writes a plan that
cites one real question and one invented one; only the real one may count as evidence.
"""
import json

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import AICall
from app.modules.audit.models import AuditLog
from app.modules.curriculum.models import SectionOffering
from app.modules.improvement.models import ImprovementPlan
from tests.ai_fakes import FakeBackend, use_fake_ai
from tests.integration.test_integrity_audit import _scenario
from tests.integration.test_integrity_evidence import _students_with_marks

BASE = "/api/v1/improvement"
STEP = "You can call one of these read-only tools"
FINAL = "Write the improvement plan from these results only"


def _steps(*replies):
    queue = list(replies)
    return lambda temperature: queue.pop(0) if queue else {
        "thought": "Done.", "action": "finish", "tool": None, "co": None}


async def _section(db: AsyncSession) -> dict:
    s = await _scenario(db, [("Q1", "CO1", "C3"), ("Q2", "CO2", "C4")])
    # CO1 is fine; CO2's only question is answered badly by almost everyone.
    await _students_with_marks(db, s, {
        "Q1": ["5", "4", "4", "5", "3"],
        "Q2": ["0", "1", "0", "4", "0"],
    })
    return s


async def test_agent_explains_a_gap_from_its_tools_and_checks_the_citations(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _section(db_session)
    backend = use_fake_ai(FakeBackend(verdicts={
        FINAL: {
            "summary": "CO2 was not attained because Q2 was answered badly.",
            "follow_up": None,
            "diagnoses": [{
                "co": "CO2",
                "problem": "Only 1 of 5 students scored at least half on Q2.",
                "likely_cause": "Curve fitting got little practice.",
                "confidence": 0.7,
                "evidence": [
                    {"tool": "question_stats", "ref": "Q2", "detail": "average 20%"},
                    {"tool": "question_stats", "ref": "Q9", "detail": "made up"},
                ],
                "interventions": [{"action": "Add a least-squares lab in week 9.", "kind": "teaching",
                                   "effort": "low", "success_measure": "Q2-type average at least 50%"}],
            }],
        },
        STEP: _steps(
            {"thought": "CO2 is not attained; look at its questions.", "action": "call",
             "tool": "question_stats", "co": "CO2"},
            {"thought": "See how CO2 was taught.", "action": "call", "tool": "lesson_plan", "co": "CO2"},
        ),
    }))

    resp = await client.post(f"{BASE}/sections/{s['offering_id']}/plan", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    plan = resp.json()
    assert plan["prompt_version"] == "improve-v1"
    assert [(step.get("tool"), step["chosen_by"]) for step in plan["steps"]] == [
        ("outcome_attainment", "fixed"), ("question_stats", "model"), ("lesson_plan", "model"),
        (None, "model"),
    ]
    stats = plan["steps"][1]["result"]["questions"][0]
    assert stats["question"] == "Q2" and stats["average_pct"] == 20.0 and stats["zero_pct"] == 60.0
    assert stats["at_least_half_pct"] == 20.0

    [diagnosis] = plan["diagnoses"]
    assert diagnosis["co"] == "CO2" and diagnosis["supported"] is True
    assert [(e["ref"], e["verified"]) for e in diagnosis["evidence"]] == [("Q2", True), ("Q9", False)]
    assert diagnosis["interventions"][0]["id"] == "d1-i1"

    # Tool results reach the model as aggregates: no student names or identifiers.
    prompts = "\n".join(backend.prompts)
    assert "Evidence Student" not in prompts and "@student.example.edu" not in prompts
    calls = (await db_session.execute(select(AICall).where(AICall.feature == "improvement"))).scalars().all()
    assert {c.purpose for c in calls} >= {"improvement_step", "improvement_plan"}
    audit = (await db_session.execute(select(AuditLog).where(
        AuditLog.action == "AI_IMPROVEMENT_PLAN", AuditLog.entity_id == s["offering_id"]))).scalar_one()
    assert json.loads(audit.extra)["diagnoses"] == 1

    decided = await client.post(f"{BASE}/plans/{plan['id']}/interventions/d1-i1", headers=auth_headers,
                                json={"decision": "ACCEPTED", "note": "Will do."})
    assert decided.status_code == 200
    assert decided.json()["diagnoses"][0]["interventions"][0]["decision"] == "ACCEPTED"
    latest = await client.get(f"{BASE}/sections/{s['offering_id']}/plan", headers=auth_headers)
    assert latest.json()["id"] == plan["id"]


async def test_the_next_plan_for_the_course_sees_what_was_accepted(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _section(db_session)
    use_fake_ai(FakeBackend(verdicts={
        FINAL: {"summary": "First plan.", "follow_up": None, "diagnoses": [{
            "co": "CO2", "problem": "Weak.", "likely_cause": "Practice.", "confidence": 0.5,
            "evidence": [{"tool": "outcome_attainment", "ref": "CO2", "detail": "not attained"}],
            "interventions": [{"action": "Add a lab.", "kind": "teaching", "effort": "low",
                               "success_measure": "50%"}]}]},
        STEP: _steps(),
    }))
    first = (await client.post(f"{BASE}/sections/{s['offering_id']}/plan", headers=auth_headers)).json()
    await client.post(f"{BASE}/plans/{first['id']}/interventions/d1-i1", headers=auth_headers,
                      json={"decision": "ACCEPTED"})

    # The same course taught in another section (next term).
    course_id = (await db_session.execute(
        select(ImprovementPlan.course_id).where(ImprovementPlan.id == first["id"]))).scalar_one()
    other = await _scenario(db_session, [("Q1", "CO1", "C3")])
    offering = await db_session.get(SectionOffering, other["offering_id"])
    offering.course_id = course_id
    await db_session.commit()
    await _students_with_marks(db_session, other, {"Q1": ["5", "5"]})

    backend = use_fake_ai(FakeBackend(verdicts={
        FINAL: {"summary": "Second plan.", "follow_up": "The lab helped.", "diagnoses": []},
        STEP: _steps(),
    }))
    second = await client.post(f"{BASE}/sections/{other['offering_id']}/plan", headers=auth_headers)
    assert second.status_code == 200, second.text
    body = second.json()
    assert [step.get("tool") for step in body["steps"][:2]] == ["outcome_attainment", "previous_plan"]
    assert body["steps"][1]["result"]["diagnoses"][0]["accepted_interventions"] == ["Add a lab."]
    assert body["follow_up"] == "The lab helped."
    assert "previous_plan" in next(p for p in backend.prompts if FINAL in p)


async def test_agent_needs_marks(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    use_fake_ai(FakeBackend())
    resp = await client.post(f"{BASE}/sections/{s['offering_id']}/plan", headers=auth_headers)
    assert resp.status_code == 422 and "no marks" in resp.json()["detail"]
