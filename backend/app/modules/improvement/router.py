from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.ai.gateway import BackendFactory, get_backend_factory
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.improvement.schemas import InterventionDecision, PlanResponse
from app.modules.improvement.service import ImprovementService

router = APIRouter(prefix="/improvement", tags=["Improvement agent"])

_read = require_permission("integrity.read")
_manage = require_permission("integrity.manage")


@router.post("/sections/{section_offering_id}/plan", response_model=PlanResponse)
async def make_improvement_plan(
    section_offering_id: UUID,
    manifest: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    backend_factory: Annotated[BackendFactory, Depends(get_backend_factory)],
):
    """Run the improvement agent on this section. Advisory: marks and attainment are untouched."""
    return await ImprovementService(db, current_user, manifest, backend_factory).run(section_offering_id)


@router.get("/sections/{section_offering_id}/plan", response_model=PlanResponse | None)
async def latest_improvement_plan(
    section_offering_id: UUID,
    manifest: Annotated[PermissionManifestResponse, Depends(_read)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await ImprovementService(db, current_user, manifest).latest(section_offering_id)


@router.post("/plans/{plan_id}/interventions/{intervention_id}", response_model=PlanResponse)
async def decide_intervention(
    plan_id: UUID,
    intervention_id: str,
    body: InterventionDecision,
    manifest: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await ImprovementService(db, current_user, manifest).decide(
        plan_id, intervention_id, body.decision, body.note
    )
