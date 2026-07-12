from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reporting.models import ReportRun


class ReportRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: ReportRun) -> ReportRun:
        self._session.add(run)
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def get_by_id(self, run_id: UUID, org_id: UUID | None = None) -> ReportRun | None:
        stmt = select(ReportRun).where(ReportRun.id == run_id)
        if org_id is not None:
            stmt = stmt.where(ReportRun.organization_id == org_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(self, org_id: UUID, requested_by_user_id: UUID) -> list[ReportRun]:
        result = await self._session.execute(
            select(ReportRun)
            .where(
                and_(
                    ReportRun.organization_id == org_id,
                    ReportRun.requested_by_user_id == requested_by_user_id,
                )
            )
            .order_by(desc(ReportRun.created_at))
        )
        return list(result.scalars().all())

    async def update(self, run: ReportRun, data: dict) -> ReportRun:
        for key, value in data.items():
            setattr(run, key, value)
        self._session.add(run)
        await self._session.flush()
        await self._session.refresh(run)
        return run
