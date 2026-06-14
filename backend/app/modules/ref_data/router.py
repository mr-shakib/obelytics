from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.ref_data.schemas import (
    AssessmentTypeCreate,
    AssessmentTypeResponse,
    AssessmentTypeUpdate,
    BloomDomainCreate,
    BloomDomainResponse,
    BloomDomainUpdate,
    BloomLevelCreate,
    BloomLevelResponse,
    BloomLevelUpdate,
    ComplexActivityCreate,
    ComplexActivityResponse,
    ComplexActivityUpdate,
    ComplexProblemCreate,
    ComplexProblemResponse,
    ComplexProblemUpdate,
    CourseCategoryCreate,
    CourseCategoryResponse,
    CourseCategoryUpdate,
    DeliveryMethodCreate,
    DeliveryMethodResponse,
    DeliveryMethodUpdate,
    KnowledgeProfileCreate,
    KnowledgeProfileResponse,
    KnowledgeProfileUpdate,
    MappingWeightLabelCreate,
    MappingWeightLabelResponse,
    MappingWeightLabelUpdate,
    POTypeCreate,
    POTypeResponse,
    POTypeUpdate,
)
from app.modules.ref_data.service import (
    AssessmentTypeService,
    BloomDomainService,
    BloomLevelService,
    ComplexActivityService,
    ComplexProblemService,
    CourseCategoryService,
    DeliveryMethodService,
    KnowledgeProfileService,
    MappingWeightLabelService,
    POTypeService,
)

router = APIRouter(prefix="/ref-data", tags=["Reference Data"])

_manage = require_permission("config.manage")


# ── Bloom Domains ─────────────────────────────────────────────────────────────

@router.get("/bloom-domains", response_model=list[BloomDomainResponse])
async def list_bloom_domains(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await BloomDomainService(db).list_active(current_user.organization_id)


@router.post("/bloom-domains", response_model=BloomDomainResponse, status_code=status.HTTP_201_CREATED)
async def create_bloom_domain(
    body: BloomDomainCreate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await BloomDomainService(db).create(body, current_user.organization_id)


@router.patch("/bloom-domains/{record_id}", response_model=BloomDomainResponse)
async def update_bloom_domain(
    record_id: UUID,
    body: BloomDomainUpdate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await BloomDomainService(db).update(record_id, body, current_user.organization_id)


# ── Bloom Levels ──────────────────────────────────────────────────────────────

@router.get("/bloom-levels", response_model=list[BloomLevelResponse])
async def list_all_bloom_levels(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await BloomLevelService(db).list_all_active(current_user.organization_id)


@router.get("/bloom-domains/{domain_id}/levels", response_model=list[BloomLevelResponse])
async def list_bloom_levels(
    domain_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await BloomLevelService(db).list_by_domain(domain_id, current_user.organization_id)


@router.post("/bloom-levels", response_model=BloomLevelResponse, status_code=status.HTTP_201_CREATED)
async def create_bloom_level(
    body: BloomLevelCreate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await BloomLevelService(db).create(body, current_user.organization_id)


@router.patch("/bloom-levels/{record_id}", response_model=BloomLevelResponse)
async def update_bloom_level(
    record_id: UUID,
    body: BloomLevelUpdate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await BloomLevelService(db).update(record_id, body, current_user.organization_id)


# ── Delivery Methods ──────────────────────────────────────────────────────────

@router.get("/delivery-methods", response_model=list[DeliveryMethodResponse])
async def list_delivery_methods(
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await DeliveryMethodService(db).list_active(current_user.organization_id)


@router.post("/delivery-methods", response_model=DeliveryMethodResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery_method(
    body: DeliveryMethodCreate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await DeliveryMethodService(db).create(body, current_user.organization_id)


@router.patch("/delivery-methods/{record_id}", response_model=DeliveryMethodResponse)
async def update_delivery_method(
    record_id: UUID,
    body: DeliveryMethodUpdate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await DeliveryMethodService(db).update(record_id, body, current_user.organization_id)


# ── Course Categories ─────────────────────────────────────────────────────────

@router.get("/course-categories", response_model=list[CourseCategoryResponse])
async def list_course_categories(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await CourseCategoryService(db).list_active(current_user.organization_id)


@router.post("/course-categories", response_model=CourseCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_course_category(
    body: CourseCategoryCreate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await CourseCategoryService(db).create(body, current_user.organization_id)


@router.patch("/course-categories/{record_id}", response_model=CourseCategoryResponse)
async def update_course_category(
    record_id: UUID,
    body: CourseCategoryUpdate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await CourseCategoryService(db).update(record_id, body, current_user.organization_id)


# ── Assessment Types ──────────────────────────────────────────────────────────

@router.get("/assessment-types", response_model=list[AssessmentTypeResponse])
async def list_assessment_types(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await AssessmentTypeService(db).list_active(current_user.organization_id)


@router.post("/assessment-types", response_model=AssessmentTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment_type(
    body: AssessmentTypeCreate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await AssessmentTypeService(db).create(body, current_user.organization_id)


@router.patch("/assessment-types/{record_id}", response_model=AssessmentTypeResponse)
async def update_assessment_type(
    record_id: UUID,
    body: AssessmentTypeUpdate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await AssessmentTypeService(db).update(record_id, body, current_user.organization_id)


# ── Complex Problems ──────────────────────────────────────────────────────────

@router.get("/complex-problems", response_model=list[ComplexProblemResponse])
async def list_complex_problems(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await ComplexProblemService(db).list_active(current_user.organization_id)


@router.post("/complex-problems", response_model=ComplexProblemResponse, status_code=status.HTTP_201_CREATED)
async def create_complex_problem(
    body: ComplexProblemCreate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await ComplexProblemService(db).create(body, current_user.organization_id)


@router.patch("/complex-problems/{record_id}", response_model=ComplexProblemResponse)
async def update_complex_problem(
    record_id: UUID,
    body: ComplexProblemUpdate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await ComplexProblemService(db).update(record_id, body, current_user.organization_id)


# ── Complex Activities ────────────────────────────────────────────────────────

@router.get("/complex-activities", response_model=list[ComplexActivityResponse])
async def list_complex_activities(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await ComplexActivityService(db).list_active(current_user.organization_id)


@router.post("/complex-activities", response_model=ComplexActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_complex_activity(
    body: ComplexActivityCreate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await ComplexActivityService(db).create(body, current_user.organization_id)


@router.patch("/complex-activities/{record_id}", response_model=ComplexActivityResponse)
async def update_complex_activity(
    record_id: UUID,
    body: ComplexActivityUpdate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await ComplexActivityService(db).update(record_id, body, current_user.organization_id)


# ── Knowledge Profiles ────────────────────────────────────────────────────────

@router.get("/knowledge-profiles", response_model=list[KnowledgeProfileResponse])
async def list_knowledge_profiles(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await KnowledgeProfileService(db).list_active(current_user.organization_id)


@router.post("/knowledge-profiles", response_model=KnowledgeProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_profile(
    body: KnowledgeProfileCreate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await KnowledgeProfileService(db).create(body, current_user.organization_id)


@router.patch("/knowledge-profiles/{record_id}", response_model=KnowledgeProfileResponse)
async def update_knowledge_profile(
    record_id: UUID,
    body: KnowledgeProfileUpdate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await KnowledgeProfileService(db).update(record_id, body, current_user.organization_id)


# ── PO Types ──────────────────────────────────────────────────────────────────

@router.get("/po-types", response_model=list[POTypeResponse])
async def list_po_types(
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await POTypeService(db).list_active(current_user.organization_id)


@router.post("/po-types", response_model=POTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_po_type(
    body: POTypeCreate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await POTypeService(db).create(body, current_user.organization_id)


@router.patch("/po-types/{record_id}", response_model=POTypeResponse)
async def update_po_type(
    record_id: UUID,
    body: POTypeUpdate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await POTypeService(db).update(record_id, body, current_user.organization_id)


# ── Mapping Weight Labels ─────────────────────────────────────────────────────

@router.get("/mapping-weights", response_model=list[MappingWeightLabelResponse])
async def list_mapping_weights(
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await MappingWeightLabelService(db).list_all(current_user.organization_id)


@router.post("/mapping-weights", response_model=MappingWeightLabelResponse, status_code=status.HTTP_201_CREATED)
async def create_mapping_weight(
    body: MappingWeightLabelCreate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await MappingWeightLabelService(db).create(body, current_user.organization_id)


@router.patch("/mapping-weights/{record_id}", response_model=MappingWeightLabelResponse)
async def update_mapping_weight(
    record_id: UUID,
    body: MappingWeightLabelUpdate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await MappingWeightLabelService(db).update(record_id, body, current_user.organization_id)
