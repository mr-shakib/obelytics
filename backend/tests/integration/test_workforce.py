"""Workforce readiness end to end: job postings → skills → coverage by the curriculum's COs."""
import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.curriculum.models import Curriculum
from app.modules.obe.models import COPOMappingEntry, COPOMappingSet
from tests.ai_fakes import FakeBackend, use_fake_ai
from tests.conftest import TEST_ORG_ID
from tests.integration.test_outcome_authoring import _scenario

BASE = "/api/v1/workforce"
COVERAGE_NEEDLE = "Compare what employers ask for"


def _skills(*names):
    return {"skills": [{"name": n, "category": "technical", "required": True} for n in names]}


@pytest.mark.asyncio
async def test_postings_are_read_and_compared_with_the_curriculum(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session)
    curriculum = await db_session.get(Curriculum, uuid.UUID(s["curriculum_id"]))
    program_id = curriculum.program_id
    mapping_set = COPOMappingSet(organization_id=TEST_ORG_ID, curriculum_id=curriculum.id,
                                 course_id=uuid.UUID(s["course_id"]))
    db_session.add(mapping_set)
    await db_session.flush()
    db_session.add(COPOMappingEntry(mapping_set_id=mapping_set.id, course_outcome_id=s["co"]["CO2"],
                                    program_outcome_id=s["po"]["PO3"], weight=3, justification="Design."))
    await db_session.commit()
    course_code = (await client.get(f"/api/v1/courses/{s['course_id']}", headers=auth_headers)).json()["code"]

    backend = use_fake_ai(FakeBackend(verdicts={
        "Kernel Engineer": _skills("Memory management", "C programming"),
        "Systems Engineer": _skills("memory management", "Linux administration"),
        COVERAGE_NEEDLE: {"skills": [
            {"skill": "Memory management", "coverage": "covered", "outcomes": [f"{course_code}/CO2"],
             "reason": "CO2 designs an allocator.", "suggested_course": None},
            {"skill": "C programming", "coverage": "partial", "outcomes": ["FAKE/CO1"],
             "reason": "Only implied.", "suggested_course": course_code},
            {"skill": "Linux administration", "coverage": "gap", "outcomes": [],
             "reason": "Not taught.", "suggested_course": course_code},
        ]},
    }))
    for title in ("Kernel Engineer", "Systems Engineer"):
        resp = await client.post(f"{BASE}/programs/{program_id}/postings", headers=auth_headers, json={
            "title": title, "employer": "Example Ltd",
            "text": f"We are hiring a {title} to work on operating system internals and tooling.",
        })
        assert resp.status_code == 201, resp.text
        assert resp.json()["skills"] and resp.json()["skills_prompt_version"] == "job-skills-v1"

    resp = await client.post(f"{BASE}/programs/{program_id}/analysis", headers=auth_headers,
                             json={"curriculum_id": s["curriculum_id"]})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    skills = {x["skill"]: x for x in body["skills"]}
    assert body["posting_count"] == 2 and skills["Memory management"]["postings"] == 2
    assert skills["Memory management"]["coverage"] == "covered"
    assert skills["Memory management"]["program_outcomes"] == ["PO3"]  # via the CO-PO mapping
    assert skills["C programming"]["coverage"] == "gap"  # its only CO reference was invented
    assert skills["Linux administration"]["suggested_course"]["code"] == course_code
    # 2 of 4 skill-mentions are covered
    assert body["summary"]["coverage_pct"] == 50.0
    po3 = next(p for p in body["program_outcomes"] if p["code"] == "PO3")
    assert po3["skills"] == ["Memory management"] and po3["demand"] == 2

    coverage_prompt = next(p for p in backend.prompts if COVERAGE_NEEDLE in p)
    assert f"{course_code}/CO2" in coverage_prompt and "Memory management (2 of 2" in coverage_prompt
    latest = await client.get(f"{BASE}/programs/{program_id}/analysis",
                              params={"curriculum_id": s["curriculum_id"]}, headers=auth_headers)
    assert latest.json()["id"] == body["id"]
    audit = (await db_session.execute(select(AuditLog).where(
        AuditLog.action == "AI_MARKET_ANALYSIS", AuditLog.entity_id == curriculum.id))).scalar_one()
    assert json.loads(audit.extra)["coverage_pct"] == 50.0


@pytest.mark.asyncio
async def test_analysis_needs_postings_and_teachers_cannot_run_it(
    client: AsyncClient, auth_headers: dict, teacher_auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session)
    curriculum = await db_session.get(Curriculum, uuid.UUID(s["curriculum_id"]))
    use_fake_ai(FakeBackend())
    resp = await client.post(f"{BASE}/programs/{curriculum.program_id}/analysis", headers=auth_headers,
                             json={"curriculum_id": s["curriculum_id"]})
    assert resp.status_code == 422 and "job postings" in resp.json()["detail"]
    resp = await client.post(f"{BASE}/programs/{curriculum.program_id}/postings", headers=teacher_auth_headers,
                             json={"title": "Engineer", "text": "x" * 50})
    assert resp.status_code == 403
