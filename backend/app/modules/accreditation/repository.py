from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accreditation.models import (
    AccreditationCriterion,
    AccreditationCycle,
    CriterionPOMapping,
)


class AccreditationCycleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, obj: AccreditationCycle) -> AccreditationCycle:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def get_by_id(self, id: UUID, org_id: UUID) -> AccreditationCycle | None:
        result = await self._session.execute(
            select(AccreditationCycle).where(
                and_(
                    AccreditationCycle.id == id,
                    AccreditationCycle.organization_id == org_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_for_org(
        self, org_id: UUID, program_id: UUID | None = None
    ) -> list[AccreditationCycle]:
        conditions = [AccreditationCycle.organization_id == org_id]
        if program_id is not None:
            conditions.append(AccreditationCycle.program_id == program_id)
        result = await self._session.execute(
            select(AccreditationCycle).where(and_(*conditions))
        )
        return list(result.scalars().all())

    async def update(
        self, obj: AccreditationCycle, data: dict
    ) -> AccreditationCycle:
        for key, value in data.items():
            setattr(obj, key, value)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj


class AccreditationCriterionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, obj: AccreditationCriterion) -> AccreditationCriterion:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def get_by_id(self, id: UUID) -> AccreditationCriterion | None:
        result = await self._session.execute(
            select(AccreditationCriterion).where(AccreditationCriterion.id == id)
        )
        return result.scalar_one_or_none()

    async def list_by_cycle(self, cycle_id: UUID) -> list[AccreditationCriterion]:
        result = await self._session.execute(
            select(AccreditationCriterion)
            .where(AccreditationCriterion.cycle_id == cycle_id)
            .order_by(AccreditationCriterion.order_index)
        )
        return list(result.scalars().all())

    async def update(
        self, obj: AccreditationCriterion, data: dict
    ) -> AccreditationCriterion:
        for key, value in data.items():
            setattr(obj, key, value)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def delete(self, obj: AccreditationCriterion) -> None:
        await self._session.delete(obj)
        await self._session.flush()


class CriterionPOMappingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, obj: CriterionPOMapping) -> CriterionPOMapping:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def list_by_criterion(self, criterion_id: UUID) -> list[CriterionPOMapping]:
        result = await self._session.execute(
            select(CriterionPOMapping).where(
                CriterionPOMapping.criterion_id == criterion_id
            )
        )
        return list(result.scalars().all())

    async def find(
        self, criterion_id: UUID, program_outcome_id: UUID
    ) -> CriterionPOMapping | None:
        result = await self._session.execute(
            select(CriterionPOMapping).where(
                and_(
                    CriterionPOMapping.criterion_id == criterion_id,
                    CriterionPOMapping.program_outcome_id == program_outcome_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, obj: CriterionPOMapping) -> None:
        await self._session.delete(obj)
        await self._session.flush()
