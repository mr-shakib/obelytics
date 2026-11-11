import json
from uuid import UUID

from app.core.database import AsyncSessionLocal
from app.modules.ai.providers import build_backend
from app.modules.integrity.jobs import PAYLOAD_KEY, execute_job


async def run_integrity_job(ctx: dict, job_id: str) -> None:
    # Read and delete in one step: the paper's pages never outlive the job in Redis.
    raw = await ctx["redis"].getdel(PAYLOAD_KEY.format(job_id))
    payload = json.loads(raw) if raw else None
    await execute_job(AsyncSessionLocal, build_backend, UUID(job_id), payload)
