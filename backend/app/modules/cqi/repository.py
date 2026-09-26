from uuid import UUID

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cqi.models import COAttainmentGap, POAttainmentGap
from app.modules.curriculum.models import Curriculum, SectionOffering


class COGapRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _scoped(
        self,
        org_id: UUID,
        program_id: UUID | None,
        academic_term_id: UUID | None,
        status: str | None,
    ) -> Select:
        stmt = select(COAttainmentGap).where(COAttainmentGap.organization_id == org_id)
        if status is not None:
            stmt = stmt.where(COAttainmentGap.status == status)
        # Program and term live on the offering, not the gap — join to filter.
        if program_id is not None or academic_term_id is not None:
            stmt = stmt.join(
                SectionOffering,
                SectionOffering.id == COAttainmentGap.section_offering_id,
            )
            if academic_term_id is not None:
                stmt = stmt.where(SectionOffering.academic_term_id == academic_term_id)
            if program_id is not None:
                stmt = stmt.join(
                    Curriculum, Curriculum.id == SectionOffering.curriculum_id
                ).where(Curriculum.program_id == program_id)
        return stmt

    async def list_gaps(
        self,
        org_id: UUID,
        program_id: UUID | None = None,
        academic_term_id: UUID | None = None,
        status: str | None = None,
    ) -> list[COAttainmentGap]:
        stmt = self._scoped(org_id, program_id, academic_term_id, status).order_by(
            COAttainmentGap.detected_at.desc()
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_by_offering(
        self, org_id: UUID, section_offering_id: UUID
    ) -> list[COAttainmentGap]:
        result = await self._session.execute(
            select(COAttainmentGap)
            .where(
                and_(
                    COAttainmentGap.organization_id == org_id,
                    COAttainmentGap.section_offering_id == section_offering_id,
                )
            )
            .order_by(COAttainmentGap.attainment_pct.asc())
        )
        return list(result.scalars().all())

    async def get(self, org_id: UUID, gap_id: UUID) -> COAttainmentGap | None:
        result = await self._session.execute(
            select(COAttainmentGap).where(
                and_(
                    COAttainmentGap.organization_id == org_id,
                    COAttainmentGap.id == gap_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def count_by_status(
        self,
        org_id: UUID,
        program_id: UUID | None = None,
        academic_term_id: UUID | None = None,
    ) -> dict[str, int]:
        stmt = self._scoped(org_id, program_id, academic_term_id, None).with_only_columns(
            COAttainmentGap.status, func.count()
        ).group_by(COAttainmentGap.status)
        rows = (await self._session.execute(stmt)).all()
        return {status: count for status, count in rows}


class POGapRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _scoped(
        self,
        org_id: UUID,
        program_id: UUID | None,
        academic_term_id: UUID | None,
        status: str | None,
    ) -> Select:
        stmt = select(POAttainmentGap).where(POAttainmentGap.organization_id == org_id)
        if program_id is not None:
            stmt = stmt.where(POAttainmentGap.program_id == program_id)
        if academic_term_id is not None:
            stmt = stmt.where(POAttainmentGap.academic_term_id == academic_term_id)
        if status is not None:
            stmt = stmt.where(POAttainmentGap.status == status)
        return stmt

    async def list_gaps(
        self,
        org_id: UUID,
        program_id: UUID | None = None,
        academic_term_id: UUID | None = None,
        status: str | None = None,
    ) -> list[POAttainmentGap]:
        stmt = self._scoped(org_id, program_id, academic_term_id, status).order_by(
            POAttainmentGap.detected_at.desc()
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get(self, org_id: UUID, gap_id: UUID) -> POAttainmentGap | None:
        result = await self._session.execute(
            select(POAttainmentGap).where(
                and_(
                    POAttainmentGap.organization_id == org_id,
                    POAttainmentGap.id == gap_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def count_by_status(
        self,
        org_id: UUID,
        program_id: UUID | None = None,
        academic_term_id: UUID | None = None,
    ) -> dict[str, int]:
        stmt = self._scoped(org_id, program_id, academic_term_id, None).with_only_columns(
            POAttainmentGap.status, func.count()
        ).group_by(POAttainmentGap.status)
        rows = (await self._session.execute(stmt)).all()
        return {status: count for status, count in rows}
