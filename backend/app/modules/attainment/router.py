from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.attainment.exceptions import AttainmentNotComputed
from app.modules.attainment.schemas import (
    AttainmentConfigResponse,
    AttainmentConfigUpdate,
    AttainmentSummary,
    COAttainmentResultResponse,
    POAttainmentResultResponse,
)
from app.modules.attainment.service import AttainmentConfigService, AttainmentResultService

router = APIRouter(prefix="/attainment", tags=["Attainment"])

_view = require_permission("attainment.read")
_manage = require_permission("attainment.configure")


# ── Attainment Summary ────────────────────────────────────────────────────────

@router.get(
    "/section-offerings/{so_id}/summary",
    response_model=AttainmentSummary,
)
async def get_attainment_summary(
    so_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_view)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AttainmentResultService(db)
    try:
        summary = await svc.get_summary(current_user.organization_id, so_id)
    except AttainmentNotComputed as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return AttainmentSummary(
        section_offering_id=summary["section_offering_id"],
        co_results=[COAttainmentResultResponse.model_validate(r) for r in summary["co_results"]],
        po_results=[POAttainmentResultResponse.model_validate(r) for r in summary["po_results"]],
    )


@router.post(
    "/section-offerings/{so_id}/recompute",
    response_model=AttainmentSummary,
)
async def recompute_attainment(
    so_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AttainmentResultService(db)
    try:
        summary = await svc.trigger_recompute(current_user.organization_id, so_id)
    except AttainmentNotComputed as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return AttainmentSummary(
        section_offering_id=summary["section_offering_id"],
        co_results=[COAttainmentResultResponse.model_validate(r) for r in summary["co_results"]],
        po_results=[POAttainmentResultResponse.model_validate(r) for r in summary["po_results"]],
    )


# ── Config ────────────────────────────────────────────────────────────────────

@router.get("/config", response_model=AttainmentConfigResponse)
async def get_org_config(
    _: Annotated[PermissionManifestResponse, Depends(_view)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AttainmentConfigService(db)
    config = await svc.get_config(current_user.organization_id, program_id=None)
    return AttainmentConfigResponse.model_validate(config)


@router.get("/config/programs/{program_id}", response_model=AttainmentConfigResponse)
async def get_program_config(
    program_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_view)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AttainmentConfigService(db)
    config = await svc.get_config(current_user.organization_id, program_id=program_id)
    return AttainmentConfigResponse.model_validate(config)


@router.patch("/config", response_model=AttainmentConfigResponse)
async def update_org_config(
    body: AttainmentConfigUpdate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AttainmentConfigService(db)
    config = await svc.update_config(current_user.organization_id, None, body)
    return AttainmentConfigResponse.model_validate(config)


@router.patch("/config/programs/{program_id}", response_model=AttainmentConfigResponse)
async def update_program_config(
    program_id: UUID,
    body: AttainmentConfigUpdate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AttainmentConfigService(db)
    config = await svc.update_config(current_user.organization_id, program_id, body)
    return AttainmentConfigResponse.model_validate(config)
