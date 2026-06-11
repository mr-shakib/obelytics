from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.obe.schemas import (
    COCAMappingCreate,
    COCAMappingResponse,
    COCPMappingCreate,
    COCPMappingResponse,
    CODeliveryMethodCreate,
    CODeliveryMethodResponse,
    COKPMappingCreate,
    COKPMappingResponse,
    COPOMappingEntryUpsert,
    COPOMappingEntryResponse,
    COPOMappingSetCreate,
    COPOMappingSetResponse,
    COPOMappingValidationResponse,
    CourseOutcomeCreate,
    CourseOutcomeResponse,
    CourseOutcomeUpdate,
    POKnowledgeProfileCreate,
    POKnowledgeProfileResponse,
    ProgramOutcomeCreate,
    ProgramOutcomeResponse,
    ProgramOutcomeUpdate,
)
from app.modules.obe.service import (
    COCAMappingService,
    COCPMappingService,
    CODeliveryMethodService,
    COKPMappingService,
    COService,
    MappingSetService,
    POKnowledgeProfileService,
    POService,
)

router = APIRouter(tags=["OBE"])


# ── Program Outcomes ──────────────────────────────────────────────────────────

@router.get("/program-outcomes", response_model=list[ProgramOutcomeResponse])
async def list_program_outcomes(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("po.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    program_id: UUID | None = None,
):
    svc = POService(db)
    return await svc.list_active(current_user.organization_id, program_id)


@router.post("/program-outcomes", response_model=ProgramOutcomeResponse, status_code=status.HTTP_201_CREATED)
async def create_program_outcome(
    body: ProgramOutcomeCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("po.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = POService(db)
    return await svc.create(body, current_user.organization_id)


@router.get("/program-outcomes/{po_id}", response_model=ProgramOutcomeResponse)
async def get_program_outcome(
    po_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("po.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = POService(db)
    return await svc.get(po_id, current_user.organization_id)


@router.patch("/program-outcomes/{po_id}", response_model=ProgramOutcomeResponse)
async def update_program_outcome(
    po_id: UUID,
    body: ProgramOutcomeUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("po.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = POService(db)
    return await svc.update(po_id, body, current_user.organization_id)


@router.post("/program-outcomes/{po_id}/archive", response_model=ProgramOutcomeResponse)
async def archive_program_outcome(
    po_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("po.archive"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = POService(db)
    return await svc.archive(po_id, current_user.organization_id)


@router.post(
    "/program-outcomes/{po_id}/knowledge-profiles",
    response_model=POKnowledgeProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_po_knowledge_profile(
    po_id: UUID,
    body: POKnowledgeProfileCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("po.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = POKnowledgeProfileService(db)
    return await svc.add(po_id, body.knowledge_profile_id, current_user.organization_id)


@router.get("/program-outcomes/{po_id}/knowledge-profiles", response_model=list[POKnowledgeProfileResponse])
async def list_po_knowledge_profiles(
    po_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("po.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = POKnowledgeProfileService(db)
    return await svc.list_by_po(po_id, current_user.organization_id)


@router.delete(
    "/program-outcomes/{po_id}/knowledge-profiles/{kp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_po_knowledge_profile(
    po_id: UUID,
    kp_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("po.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = POKnowledgeProfileService(db)
    await svc.remove(po_id, kp_id, current_user.organization_id)


# ── Course Outcomes ───────────────────────────────────────────────────────────

@router.get("/course-outcomes", response_model=list[CourseOutcomeResponse])
async def list_course_outcomes(
    curriculum_id: UUID,
    course_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COService(db)
    return await svc.list_by_curriculum_course(curriculum_id, course_id, current_user.organization_id)


@router.post("/course-outcomes", response_model=CourseOutcomeResponse, status_code=status.HTTP_201_CREATED)
async def create_course_outcome(
    body: CourseOutcomeCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COService(db)
    return await svc.create(body, current_user.organization_id, current_user.id)


@router.delete("/course-outcomes/{co_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course_outcome(
    co_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COService(db)
    await svc.delete(co_id, current_user.organization_id)


@router.get("/course-outcomes/{co_id}", response_model=CourseOutcomeResponse)
async def get_course_outcome(
    co_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COService(db)
    return await svc.get(co_id, current_user.organization_id)


@router.patch("/course-outcomes/{co_id}", response_model=CourseOutcomeResponse)
async def update_course_outcome(
    co_id: UUID,
    body: CourseOutcomeUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COService(db)
    return await svc.update(co_id, body, current_user.organization_id)


@router.post("/course-outcomes/{co_id}/submit", response_model=CourseOutcomeResponse)
async def submit_course_outcome(
    co_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.submit"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COService(db)
    return await svc.submit(co_id, current_user.organization_id, current_user.id)


@router.post("/course-outcomes/{co_id}/approve", response_model=CourseOutcomeResponse)
async def approve_course_outcome(
    co_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.approve"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COService(db)
    return await svc.approve(co_id, current_user.organization_id, current_user.id)


@router.post("/course-outcomes/{co_id}/reject", response_model=CourseOutcomeResponse)
async def reject_course_outcome(
    co_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.approve"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COService(db)
    return await svc.reject(co_id, current_user.organization_id, current_user.id)


@router.post("/course-outcomes/{co_id}/publish", response_model=CourseOutcomeResponse)
async def publish_course_outcome(
    co_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.publish"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COService(db)
    return await svc.publish(co_id, current_user.organization_id, current_user.id)


@router.post(
    "/course-outcomes/{co_id}/delivery-methods",
    response_model=CODeliveryMethodResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_co_delivery_method(
    co_id: UUID,
    body: CODeliveryMethodCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CODeliveryMethodService(db)
    return await svc.add(co_id, body.delivery_method_id, current_user.organization_id)


@router.get("/course-outcomes/{co_id}/delivery-methods", response_model=list[CODeliveryMethodResponse])
async def list_co_delivery_methods(
    co_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CODeliveryMethodService(db)
    return await svc.list_by_co(co_id, current_user.organization_id)


@router.delete(
    "/course-outcomes/{co_id}/delivery-methods/{dm_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_co_delivery_method(
    co_id: UUID,
    dm_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CODeliveryMethodService(db)
    await svc.remove(co_id, dm_id, current_user.organization_id)


# ── CO-PO Mapping Sets ────────────────────────────────────────────────────────

@router.get("/mappings/co-po", response_model=COPOMappingSetResponse)
async def get_co_po_mapping_set(
    curriculum_id: UUID,
    course_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_po.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MappingSetService(db)
    ms = await svc._repo.find_by_curriculum_course(curriculum_id, course_id)
    if ms is None:
        from app.modules.obe.exceptions import MappingSetNotFoundError
        raise MappingSetNotFoundError()
    return ms


@router.post(
    "/mappings/co-po",
    response_model=COPOMappingSetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_co_po_mapping_set(
    body: COPOMappingSetCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_po.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MappingSetService(db)
    return await svc.get_or_create(
        body.curriculum_id, body.course_id, current_user.organization_id, current_user.id
    )


@router.get("/mappings/co-po/{set_id}", response_model=COPOMappingSetResponse)
async def get_co_po_mapping_set_by_id(
    set_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_po.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MappingSetService(db)
    return await svc.get(set_id, current_user.organization_id)


@router.get("/mappings/co-po/{set_id}/entries", response_model=list[COPOMappingEntryResponse])
async def list_co_po_mapping_entries(
    set_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_po.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MappingSetService(db)
    return await svc.list_entries(set_id, current_user.organization_id)


@router.put("/mappings/co-po/{set_id}/entries", response_model=list[COPOMappingEntryResponse])
async def upsert_co_po_mapping_entries(
    set_id: UUID,
    entries: list[COPOMappingEntryUpsert],
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_po.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MappingSetService(db)
    return await svc.upsert_entries(set_id, entries, current_user.organization_id)


@router.get("/mappings/co-po/{set_id}/validate", response_model=COPOMappingValidationResponse)
async def validate_co_po_mapping_set(
    set_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_po.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MappingSetService(db)
    return await svc.validate(set_id, current_user.organization_id)


@router.post("/mappings/co-po/{set_id}/publish", response_model=COPOMappingSetResponse)
async def publish_co_po_mapping_set(
    set_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_po.publish"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MappingSetService(db)
    return await svc.publish(set_id, current_user.organization_id, current_user.id)


# ── CO-CP Mappings ────────────────────────────────────────────────────────────

@router.get("/mappings/co-cp", response_model=list[COCPMappingResponse])
async def list_co_cp_mappings(
    course_outcome_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COCPMappingService(db)
    return await svc.list_by_co(course_outcome_id, current_user.organization_id)


@router.post("/mappings/co-cp", response_model=COCPMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_co_cp_mapping(
    body: COCPMappingCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_cp.manage"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COCPMappingService(db)
    return await svc.create(body, current_user.organization_id, current_user.id)


@router.post("/mappings/co-cp/{mapping_id}/approve", response_model=COCPMappingResponse)
async def approve_co_cp_mapping(
    mapping_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_cp.approve"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COCPMappingService(db)
    return await svc.approve(mapping_id, current_user.organization_id, current_user.id)


@router.delete("/mappings/co-cp/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_co_cp_mapping(
    mapping_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_cp.manage"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COCPMappingService(db)
    await svc.remove(mapping_id, current_user.organization_id)


# ── CO-CA Mappings ────────────────────────────────────────────────────────────

@router.get("/mappings/co-ca", response_model=list[COCAMappingResponse])
async def list_co_ca_mappings(
    course_outcome_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COCAMappingService(db)
    return await svc.list_by_co(course_outcome_id, current_user.organization_id)


@router.post("/mappings/co-ca", response_model=COCAMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_co_ca_mapping(
    body: COCAMappingCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_ca.manage"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COCAMappingService(db)
    return await svc.create(body, current_user.organization_id, current_user.id)


@router.post("/mappings/co-ca/{mapping_id}/approve", response_model=COCAMappingResponse)
async def approve_co_ca_mapping(
    mapping_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_ca.approve"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COCAMappingService(db)
    return await svc.approve(mapping_id, current_user.organization_id, current_user.id)


@router.delete("/mappings/co-ca/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_co_ca_mapping(
    mapping_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_ca.manage"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COCAMappingService(db)
    await svc.remove(mapping_id, current_user.organization_id)


# ── CO-KP Mappings ────────────────────────────────────────────────────────────

@router.get("/mappings/co-kp", response_model=list[COKPMappingResponse])
async def list_co_kp_mappings(
    course_outcome_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COKPMappingService(db)
    return await svc.list_by_co(course_outcome_id, current_user.organization_id)


@router.post("/mappings/co-kp", response_model=COKPMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_co_kp_mapping(
    body: COKPMappingCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_kp.manage"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COKPMappingService(db)
    return await svc.create(body, current_user.organization_id, current_user.id)


@router.post("/mappings/co-kp/{mapping_id}/approve", response_model=COKPMappingResponse)
async def approve_co_kp_mapping(
    mapping_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_kp.approve"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COKPMappingService(db)
    return await svc.approve(mapping_id, current_user.organization_id, current_user.id)


@router.delete("/mappings/co-kp/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_co_kp_mapping(
    mapping_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_kp.manage"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COKPMappingService(db)
    await svc.remove(mapping_id, current_user.organization_id)
