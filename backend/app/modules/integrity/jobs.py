"""
Background work for the integrity auditor: reading a paper, running an audit.

Model calls take seconds to minutes, so the API only records a job and hands it to
a runner; the page polls the job's progress.

- ArqJobRunner    — production: the arq worker runs the job. A paper's page images
  are parked in Redis under a short-lived key and deleted the moment the worker
  reads them (they are never part of arq's stored job record).
- InlineJobRunner — local development without a worker: runs in the API process.
"""
import asyncio
import base64
import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.ai.gateway import AIGateway, BackendFactory
from app.modules.ai.providers import AIError, build_backend
from app.modules.integrity.documents import PreparedPage, PreparedPaper
from app.modules.integrity.models import IntegrityJob

logger = logging.getLogger(__name__)

PAYLOAD_KEY = "integrity:payload:{}"
TASK_NAME = "run_integrity_job"

SessionFactory = Callable[[], AsyncSession]


class JobError(RuntimeError):
    """A job could not finish for a reason the teacher should see."""


# ── Payload (page images and text, for READ_PAPER) ───────────────────────────

def encode_paper(paper: PreparedPaper) -> dict:
    return {
        "method": paper.method,
        "page_count": paper.page_count,
        "pages": [
            {
                "image": base64.b64encode(page.image).decode() if page.image is not None else None,
                "text": page.text,
            }
            for page in paper.pages
        ],
    }


def decode_paper(payload: dict) -> PreparedPaper:
    return PreparedPaper(
        method=payload["method"],
        page_count=payload.get("page_count"),
        pages=[
            PreparedPage(
                image=base64.b64decode(page["image"]) if page.get("image") else None,
                text=page.get("text"),
            )
            for page in payload["pages"]
        ],
    )


# ── Running a job ─────────────────────────────────────────────────────────────

async def execute_job(
    session_factory: SessionFactory,
    backend_factory: BackendFactory,
    job_id: UUID,
    payload: dict | None,
) -> None:
    # Imported here: the service imports this module for the runners.
    from app.modules.integrity.service import IntegrityJobService

    async with session_factory() as session:
        job = await session.get(IntegrityJob, job_id)
        if job is None or job.status != "QUEUED":
            return
        job.status = "RUNNING"
        job.started_at = datetime.now(timezone.utc)
        await session.commit()

        gateway = await AIGateway.for_feature(
            session,
            feature="integrity",
            organization_id=job.organization_id,
            user_id=job.created_by_user_id,
            backend_factory=backend_factory,
        )
        work = IntegrityJobService(session, gateway, job)
        try:
            if not gateway.available:
                raise JobError(gateway.unavailable_reason())
            if job.kind == "READ_PAPER":
                if payload is None:
                    raise JobError("The uploaded file expired before it could be read. Upload it again.")
                job.result = await work.read(decode_paper(payload))
            else:
                job.result = await work.audit()
            job.status = "DONE"
        except (AIError, JobError) as exc:
            await work.fail(str(exc))
        except Exception:
            logger.exception("Integrity job %s failed", job_id)
            await work.fail("Something went wrong on the server while doing this. Try again.")
        job = await session.get(IntegrityJob, job_id)
        job.finished_at = datetime.now(timezone.utc)
        gateway.record_usage(session)
        await session.commit()


# ── Runners ───────────────────────────────────────────────────────────────────

class JobRunner(Protocol):
    async def submit(self, job_id: UUID, payload: dict | None) -> None: ...


class ArqJobRunner:
    async def submit(self, job_id: UUID, payload: dict | None) -> None:
        from app.core.arq_pool import get_arq_pool

        pool = await get_arq_pool()
        if payload is not None:
            await pool.set(
                PAYLOAD_KEY.format(job_id), json.dumps(payload),
                ex=settings.INTEGRITY_JOB_TIMEOUT_SECONDS,
            )
        await pool.enqueue_job(TASK_NAME, str(job_id), _job_id=f"integrity:{job_id}")


class InlineJobRunner:
    _tasks: set[asyncio.Task] = set()

    async def submit(self, job_id: UUID, payload: dict | None) -> None:
        from app.core.database import AsyncSessionLocal

        task = asyncio.create_task(execute_job(AsyncSessionLocal, build_backend, job_id, payload))
        # Keep a reference so the task is not garbage-collected mid-run.
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


def get_job_runner() -> JobRunner:
    """FastAPI dependency; tests override it to run jobs synchronously."""
    return ArqJobRunner() if settings.INTEGRITY_JOB_RUNNER == "arq" else InlineJobRunner()
