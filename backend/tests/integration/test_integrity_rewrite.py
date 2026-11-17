"""
Rewriting a question to fit its mapping: one model writes, the auditor checks.

The checker is the normal audit, never told the target, so a rewrite only counts as
verified when an independent judgment lands on the intended CO and Bloom level.
"""
import json
import uuid

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import AICall
from app.modules.assessment.models import MarksheetQuestion
from app.modules.audit.models import AuditLog
from app.modules.integrity.models import QuestionRewrite
from tests.ai_fakes import FakeBackend, use_fake_ai
from tests.ai_fakes import verdict as _verdict
from tests.integration.test_integrity_audit import _save_texts, _scenario

BASE = "/api/v1/integrity"
REWRITE = "Rewrite the question so that"
ORIGINAL = "Develop the Newton-Raphson iteration formula for f(x) = x^2 - 2."


def _replies(*texts):
    """Rewrite replies in order, one per attempt."""
    queue = [{"question": text, "changes": [f"Changed to: {text[:20]}"]} for text in texts]
    return lambda temperature: queue.pop(0)


async def test_rewrite_is_verified_by_the_auditor_and_leaves_the_marksheet_alone(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C6")])
    qid = s["question_ids"]["Q1"]
    await _save_texts(client, auth_headers, s["offering_id"], {qid: ORIGINAL})
    backend = use_fake_ai(FakeBackend(verdicts={
        REWRITE: _replies("Design a new hybrid root-finding method for a function with a flat region; "
                          "justify its stopping rule."),
        "hybrid root-finding": _verdict("C6", "CO1"),
    }))

    resp = await client.post(f"{BASE}/questions/{qid}/rewrite", headers=auth_headers,
                             json={"instruction": "Keep it under 10 marks."})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["verified_alignment"] == "ALIGNED"
    assert body["target_bloom_code"] == "C6" and body["target_course_outcome"]["code"] == "CO1"
    assert body["rewritten_text"].startswith("Design a new hybrid")
    assert len(body["attempts"]) == 1 and body["attempts"][0]["judged_bloom"] == "C6"
    assert body["prompt_version"] == "rewrite-v2" and body["decision"] is None

    rewrite_prompt = next(p for p in backend.prompts if REWRITE in p)
    assert f"<question>\n{ORIGINAL}\n</question>" in rewrite_prompt
    assert "Course outcome CO1" in rewrite_prompt and "Bloom level C6 Create" in rewrite_prompt
    assert "<teacher_request>Keep it under 10 marks.</teacher_request>" in rewrite_prompt
    # The checker is the plain audit: it is not told what the rewrite was aiming for.
    check_prompt = next(p for p in backend.prompts if "hybrid root-finding" in p and REWRITE not in p)
    assert "C6 Create" not in check_prompt.split("<question>")[1]

    question = await db_session.get(MarksheetQuestion, qid)
    await db_session.refresh(question)
    assert question.question_text == ORIGINAL  # advisory: the paper's wording is untouched
    calls = await db_session.scalar(select(func.count()).select_from(AICall).where(
        AICall.purpose == "rewrite_question"))
    assert calls >= 1
    audit = (await db_session.execute(select(AuditLog).where(
        AuditLog.action == "INTEGRITY_QUESTION_REWRITTEN", AuditLog.entity_id == qid))).scalar_one()
    assert json.loads(audit.extra)["verified_alignment"] == "ALIGNED"

    kept = await client.post(f"{BASE}/rewrites/{body['id']}/decision", headers=auth_headers,
                             json={"decision": "KEPT"})
    assert kept.status_code == 200 and kept.json()["decision"] == "KEPT"
    overview = await client.get(f"{BASE}/sections/{s['offering_id']}", params={"exam_type": "FINAL"},
                                headers=auth_headers)
    assert overview.json()["questions"][0]["kept_rewrite"]["id"] == body["id"]


async def test_rewrite_tries_again_with_the_checkers_reason(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C6")])
    qid = s["question_ids"]["Q1"]
    await _save_texts(client, auth_headers, s["offering_id"], {qid: ORIGINAL})
    backend = use_fake_ai(FakeBackend(verdicts={
        REWRITE: _replies("Construct the Newton-Raphson formula step by step.",
                          "Invent a safeguarded root-finding scheme for a function with a flat region."),
        "step by step": _verdict("C3", "CO1"),
        "safeguarded": _verdict("C6", "CO1"),
    }))
    body = (await client.post(f"{BASE}/questions/{qid}/rewrite", headers=auth_headers, json={})).json()

    assert [a["alignment"] for a in body["attempts"]] == ["PARTIAL", "ALIGNED"]
    assert body["rewritten_text"].startswith("Invent a safeguarded")
    second = [p for p in backend.prompts if REWRITE in p][1]
    assert "Your previous rewrite was reviewed independently and judged C3" in second


async def test_rewrite_reports_when_it_could_not_reach_the_target(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C6")])
    qid = s["question_ids"]["Q1"]
    await _save_texts(client, auth_headers, s["offering_id"], {qid: ORIGINAL})
    use_fake_ai(FakeBackend(verdicts={
        REWRITE: _replies("Apply Newton-Raphson twice to x^2 - 2.", "Apply Newton-Raphson three times."),
        "Newton-Raphson t": _verdict("C3", "CO1"),
    }))
    body = (await client.post(f"{BASE}/questions/{qid}/rewrite", headers=auth_headers, json={})).json()
    assert body["verified_alignment"] == "PARTIAL" and len(body["attempts"]) == 2
    row = await db_session.get(QuestionRewrite, uuid.UUID(body["id"]))
    assert row.verified_alignment == "PARTIAL"


async def test_rewrite_needs_wording_and_a_target(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    qid = s["question_ids"]["Q1"]
    use_fake_ai(FakeBackend())
    resp = await client.post(f"{BASE}/questions/{qid}/rewrite", headers=auth_headers, json={})
    assert resp.status_code == 422 and "no wording" in resp.json()["detail"]

    resp = await client.post(f"{BASE}/questions/{uuid.uuid4()}/rewrite", headers=auth_headers, json={})
    assert resp.status_code == 404
