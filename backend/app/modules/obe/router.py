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
    COPOMappingEntryResponse,
    COPOMappingEntryUpsert,
    COPOMappingSetCreate,
    COPOMappingSetResponse,
    COPOMappingValidationResponse,
    CourseOutcomeCreate,
    CourseOutcomeResponse,
    CourseOutcomeUpdate,
    PEOCreate,
    PEOMappingSet,
    PEOMissionMappingResponse,
    PEOMissionMappingSet,
    PEOPOMappingResponse,
    PEOResponse,
    PEOUpdate,
    POKnowledgeProfileCreate,
    POKnowledgeProfileResponse,
    POVersionCreate,
    POVersionResponse,
    POVersionUpdate,
    ProgramMissionCreate,
    ProgramMissionResponse,
    ProgramMissionUpdate,
    ProgramOutcomeBulkImportRequest,
    ProgramOutcomeBulkImportResponse,
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
    PEOService,
    POKnowledgeProfileService,
    POService,
    POVersionService,
    ProgramMissionService,
)

router = APIRouter(tags=["OBE"])


# ── PO Versions ──────────────────────────────────────────────────────────────


@router.get("/po-versions", response_model=list[POVersionResponse])
async def list_po_versions(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("po.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = POVersionService(db)
    versions = await svc.list_active(current_user.organization_id)
    repo = svc._repo
    results = []
    for v in versions:
        count = await repo.count_pos(v.id)
        resp = POVersionResponse.model_validate(v)
        resp.po_count = count
        results.append(resp)
    return results


@router.post("/po-versions", response_model=POVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_po_version(
    body: POVersionCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("po.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = POVersionService(db)
    version = await svc.create(body, current_user.organization_id)
    resp = POVersionResponse.model_validate(version)
    resp.po_count = 0
    return resp


@router.get("/po-versions/{version_id}", response_model=POVersionResponse)
async def get_po_version(
    version_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("po.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = POVersionService(db)
    data = await svc.get_with_count(version_id, current_user.organization_id)
    resp = POVersionResponse.model_validate(data["version"])
    resp.po_count = data["po_count"]
    return resp


@router.patch("/po-versions/{version_id}", response_model=POVersionResponse)
async def update_po_version(
    version_id: UUID,
    body: POVersionUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("po.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = POVersionService(db)
    version = await svc.update(version_id, body, current_user.organization_id)
    count = await svc._repo.count_pos(version.id)
    resp = POVersionResponse.model_validate(version)
    resp.po_count = count
    return resp


# ── Program Outcomes ──────────────────────────────────────────────────────────


@router.get("/program-outcomes", response_model=list[ProgramOutcomeResponse])
async def list_program_outcomes(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("po.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    program_id: UUID | None = None,
    po_version_id: UUID | None = None,
):
    svc = POService(db)
    return await svc.list_active(current_user.organization_id, program_id, po_version_id)


@router.post(
    "/program-outcomes", response_model=ProgramOutcomeResponse, status_code=status.HTTP_201_CREATED
)
async def create_program_outcome(
    body: ProgramOutcomeCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("po.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = POService(db)
    return await svc.create(body, current_user.organization_id)


@router.post("/program-outcomes/bulk-import", response_model=ProgramOutcomeBulkImportResponse)
async def bulk_import_program_outcomes(
    body: ProgramOutcomeBulkImportRequest,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("po.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = POService(db)
    return await svc.bulk_import(
        body.items, current_user.organization_id, body.po_version_id, body.program_id
    )


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


@router.get(
    "/program-outcomes/{po_id}/knowledge-profiles", response_model=list[POKnowledgeProfileResponse]
)
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
    return await svc.list_by_curriculum_course(
        curriculum_id, course_id, current_user.organization_id
    )


@router.post(
    "/course-outcomes", response_model=CourseOutcomeResponse, status_code=status.HTTP_201_CREATED
)
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


@router.get(
    "/course-outcomes/{co_id}/delivery-methods", response_model=list[CODeliveryMethodResponse]
)
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
        ms = await svc._repo.find_by_course_fallback(course_id)
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


@router.get("/mappings/co-cp", response_model=list[COCPMappingResponse])
async def list_co_cp_mappings(
    course_outcome_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("co.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COCPMappingService(db)
    return await svc.list_by_co(course_outcome_id, current_user.organization_id)


@router.post(
    "/mappings/co-cp", response_model=COCPMappingResponse, status_code=status.HTTP_201_CREATED
)
async def create_co_cp_mapping(
    body: COCPMappingCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_cp.manage"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COCPMappingService(db)
    return await svc.create(body, current_user.organization_id, current_user.id)


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


@router.post(
    "/mappings/co-ca", response_model=COCAMappingResponse, status_code=status.HTTP_201_CREATED
)
async def create_co_ca_mapping(
    body: COCAMappingCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_ca.manage"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COCAMappingService(db)
    return await svc.create(body, current_user.organization_id, current_user.id)


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


@router.post(
    "/mappings/co-kp", response_model=COKPMappingResponse, status_code=status.HTTP_201_CREATED
)
async def create_co_kp_mapping(
    body: COKPMappingCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_kp.manage"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COKPMappingService(db)
    return await svc.create(body, current_user.organization_id, current_user.id)


@router.delete("/mappings/co-kp/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_co_kp_mapping(
    mapping_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mapping.co_kp.manage"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COKPMappingService(db)
    await svc.remove(mapping_id, current_user.organization_id)


# ── Program Missions ──────────────────────────────────────────────────────────


@router.get("/programs/{program_id}/missions", response_model=list[ProgramMissionResponse])
async def list_program_missions(
    program_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mission.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramMissionService(db)
    return await svc.list_active(current_user.organization_id, program_id)


@router.post(
    "/missions",
    response_model=ProgramMissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_program_mission(
    body: ProgramMissionCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mission.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramMissionService(db)
    return await svc.create(body, current_user.organization_id)


@router.patch("/missions/{mission_id}", response_model=ProgramMissionResponse)
async def update_program_mission(
    mission_id: UUID,
    body: ProgramMissionUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mission.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramMissionService(db)
    return await svc.update(mission_id, body, current_user.organization_id)


@router.post("/missions/{mission_id}/archive", response_model=ProgramMissionResponse)
async def archive_program_mission(
    mission_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("mission.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramMissionService(db)
    return await svc.archive(mission_id, current_user.organization_id)


# ── Program Educational Objectives (PEO) ─────────────────────────────────────


@router.get("/programs/{program_id}/peos", response_model=list[PEOResponse])
async def list_peos(
    program_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("peo.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = PEOService(db)
    return await svc.list_active(current_user.organization_id, program_id)


@router.post(
    "/peos",
    response_model=PEOResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_peo(
    body: PEOCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("peo.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = PEOService(db)
    return await svc.create(body, current_user.organization_id)


@router.patch("/peos/{peo_id}", response_model=PEOResponse)
async def update_peo(
    peo_id: UUID,
    body: PEOUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("peo.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = PEOService(db)
    return await svc.update(peo_id, body, current_user.organization_id)


@router.post("/peos/{peo_id}/archive", response_model=PEOResponse)
async def archive_peo(
    peo_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("peo.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = PEOService(db)
    return await svc.archive(peo_id, current_user.organization_id)


@router.get("/peos/{peo_id}/po-mappings", response_model=list[PEOPOMappingResponse])
async def get_peo_po_mappings(
    peo_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("peo.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = PEOService(db)
    return await svc.get_po_mappings(peo_id, current_user.organization_id)


@router.put("/peos/{peo_id}/po-mappings", response_model=list[PEOPOMappingResponse])
async def set_peo_po_mappings(
    peo_id: UUID,
    body: PEOMappingSet,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("peo.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = PEOService(db)
    return await svc.set_po_mappings(peo_id, body, current_user.organization_id)


@router.get("/peos/{peo_id}/mission-mappings", response_model=list[PEOMissionMappingResponse])
async def get_peo_mission_mappings(
    peo_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("peo.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = PEOService(db)
    return await svc.get_mission_mappings(peo_id, current_user.organization_id)


@router.put("/peos/{peo_id}/mission-mappings", response_model=list[PEOMissionMappingResponse])
async def set_peo_mission_mappings(
    peo_id: UUID,
    body: PEOMissionMappingSet,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("peo.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = PEOService(db)
    return await svc.set_mission_mappings(peo_id, body, current_user.organization_id)
