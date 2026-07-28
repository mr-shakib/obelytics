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
    CourseCategory,
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
    CourseCategoryRepository,
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
    CourseCategoryCreate,
    CourseCategoryUpdate,
    DeliveryMethodCreate,
    DeliveryMethodUpdate,
    KnowledgeProfileCreate,
    KnowledgeProfileUpdate,
    MappingWeightLabelCreate,
    MappingWeightLabelUpdate,
    POTypeCreate,
    POTypeUpdate,
    RefDataBulkImportError,
    RefDataBulkImportItem,
    RefDataBulkImportResponse,
)

_CACHE_TTL = 3600  # 1 hour


def _cache_key(org_id: UUID, ref_type: str) -> str:
    return f"ref_data:{org_id}:{ref_type}"


async def _invalidate(org_id: UUID, ref_type: str) -> None:
    redis = await get_redis()
    await redis.delete(_cache_key(org_id, ref_type))


async def _bulk_import_coded(
    repo,
    model,
    items: list[RefDataBulkImportItem],
    org_id: UUID,
    *,
    entity_label: str,
    ref_type: str,
    has_name: bool,
) -> RefDataBulkImportResponse:
    """Import code/description reference records, collecting per-row errors.

    Shared by the attribute lists (CEP, complex activities, knowledge profiles),
    which all key off a short code and carry a free-text description.
    """
    created = 0
    errors: list[RefDataBulkImportError] = []
    seen_codes: set[str] = set()

    for index, item in enumerate(items):
        row = index + 1
        code = (item.code or "").strip()
        description = (item.description or "").strip()
        name = (item.name or "").strip()

        if not code or not description:
            errors.append(
                RefDataBulkImportError(
                    row=row, code=code, message="Code and description are required"
                )
            )
            continue
        if len(code) > 20:
            errors.append(
                RefDataBulkImportError(
                    row=row, code=code, message="Code must be 20 characters or fewer"
                )
            )
            continue
        if has_name and len(name) > 150:
            errors.append(
                RefDataBulkImportError(
                    row=row, code=code, message="Name must be 150 characters or fewer"
                )
            )
            continue
        if code.lower() in seen_codes:
            errors.append(
                RefDataBulkImportError(row=row, code=code, message="Duplicate code in this import")
            )
            continue
        seen_codes.add(code.lower())

        if await repo.find_by_code(code, org_id):
            errors.append(
                RefDataBulkImportError(
                    row=row, code=code, message=f"A {entity_label} with this code already exists"
                )
            )
            continue

        values = {"organization_id": org_id, "code": code, "description": description}
        if has_name:
            values["name"] = name or None
        await repo.create(model(**values))
        created += 1

    if created:
        await _invalidate(org_id, ref_type)
    return RefDataBulkImportResponse(created=created, errors=errors)


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

    async def list_all_active(self, org_id: UUID) -> list[BloomLevel]:
        return await self._repo.list_all_active(org_id)

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


class CourseCategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = CourseCategoryRepository(session)

    async def list_active(self, org_id: UUID) -> list[CourseCategory]:
        return await self._repo.list_active(org_id)

    async def get(self, record_id: UUID, org_id: UUID) -> CourseCategory:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Course category")
        return obj

    async def create(self, body: CourseCategoryCreate, org_id: UUID) -> CourseCategory:
        if await self._repo.find_by_name(body.name, org_id):
            raise RefDataConflictError("A course category with this name already exists")
        obj = CourseCategory(organization_id=org_id, name=body.name, description=body.description)
        result = await self._repo.create(obj)
        await _invalidate(org_id, "course_categories")
        return result

    async def update(self, record_id: UUID, body: CourseCategoryUpdate, org_id: UUID) -> CourseCategory:
        obj = await self._repo.get_by_id(record_id, org_id)
        if obj is None:
            raise RefDataNotFoundError("Course category")
        data = body.model_dump(exclude_none=True)
        if "name" in data and data["name"] != obj.name:
            if await self._repo.find_by_name(data["name"], org_id):
                raise RefDataConflictError("A course category with this name already exists")
        result = await self._repo.update(obj, data)
        await _invalidate(org_id, "course_categories")
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

    async def bulk_import(
        self, items: list[RefDataBulkImportItem], org_id: UUID
    ) -> RefDataBulkImportResponse:
        return await _bulk_import_coded(
            self._repo,
            ComplexProblem,
            items,
            org_id,
            entity_label="complex problem",
            ref_type="complex_problems",
            has_name=True,
        )


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

    async def bulk_import(
        self, items: list[RefDataBulkImportItem], org_id: UUID
    ) -> RefDataBulkImportResponse:
        return await _bulk_import_coded(
            self._repo,
            ComplexActivity,
            items,
            org_id,
            entity_label="complex activity",
            ref_type="complex_activities",
            has_name=True,
        )


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

    async def bulk_import(
        self, items: list[RefDataBulkImportItem], org_id: UUID
    ) -> RefDataBulkImportResponse:
        return await _bulk_import_coded(
            self._repo,
            KnowledgeProfile,
            items,
            org_id,
            entity_label="knowledge profile",
            ref_type="knowledge_profiles",
            has_name=False,
        )


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
