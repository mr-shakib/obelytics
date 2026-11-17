"""Accreditation evidence writer end to end: manual upload → retrieval → cited draft → checks → decision."""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import AICall
from app.modules.audit.models import AuditLog
from app.modules.curriculum.models import Curriculum
from tests.ai_fakes import FakeBackend, use_fake_ai
from tests.integration.test_outcome_authoring import _scenario

BASE = "/api/v1/evidence"
NEEDLE = "accreditation self-assessment report"

MANUAL = b"""CRITERION 7 PROGRAM OUTCOMES

The program shall demonstrate that its graduates attain every program outcome, measured directly.

CRITERION 9 FACILITIES

Laboratories shall be adequate for the number of students enrolled in each course."""


@pytest.mark.asyncio
async def test_draft_cites_program_records_and_flags_what_it_cannot_back(
    client: AsyncClient, auth_headers: dict, teacher_auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session)
    curriculum = await db_session.get(Curriculum, uuid.UUID(s["curriculum_id"]))
    program_id = curriculum.program_id

    resp = await client.post(f"{BASE}/documents", headers=auth_headers, data={"title": "Accreditation manual"},
                             files={"file": ("manual.txt", MANUAL, "text/plain")})
    assert resp.status_code == 201, resp.text
    assert resp.json()["passage_count"] == 2

    backend = use_fake_ai(FakeBackend(verdicts={NEEDLE: {
        "sentences": [
            {"text": "The program states its outcomes, including PO1.", "cites": ["E1"], "gap": False},
            {"text": "Ninety percent of graduates attain PO1, rising 15 points a year.", "cites": ["E1"], "gap": False},
            {"text": "Direct measurement records for every outcome are not yet available.", "cites": ["M1"],
             "gap": True},
        ],
        "missing": ["Attainment results for each program outcome"],
    }}))
    resp = await client.post(f"{BASE}/programs/{program_id}/drafts", headers=auth_headers, json={
        "curriculum_id": s["curriculum_id"], "criterion_title": "Program Outcomes",
        "criterion_guidance": "Show that graduates attain every program outcome.",
    })
    assert resp.status_code == 200, resp.text
    draft = resp.json()

    # Retrieval: the matching manual passage is offered, the facilities one is not.
    prompt = next(p for p in backend.prompts if NEEDLE in p)
    assert "attain every program outcome" in prompt and "Laboratories" not in prompt
    assert draft["sources"]["M1"]["kind"] == "manual" and draft["sources"]["E1"]["kind"] == "program_outcome"
    statuses = [x["status"] for x in draft["sentences"]]
    assert statuses == ["supported", "check", "supported"]
    assert "15" in draft["sentences"][1]["issues"][0]
    assert draft["missing"] == ["Attainment results for each program outcome"]
    assert draft["prompt_version"] == "evidence-v1" and draft["status"] == "DRAFT"

    calls = (await db_session.execute(
        select(AICall).where(AICall.purpose == "draft_accreditation_evidence")
    )).scalars().all()
    assert len(calls) == 1 and calls[0].prompt_version == "evidence-v1"

    listed = await client.get(f"{BASE}/programs/{program_id}/drafts", headers=auth_headers,
                              params={"curriculum_id": s["curriculum_id"]})
    assert [d["id"] for d in listed.json()] == [draft["id"]]

    resp = await client.post(f"{BASE}/drafts/{draft['id']}/decision", headers=auth_headers,
                             json={"decision": "ACCEPTED", "edited_text": "Edited section."})
    assert resp.status_code == 200 and resp.json()["status"] == "ACCEPTED"
    actions = (await db_session.execute(
        select(AuditLog.action).where(AuditLog.action.like("AI_EVIDENCE_%"))
    )).scalars().all()
    assert sorted(actions) == ["AI_EVIDENCE_ACCEPTED", "AI_EVIDENCE_DRAFT"]

    resp = await client.post(f"{BASE}/programs/{program_id}/drafts", headers=teacher_auth_headers, json={
        "curriculum_id": s["curriculum_id"], "criterion_title": "Program Outcomes",
    })
    assert resp.status_code == 403
