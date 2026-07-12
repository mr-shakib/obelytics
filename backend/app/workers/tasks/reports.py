from uuid import UUID

from app.core.database import AsyncSessionLocal
from app.modules.reporting.service import ReportRunService


async def generate_report_run(ctx: dict, run_id: str) -> None:
    async with AsyncSessionLocal() as session:
        svc = ReportRunService(session)
        await svc.execute(UUID(run_id))
