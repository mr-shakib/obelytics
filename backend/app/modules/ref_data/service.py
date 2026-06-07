import json
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis
from app.modules.ref_data.exceptions import RefDataConflictError, RefDataNotFoundError
from app.modules.ref_data.models import (
    AssessmentType,
    BloomDomain,
    BloomLevel,
    ComplexActivity,
    ComplexProblem,
    CourseType,
    DeliveryMethod,
    KnowledgeProfile,
    MappingWeightLabel,
    POType,
)
from app.modules.ref_data.repository import (
    AssessmentTypeRepository,
    BloomDomainRepository,
    BloomLevelRepository,
    ComplexActivityRepository,
    ComplexProblemRepository,
    CourseTypeRepository,
    DeliveryMethodRepository,
    KnowledgeProfileRepository,
    MappingWeightLabelRepository,
    POTypeRepository,
)
from app.modules.ref_data.schemas import (
    AssessmentTypeCreate,
    AssessmentTypeUpdate,
    BloomDomainCreate,
    BloomDomainUpdate,
    BloomLevelCreate,
    BloomLevelUpdate,
    ComplexActivityCreate,
    ComplexActivityUpdate,
    ComplexProblemCreate,
    ComplexProblemUpdate,
    CourseTypeCreate,
    CourseTypeUpdate,
    DeliveryMethodCreate,
    DeliveryMethodUpdate,
    KnowledgeProfileCreate,
    KnowledgeProfileUpdate,
    MappingWeightLabelCreate,
    MappingWeightLabelUpdate,
    POTypeCreate,
    POTypeUpdate,
)

_CACHE_TTL = 3600  # 1 hour


def _cache_key(org_id: UUID, ref_type: str) -> str:
    return f"ref_data:{org_id}:{ref_type}"


async def _invalidate(org_id: UUID, ref_type: str) -> None:
    redis = await get_redis()
    await redis.delete(_cache_key(org_id, ref_type))


class BloomDomainService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = BloomDomainRepository(session)

    async def list_active(self, org_id: UUID) -> list[BloomDomain]:
        return await self._repo.list_active(org_id)

    async def get(self, record_id: UUID, org_id: UUID) -> BloomDomain:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Bloom domain")
        return obj

    async def create(self, body: BloomDomainCreate, org_id: UUID) -> BloomDomain:
        if await self._repo.find_by_name(body.name, org_id):
            raise RefDataConflictError("A bloom domain with this name already exists")
        obj = BloomDomain(organization_id=org_id, name=body.name, description=body.description)
        result = await self._repo.create(obj)
        await _invalidate(org_id, "bloom_domains")
        return result

    async def update(self, record_id: UUID, body: BloomDomainUpdate, org_id: UUID) -> BloomDomain:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Bloom domain")
        data = body.model_dump(exclude_none=True)
        if "name" in data and data["name"] != obj.name:
            if await self._repo.find_by_name(data["name"], org_id):
                raise RefDataConflictError("A bloom domain with this name already exists")
        result = await self._repo.update(obj, data)
        await _invalidate(org_id, "bloom_domains")
        return result


class BloomLevelService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = BloomLevelRepository(session)

    async def list_by_domain(self, domain_id: UUID, org_id: UUID) -> list[BloomLevel]:
        return await self._repo.list_by_domain(domain_id, org_id)

    async def get(self, record_id: UUID, org_id: UUID) -> BloomLevel:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Bloom level")
        return obj

    async def create(self, body: BloomLevelCreate, org_id: UUID) -> BloomLevel:
        if await self._repo.find_by_code(body.code, body.bloom_domain_id, org_id):
            raise RefDataConflictError("A bloom level with this code already exists in the domain")
        obj = BloomLevel(
            organization_id=org_id,
            bloom_domain_id=body.bloom_domain_id,
            code=body.code,
            name=body.name,
            order_index=body.order_index,
        )
        result = await self._repo.create(obj)
        await _invalidate(org_id, "bloom_levels")
        return result

    async def update(self, record_id: UUID, body: BloomLevelUpdate, org_id: UUID) -> BloomLevel:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Bloom level")
        data = body.model_dump(exclude_none=True)
        if "code" in data and data["code"] != obj.code:
            if await self._repo.find_by_code(data["code"], obj.bloom_domain_id, org_id):
                raise RefDataConflictError("A bloom level with this code already exists in the domain")
        result = await self._repo.update(obj, data)
        await _invalidate(org_id, "bloom_levels")
        return result


class DeliveryMethodService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = DeliveryMethodRepository(session)

    async def list_active(self, org_id: UUID) -> list[DeliveryMethod]:
        return await self._repo.list_active(org_id)

    async def get(self, record_id: UUID, org_id: UUID) -> DeliveryMethod:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Delivery method")
        return obj

    async def create(self, body: DeliveryMethodCreate, org_id: UUID) -> DeliveryMethod:
        if await self._repo.find_by_name(body.name, org_id):
            raise RefDataConflictError("A delivery method with this name already exists")
        obj = DeliveryMethod(organization_id=org_id, name=body.name, description=body.description)
        result = await self._repo.create(obj)
        await _invalidate(org_id, "delivery_methods")
        return result

    async def update(self, record_id: UUID, body: DeliveryMethodUpdate, org_id: UUID) -> DeliveryMethod:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Delivery method")
        data = body.model_dump(exclude_none=True)
        if "name" in data and data["name"] != obj.name:
            if await self._repo.find_by_name(data["name"], org_id):
                raise RefDataConflictError("A delivery method with this name already exists")
        result = await self._repo.update(obj, data)
        await _invalidate(org_id, "delivery_methods")
        return result


class CourseTypeService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = CourseTypeRepository(session)

    async def list_active(self, org_id: UUID) -> list[CourseType]:
        return await self._repo.list_active(org_id)

    async def get(self, record_id: UUID, org_id: UUID) -> CourseType:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Course type")
        return obj

    async def create(self, body: CourseTypeCreate, org_id: UUID) -> CourseType:
        if await self._repo.find_by_name(body.name, org_id):
            raise RefDataConflictError("A course type with this name already exists")
        obj = CourseType(organization_id=org_id, name=body.name, description=body.description)
        result = await self._repo.create(obj)
        await _invalidate(org_id, "course_types")
        return result

    async def update(self, record_id: UUID, body: CourseTypeUpdate, org_id: UUID) -> CourseType:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Course type")
        data = body.model_dump(exclude_none=True)
        if "name" in data and data["name"] != obj.name:
            if await self._repo.find_by_name(data["name"], org_id):
                raise RefDataConflictError("A course type with this name already exists")
        result = await self._repo.update(obj, data)
        await _invalidate(org_id, "course_types")
        return result


class AssessmentTypeService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AssessmentTypeRepository(session)

    async def list_active(self, org_id: UUID) -> list[AssessmentType]:
        return await self._repo.list_active(org_id)

    async def get(self, record_id: UUID, org_id: UUID) -> AssessmentType:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Assessment type")
        return obj

    async def create(self, body: AssessmentTypeCreate, org_id: UUID) -> AssessmentType:
        if await self._repo.find_by_name(body.name, org_id):
            raise RefDataConflictError("An assessment type with this name already exists")
        obj = AssessmentType(organization_id=org_id, name=body.name, is_sessional=body.is_sessional)
        result = await self._repo.create(obj)
        await _invalidate(org_id, "assessment_types")
        return result

    async def update(self, record_id: UUID, body: AssessmentTypeUpdate, org_id: UUID) -> AssessmentType:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Assessment type")
        data = body.model_dump(exclude_none=True)
        if "name" in data and data["name"] != obj.name:
            if await self._repo.find_by_name(data["name"], org_id):
                raise RefDataConflictError("An assessment type with this name already exists")
        result = await self._repo.update(obj, data)
        await _invalidate(org_id, "assessment_types")
        return result


class ComplexProblemService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ComplexProblemRepository(session)

    async def list_active(self, org_id: UUID) -> list[ComplexProblem]:
        return await self._repo.list_active(org_id)

    async def get(self, record_id: UUID, org_id: UUID) -> ComplexProblem:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Complex problem")
        return obj

    async def create(self, body: ComplexProblemCreate, org_id: UUID) -> ComplexProblem:
        if await self._repo.find_by_code(body.code, org_id):
            raise RefDataConflictError("A complex problem with this code already exists")
        obj = ComplexProblem(organization_id=org_id, code=body.code, name=body.name, description=body.description)
        result = await self._repo.create(obj)
        await _invalidate(org_id, "complex_problems")
        return result

    async def update(self, record_id: UUID, body: ComplexProblemUpdate, org_id: UUID) -> ComplexProblem:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Complex problem")
        data = body.model_dump(exclude_none=True)
        if "code" in data and data["code"] != obj.code:
            if await self._repo.find_by_code(data["code"], org_id):
                raise RefDataConflictError("A complex problem with this code already exists")
        result = await self._repo.update(obj, data)
        await _invalidate(org_id, "complex_problems")
        return result


class ComplexActivityService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ComplexActivityRepository(session)

    async def list_active(self, org_id: UUID) -> list[ComplexActivity]:
        return await self._repo.list_active(org_id)

    async def get(self, record_id: UUID, org_id: UUID) -> ComplexActivity:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Complex activity")
        return obj

    async def create(self, body: ComplexActivityCreate, org_id: UUID) -> ComplexActivity:
        if await self._repo.find_by_code(body.code, org_id):
            raise RefDataConflictError("A complex activity with this code already exists")
        obj = ComplexActivity(organization_id=org_id, code=body.code, name=body.name, description=body.description)
        result = await self._repo.create(obj)
        await _invalidate(org_id, "complex_activities")
        return result

    async def update(self, record_id: UUID, body: ComplexActivityUpdate, org_id: UUID) -> ComplexActivity:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Complex activity")
        data = body.model_dump(exclude_none=True)
        if "code" in data and data["code"] != obj.code:
            if await self._repo.find_by_code(data["code"], org_id):
                raise RefDataConflictError("A complex activity with this code already exists")
        result = await self._repo.update(obj, data)
        await _invalidate(org_id, "complex_activities")
        return result


class KnowledgeProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = KnowledgeProfileRepository(session)

    async def list_active(self, org_id: UUID) -> list[KnowledgeProfile]:
        return await self._repo.list_active(org_id)

    async def get(self, record_id: UUID, org_id: UUID) -> KnowledgeProfile:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Knowledge profile")
        return obj

    async def create(self, body: KnowledgeProfileCreate, org_id: UUID) -> KnowledgeProfile:
        if await self._repo.find_by_code(body.code, org_id):
            raise RefDataConflictError("A knowledge profile with this code already exists")
        obj = KnowledgeProfile(organization_id=org_id, code=body.code, description=body.description)
        result = await self._repo.create(obj)
        await _invalidate(org_id, "knowledge_profiles")
        return result

    async def update(self, record_id: UUID, body: KnowledgeProfileUpdate, org_id: UUID) -> KnowledgeProfile:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Knowledge profile")
        data = body.model_dump(exclude_none=True)
        if "code" in data and data["code"] != obj.code:
            if await self._repo.find_by_code(data["code"], org_id):
                raise RefDataConflictError("A knowledge profile with this code already exists")
        result = await self._repo.update(obj, data)
        await _invalidate(org_id, "knowledge_profiles")
        return result


class POTypeService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = POTypeRepository(session)

    async def list_active(self, org_id: UUID) -> list[POType]:
        return await self._repo.list_active(org_id)

    async def get(self, record_id: UUID, org_id: UUID) -> POType:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("PO type")
        return obj

    async def create(self, body: POTypeCreate, org_id: UUID) -> POType:
        if await self._repo.find_by_name(body.name, org_id):
            raise RefDataConflictError("A PO type with this name already exists")
        obj = POType(organization_id=org_id, name=body.name, description=body.description)
        result = await self._repo.create(obj)
        await _invalidate(org_id, "po_types")
        return result

    async def update(self, record_id: UUID, body: POTypeUpdate, org_id: UUID) -> POType:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("PO type")
        data = body.model_dump(exclude_none=True)
        if "name" in data and data["name"] != obj.name:
            if await self._repo.find_by_name(data["name"], org_id):
                raise RefDataConflictError("A PO type with this name already exists")
        result = await self._repo.update(obj, data)
        await _invalidate(org_id, "po_types")
        return result


class MappingWeightLabelService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = MappingWeightLabelRepository(session)

    async def list_all(self, org_id: UUID) -> list[MappingWeightLabel]:
        return await self._repo.list_all(org_id)

    async def get(self, record_id: UUID, org_id: UUID) -> MappingWeightLabel:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Mapping weight label")
        return obj

    async def create(self, body: MappingWeightLabelCreate, org_id: UUID) -> MappingWeightLabel:
        if await self._repo.find_by_value(body.weight_value, org_id):
            raise RefDataConflictError(f"A mapping weight label for value {body.weight_value} already exists")
        obj = MappingWeightLabel(organization_id=org_id, weight_value=body.weight_value, label=body.label)
        result = await self._repo.create(obj)
        await _invalidate(org_id, "mapping_weight_labels")
        return result

    async def update(self, record_id: UUID, body: MappingWeightLabelUpdate, org_id: UUID) -> MappingWeightLabel:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Mapping weight label")
        data = body.model_dump(exclude_none=True)
        result = await self._repo.update(obj, data)
        await _invalidate(org_id, "mapping_weight_labels")
        return result
