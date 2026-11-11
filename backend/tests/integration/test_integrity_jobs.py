"""Integrity background jobs: lifecycle, conflicts, reading routes, usage and the worker hand-off."""
import io
import json
import zipfile
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from PIL import Image
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from weasyprint import HTML

from app.modules.ai.models import AICall
from app.modules.integrity import jobs as jobs_module
from app.modules.integrity.models import IntegrityJob, QuestionPaper
from app.workers.tasks import integrity as worker_task
from tests.ai_fakes import DeferredJobRunner, FakeBackend, use_fake_ai, verdict
from tests.conftest import TEST_ORG_ID
from tests.integration.test_integrity_audit import BASE, _png, _save_texts, _scenario


def _q(label, text, continues=False, **extra):
    return {"label": label, "text": text, "context": None, "marks": None, "co": None,
            "figure": None, "continues": continues, **extra}


async def _upload(client, headers, offering_id, name, data, content_type):
    return await client.post(
        f"{BASE}/sections/{offering_id}/paper", params={"exam_type": "FINAL"},
        files={"file": (name, data, content_type)}, headers=headers,
    )


def _two_page_scan() -> bytes:
    pages = [Image.new("RGB", (600, 850), "white") for _ in range(2)]
    buffer = io.BytesIO()
    pages[0].save(buffer, format="PDF", save_all=True, append_images=pages[1:])
    return buffer.getvalue()


# ── Lifecycle ─────────────────────────────────────────────────────────────────

async def test_queued_job_is_visible_and_blocks_a_second_one(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    runner = DeferredJobRunner()
    use_fake_ai(FakeBackend(), runner=runner)

    resp = await _upload(client, auth_headers, s["offering_id"], "paper.png", _png(), "image/png")
    assert resp.status_code == 202
    body = resp.json()
    assert (body["job"]["kind"], body["job"]["status"]) == ("READ_PAPER", "QUEUED")
    assert (body["job"]["progress_done"], body["job"]["progress_total"]) == (0, 1)
    assert body["paper"]["extraction_status"] == "PENDING"
    [(job_id, payload)] = runner.submitted
    assert payload["method"] == "VISION" and payload["pages"][0]["image"]

    again = await _upload(client, auth_headers, s["offering_id"], "paper.png", _png(), "image/png")
    assert again.status_code == 409
    assert "reading the paper" in again.json()["detail"]
    await _save_texts(client, auth_headers, s["offering_id"], {s["question_ids"]["Q1"]: "Apply Euler."})
    audit = await client.post(f"{BASE}/sections/{s['offering_id']}/audit",
                              params={"exam_type": "FINAL"}, headers=auth_headers)
    assert audit.status_code == 409


async def test_job_that_died_with_its_worker_shows_as_failed_and_can_be_replaced(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    use_fake_ai(FakeBackend(), runner=DeferredJobRunner())
    await _upload(client, auth_headers, s["offering_id"], "paper.png", _png(), "image/png")
    await db_session.execute(
        update(IntegrityJob)
        .where(IntegrityJob.section_offering_id == s["offering_id"])
        .values(status="RUNNING", created_at=datetime.now(timezone.utc) - timedelta(hours=3))
    )
    await db_session.commit()

    overview = await client.get(f"{BASE}/sections/{s['offering_id']}", params={"exam_type": "FINAL"},
                                headers=auth_headers)
    assert overview.json()["job"]["status"] == "FAILED"
    assert "without finishing" in overview.json()["job"]["error"]

    use_fake_ai(FakeBackend(pages=[{"questions": [_q("1", "Apply Euler's method.")]}]))
    retry = await _upload(client, auth_headers, s["offering_id"], "paper.png", _png(), "image/png")
    assert retry.status_code == 202
    assert retry.json()["job"]["status"] == "DONE"


async def test_submission_failure_is_reported_and_recorded(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    class Broken:
        async def submit(self, job_id, payload):
            raise ConnectionError("redis down")

    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    use_fake_ai(FakeBackend(), runner=Broken())
    resp = await _upload(client, auth_headers, s["offering_id"], "paper.png", _png(), "image/png")
    assert resp.status_code == 503
    job = (await db_session.execute(select(IntegrityJob).where(
        IntegrityJob.section_offering_id == s["offering_id"]
    ).execution_options(populate_existing=True))).scalar_one()
    assert job.status == "FAILED"


# ── Reading routes ────────────────────────────────────────────────────────────

async def test_question_spanning_two_scanned_pages_is_read_as_one(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3"), ("Q2a", "CO2", "C3")])
    backend = use_fake_ai(FakeBackend(pages=[
        {"questions": [_q("1", "Apply Gauss-Seidel."), _q("2(a)", "Fit a straight line to the data")]},
        {"questions": [_q("2(a)", "| x | y |\n| 1 | 2 |", continues=True, marks=6),
                       _q("2(b)", "Explain the residuals.")]},
    ]))
    resp = await _upload(client, auth_headers, s["offering_id"], "paper.pdf", _two_page_scan(),
                         "application/pdf")
    paper = resp.json()["paper"]
    assert [q["label"] for q in paper["questions"]] == ["1", "2(a)", "2(b)"]
    assert paper["questions"][1]["text"] == "Fit a straight line to the data\n| x | y |\n| 1 | 2 |"
    assert paper["questions"][1]["marks"] == 6
    assert paper["questions"][1]["matched_question_id"] == str(s["question_ids"]["Q2a"])
    assert resp.json()["job"]["progress_done"] == 2
    assert 'ended with question "2(a)"' in backend.prompts[1]


async def test_born_digital_pdf_is_split_from_its_own_text(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3"), ("Q2", "CO2", "C3")])
    pdf = HTML(string="""
        <p>Final Examination. Answer all questions. Figures in the right margin indicate marks.</p>
        <p>1. Apply the Gauss-Seidel iteration to the given system of linear equations until
        two successive approximations agree to three decimal places. [6] CO1</p>
        <p>2. Fit a second degree polynomial to the data in the table by the method of least
        squares and estimate the value at x equal to four. [6] CO2</p>""").write_pdf()
    backend = use_fake_ai(FakeBackend(splits=[{"questions": [
        _q("1", "Apply the Gauss-Seidel iteration to the given system of linear equations until "
                "two successive approximations agree to three decimal places.", marks=6, co="CO1"),
        _q("2", "Prove that every planar graph is five colourable using induction on vertices."),
    ]}]))

    resp = await _upload(client, auth_headers, s["offering_id"], "final.pdf", pdf, "application/pdf")

    paper = resp.json()["paper"]
    assert (paper["extraction_method"], paper["extraction_prompt_version"]) == ("TEXT_LAYER", "extract-text-v1")
    assert all(call["images"] == 0 for call in backend.calls)  # no vision call
    assert "two successive approximations" in backend.prompts[0]
    warnings = {q["label"]: q["warning"] for q in paper["questions"]}
    assert warnings["1"] is None
    assert warnings["2"] is not None  # not in the document: the model made it up
    assert resp.json()["job"]["result"] == {"questions": 2, "flagged": 1}


async def test_word_document_is_read_with_its_numbering(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    numbering = (
        f'<w:numbering {ns}><w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:start w:val="1"/>'
        '<w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl></w:abstractNum>'
        '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>'
    )
    paragraph = ('<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>'
                 '<w:r><w:t>Apply Euler\'s method with step size 0.1 to the initial value problem.</w:t></w:r></w:p>')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", f"<w:document {ns}><w:body>{paragraph}</w:body></w:document>")
        archive.writestr("word/numbering.xml", numbering)
    backend = use_fake_ai(FakeBackend(splits=[{"questions": [
        _q("1", "Apply Euler's method with step size 0.1 to the initial value problem."),
    ]}]))

    resp = await _upload(client, auth_headers, s["offering_id"], "final.docx", buffer.getvalue(),
                         "application/octet-stream")

    assert resp.status_code == 202, resp.text
    paper = resp.json()["paper"]
    assert (paper["extraction_method"], paper["page_count"]) == ("DOCX", None)
    assert "1. Apply Euler's method" in backend.prompts[0]
    assert paper["questions"][0]["matched_question_id"] == str(s["question_ids"]["Q1"])


# ── Gateway integration ───────────────────────────────────────────────────────

async def test_every_model_call_is_logged_with_usage(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    await _save_texts(client, auth_headers, s["offering_id"],
                      {s["question_ids"]["Q1"]: "Apply Gauss-Seidel iteration."})
    use_fake_ai(FakeBackend(verdicts={"Gauss-Seidel": verdict("C3", "CO1")}))
    await client.post(f"{BASE}/sections/{s['offering_id']}/audit", params={"exam_type": "FINAL"},
                      headers=auth_headers)

    calls = (await db_session.execute(select(AICall).where(
        AICall.organization_id == TEST_ORG_ID, AICall.purpose == "audit_question",
        AICall.prompt_version == "audit-v3", AICall.feature == "integrity",
    ).order_by(AICall.created_at.desc()).limit(3))).scalars().all()
    assert len(calls) == 3  # three independent judgments
    assert all(c.status == "OK" and c.input_tokens == 300 and c.model == "fake-text" for c in calls)


async def test_external_provider_never_sees_personal_data_in_question_text(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    await _save_texts(client, auth_headers, s["offering_id"], {
        s["question_ids"]["Q1"]: "Apply Gauss-Seidel. Email your working to rahim@example.edu (ID 221-15-4567).",
    })
    backend = use_fake_ai(FakeBackend(external=True, verdicts={"Gauss-Seidel": verdict("C3", "CO1")}))
    await client.post(f"{BASE}/sections/{s['offering_id']}/audit", params={"exam_type": "FINAL"},
                      headers=auth_headers)
    assert backend.prompts
    assert all("rahim@" not in p and "221-15-4567" not in p for p in backend.prompts)
    assert "[EMAIL]" in backend.prompts[0] and "[ID]" in backend.prompts[0]


async def test_organization_can_turn_the_auditor_off(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    await _save_texts(client, auth_headers, s["offering_id"], {s["question_ids"]["Q1"]: "Apply Euler."})
    backend = use_fake_ai(FakeBackend())
    assert (await client.put("/api/v1/ai/settings", json={"integrity_provider": "off"},
                             headers=auth_headers)).status_code == 200
    try:
        resp = await client.post(f"{BASE}/sections/{s['offering_id']}/audit",
                                 params={"exam_type": "FINAL"}, headers=auth_headers)
        assert resp.json()["job"]["status"] == "FAILED"
        assert "turned off" in resp.json()["job"]["error"]
        assert backend.prompts == []
    finally:
        await client.put("/api/v1/ai/settings", json={"integrity_provider": None}, headers=auth_headers)


# ── Worker hand-off ───────────────────────────────────────────────────────────

async def test_arq_runner_parks_pages_in_redis_and_the_worker_deletes_them(monkeypatch):
    store: dict = {}
    enqueued: list = []

    class FakePool:
        async def set(self, key, value, ex):
            store[key] = (value, ex)

        async def enqueue_job(self, name, *args, _job_id):
            enqueued.append((name, args, _job_id))

    class FakeRedis:
        async def getdel(self, key):
            value = store.pop(key, (None, None))[0]
            return value.encode() if value else None

    async def fake_pool():
        return FakePool()

    import app.core.arq_pool as arq_pool
    monkeypatch.setattr(arq_pool, "get_arq_pool", fake_pool)
    ran: list = []

    async def fake_execute(session_factory, backend_factory, job_id, payload):
        ran.append((job_id, payload))

    monkeypatch.setattr(worker_task, "execute_job", fake_execute)

    job_id = __import__("uuid").uuid4()
    payload = {"method": "VISION", "page_count": 1, "pages": [{"image": "aGVsbG8=", "text": None}]}
    await jobs_module.ArqJobRunner().submit(job_id, payload)

    key = f"integrity:payload:{job_id}"
    assert json.loads(store[key][0]) == payload and store[key][1] > 0
    assert enqueued == [("run_integrity_job", (str(job_id),), f"integrity:{job_id}")]
    # arq's own job record holds only the id — never the pages.
    assert "aGVsbG8" not in json.dumps(enqueued)

    await worker_task.run_integrity_job({"redis": FakeRedis()}, str(job_id))
    assert ran == [(job_id, payload)]
    assert key not in store


async def test_paper_payload_round_trips():
    from app.modules.integrity.documents import PreparedPage, PreparedPaper

    paper = PreparedPaper(method="MIXED", page_count=2,
                          pages=[PreparedPage(image=b"\x00jpeg"), PreparedPage(text="1. Define.")])
    decoded = jobs_module.decode_paper(json.loads(json.dumps(jobs_module.encode_paper(paper))))
    assert decoded == paper


async def test_paper_file_is_never_stored(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    s = await _scenario(db_session, [("Q1", "CO1", "C3")])
    use_fake_ai(FakeBackend(pages=[{"questions": [_q("1", "Apply Euler.")]}]))
    await _upload(client, auth_headers, s["offering_id"], "paper.png", _png(), "image/png")
    columns = QuestionPaper.__table__.columns.keys()
    assert not any("data" in c or "content" == c or "file_bytes" in c for c in columns)
    assert await db_session.scalar(select(func.count()).select_from(QuestionPaper).where(
        QuestionPaper.section_offering_id == s["offering_id"])) == 1
