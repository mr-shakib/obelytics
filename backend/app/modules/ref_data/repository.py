from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ref_data.models import (
    AssessmentType,
    BloomDomain,
    BloomLevel,
    ComplexActivity,
    ComplexProblem,
    CourseCategory,
    DeliveryMethod,
    KnowledgeProfile,
    MappingWeightLabel,
    POType,
)


class _BaseRefRepo:
    _model = None

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self, org_id: UUID):
        result = await self._session.execute(
            select(self._model).where(
                and_(self._model.organization_id == org_id, self._model.is_active.is_(True))
            )
        )
        return list(result.scalars().all())

    async def get_by_id(self, record_id: UUID, org_id: UUID):
        result = await self._session.execute(
            select(self._model).where(
                and_(self._model.id == record_id, self._model.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj):
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj, data: dict):
        for key, value in data.items():
            setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj


class BloomDomainRepository(_BaseRefRepo):
    _model = BloomDomain

    async def find_by_name(self, name: str, org_id: UUID) -> BloomDomain | None:
        result = await self._session.execute(
            select(BloomDomain).where(
                and_(BloomDomain.name == name, BloomDomain.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()


class BloomLevelRepository(_BaseRefRepo):
    _model = BloomLevel

    async def list_by_domain(self, domain_id: UUID, org_id: UUID) -> list[BloomLevel]:
        result = await self._session.execute(
            select(BloomLevel).where(
                and_(
                    BloomLevel.bloom_domain_id == domain_id,
                    BloomLevel.organization_id == org_id,
                    BloomLevel.is_active.is_(True),
                )
            ).order_by(BloomLevel.order_index)
        )
        return list(result.scalars().all())

    async def list_all_active(self, org_id: UUID) -> list[BloomLevel]:
        result = await self._session.execute(
            select(BloomLevel).where(
                and_(BloomLevel.organization_id == org_id, BloomLevel.is_active.is_(True))
            ).order_by(BloomLevel.bloom_domain_id, BloomLevel.order_index)
        )
        return list(result.scalars().all())

    async def find_by_code(self, code: str, domain_id: UUID, org_id: UUID) -> BloomLevel | None:
        result = await self._session.execute(
            select(BloomLevel).where(
                and_(
                    BloomLevel.code == code,
                    BloomLevel.bloom_domain_id == domain_id,
                    BloomLevel.organization_id == org_id,
                )
            )
        )
        return result.scalar_one_or_none()


class DeliveryMethodRepository(_BaseRefRepo):
    _model = DeliveryMethod

    async def find_by_name(self, name: str, org_id: UUID) -> DeliveryMethod | None:
        result = await self._session.execute(
            select(DeliveryMethod).where(
                and_(DeliveryMethod.name == name, DeliveryMethod.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()


class CourseCategoryRepository(_BaseRefRepo):
    _model = CourseCategory

    async def find_by_name(self, name: str, org_id: UUID) -> CourseCategory | None:
        result = await self._session.execute(
            select(CourseCategory).where(
                and_(CourseCategory.name == name, CourseCategory.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()


class AssessmentTypeRepository(_BaseRefRepo):
    _model = AssessmentType

    async def find_by_name(self, name: str, org_id: UUID) -> AssessmentType | None:
        result = await self._session.execute(
            select(AssessmentType).where(
                and_(AssessmentType.name == name, AssessmentType.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()


class ComplexProblemRepository(_BaseRefRepo):
    _model = ComplexProblem

    async def find_by_code(self, code: str, org_id: UUID) -> ComplexProblem | None:
        result = await self._session.execute(
            select(ComplexProblem).where(
                and_(ComplexProblem.code == code, ComplexProblem.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()


class ComplexActivityRepository(_BaseRefRepo):
    _model = ComplexActivity

    async def find_by_code(self, code: str, org_id: UUID) -> ComplexActivity | None:
        result = await self._session.execute(
            select(ComplexActivity).where(
                and_(ComplexActivity.code == code, ComplexActivity.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()


class KnowledgeProfileRepository(_BaseRefRepo):
    _model = KnowledgeProfile

    async def find_by_code(self, code: str, org_id: UUID) -> KnowledgeProfile | None:
        result = await self._session.execute(
            select(KnowledgeProfile).where(
                and_(KnowledgeProfile.code == code, KnowledgeProfile.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()


class POTypeRepository(_BaseRefRepo):
    _model = POType

    async def find_by_name(self, name: str, org_id: UUID) -> POType | None:
        result = await self._session.execute(
            select(POType).where(
                and_(POType.name == name, POType.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()


class MappingWeightLabelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self, org_id: UUID) -> list[MappingWeightLabel]:
        result = await self._session.execute(
            select(MappingWeightLabel).where(
                MappingWeightLabel.organization_id == org_id
            ).order_by(MappingWeightLabel.weight_value)
        )
        return list(result.scalars().all())

    async def get_by_id(self, record_id: UUID, org_id: UUID) -> MappingWeightLabel | None:
        result = await self._session.execute(
            select(MappingWeightLabel).where(
                and_(MappingWeightLabel.id == record_id, MappingWeightLabel.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def find_by_value(self, weight_value: int, org_id: UUID) -> MappingWeightLabel | None:
        result = await self._session.execute(
            select(MappingWeightLabel).where(
                and_(
                    MappingWeightLabel.weight_value == weight_value,
                    MappingWeightLabel.organization_id == org_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: MappingWeightLabel) -> MappingWeightLabel:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: MappingWeightLabel, data: dict) -> MappingWeightLabel:
        for key, value in data.items():
            setattr(obj, key, value)
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj
