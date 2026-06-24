from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attainment.models import AttainmentConfig, COAttainmentResult, POAttainmentResult


class AttainmentConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_org(self, org_id: UUID) -> AttainmentConfig | None:
        """Get org-wide default config (program_id IS NULL)."""
        result = await self._session.execute(
            select(AttainmentConfig).where(
                and_(
                    AttainmentConfig.organization_id == org_id,
                    AttainmentConfig.program_id.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_for_program(self, org_id: UUID, program_id: UUID) -> AttainmentConfig | None:
        """Get program-specific config."""
        result = await self._session.execute(
            select(AttainmentConfig).where(
                and_(
                    AttainmentConfig.organization_id == org_id,
                    AttainmentConfig.program_id == program_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: AttainmentConfig) -> AttainmentConfig:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: AttainmentConfig, data: dict) -> AttainmentConfig:
        for key, value in data.items():
            setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj


class COAttainmentResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_offering(self, section_offering_id: UUID) -> list[COAttainmentResult]:
        result = await self._session.execute(
            select(COAttainmentResult).where(
                COAttainmentResult.section_offering_id == section_offering_id
            )
        )
        return list(result.scalars().all())

    async def upsert(self, obj: COAttainmentResult) -> COAttainmentResult:
        """Insert or update based on (section_offering_id, course_outcome_id) unique key."""
        stmt = pg_insert(COAttainmentResult).values(
            id=obj.id,
            organization_id=obj.organization_id,
            section_offering_id=obj.section_offering_id,
            course_outcome_id=obj.course_outcome_id,
            average_attainment_pct=obj.average_attainment_pct,
            students_above_threshold=obj.students_above_threshold,
            total_students=obj.total_students,
            is_attained=obj.is_attained,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["section_offering_id", "course_outcome_id"],
            set_={
                "average_attainment_pct": stmt.excluded.average_attainment_pct,
                "students_above_threshold": stmt.excluded.students_above_threshold,
                "total_students": stmt.excluded.total_students,
                "is_attained": stmt.excluded.is_attained,
                "updated_at": stmt.excluded.calculated_at,
            },
        )
        await self._session.execute(stmt)
        # Fetch the persisted row
        result = await self._session.execute(
            select(COAttainmentResult).where(
                and_(
                    COAttainmentResult.section_offering_id == obj.section_offering_id,
                    COAttainmentResult.course_outcome_id == obj.course_outcome_id,
                )
            )
        )
        return result.scalar_one()

    async def delete_by_offering(self, section_offering_id: UUID) -> None:
        result = await self._session.execute(
            select(COAttainmentResult).where(
                COAttainmentResult.section_offering_id == section_offering_id
            )
        )
        for row in result.scalars().all():
            await self._session.delete(row)
        await self._session.flush()


class POAttainmentResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_offering(self, section_offering_id: UUID) -> list[POAttainmentResult]:
        result = await self._session.execute(
            select(POAttainmentResult).where(
                POAttainmentResult.section_offering_id == section_offering_id
            )
        )
        return list(result.scalars().all())

    async def upsert(self, obj: POAttainmentResult) -> POAttainmentResult:
        """Insert or update based on (section_offering_id, program_outcome_id) unique key."""
        stmt = pg_insert(POAttainmentResult).values(
            id=obj.id,
            organization_id=obj.organization_id,
            section_offering_id=obj.section_offering_id,
            program_outcome_id=obj.program_outcome_id,
            attainment_pct=obj.attainment_pct,
            contributing_co_count=obj.contributing_co_count,
            students_above_threshold=obj.students_above_threshold,
            total_students=obj.total_students,
            is_attained=obj.is_attained,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["section_offering_id", "program_outcome_id"],
            set_={
                "attainment_pct": stmt.excluded.attainment_pct,
                "contributing_co_count": stmt.excluded.contributing_co_count,
                "students_above_threshold": stmt.excluded.students_above_threshold,
                "total_students": stmt.excluded.total_students,
                "is_attained": stmt.excluded.is_attained,
                "updated_at": stmt.excluded.calculated_at,
            },
        )
        await self._session.execute(stmt)
        # Fetch the persisted row
        result = await self._session.execute(
            select(POAttainmentResult).where(
                and_(
                    POAttainmentResult.section_offering_id == obj.section_offering_id,
                    POAttainmentResult.program_outcome_id == obj.program_outcome_id,
                )
            )
        )
        return result.scalar_one()

    async def delete_by_offering(self, section_offering_id: UUID) -> None:
        result = await self._session.execute(
            select(POAttainmentResult).where(
                POAttainmentResult.section_offering_id == section_offering_id
            )
        )
        for row in result.scalars().all():
            await self._session.delete(row)
        await self._session.flush()
