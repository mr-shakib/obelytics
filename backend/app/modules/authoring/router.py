from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_any_permission, require_permission
from app.modules.ai.gateway import BackendFactory, get_backend_factory
from app.modules.authoring.schemas import (
    ApplyRequest,
    ApplyResponse,
    DecisionRequest,
    DecisionResponse,
    DraftRequest,
    DraftResponse,
    MappingSuggestRequest,
    MappingSuggestResponse,
    OutlineApplyRequest,
    OutlineApplyResponse,
    OutlinePreview,
    RefineRequest,
    RefineResponse,
)
from app.modules.authoring.service import AuthoringService
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.integrity import documents

router = APIRouter(prefix="/authoring", tags=["Outcome authoring"])

Manifest = PermissionManifestResponse


def _service(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    backend_factory: Annotated[BackendFactory, Depends(get_backend_factory)],
) -> AuthoringService:
    return AuthoringService(db, current_user, backend_factory)


Service = Annotated[AuthoringService, Depends(_service)]


@router.post("/course-outcomes/draft", response_model=DraftResponse)
async def draft_course_outcomes(
    body: DraftRequest,
    _: Annotated[Manifest, Depends(require_permission("co.create"))],
    service: Service,
):
    """Draft COs for a course. Nothing is saved: the teacher adds the ones they want."""
    return await service.draft(body)


@router.post("/course-outcomes/refine", response_model=RefineResponse)
async def refine_course_outcome(
    body: RefineRequest,
    _: Annotated[Manifest, Depends(require_any_permission("co.create", "co.update"))],
    service: Service,
):
    """Improve one CO statement (an AI draft or the teacher's own). Nothing is saved."""
    return await service.refine(body)


@router.post("/co-po/suggest", response_model=MappingSuggestResponse)
async def suggest_co_po_mapping(
    body: MappingSuggestRequest,
    _: Annotated[Manifest, Depends(require_permission("mapping.co_po.update"))],
    service: Service,
):
    """Suggest CO-PO links, each checked against the K, CEP and CEA rules. Nothing is saved."""
    return await service.suggest_mapping(body)


@router.post("/co-po/suggestions/{suggestion_id}/apply", response_model=ApplyResponse)
async def apply_co_po_suggestion(
    suggestion_id: UUID,
    body: ApplyRequest,
    manifest: Annotated[Manifest, Depends(require_permission("mapping.co_po.update"))],
    service: Service,
):
    """Add the chosen links (and the K/CEP/CEA mappings they need), re-checking every rule."""
    return await service.apply_mapping(suggestion_id, body, manifest)


@router.post("/suggestions/{suggestion_id}/decision", response_model=DecisionResponse)
async def record_suggestion_decision(
    suggestion_id: UUID,
    body: DecisionRequest,
    _: Annotated[
        Manifest,
        Depends(require_any_permission("co.create", "co.update", "mapping.co_po.update")),
    ],
    service: Service,
):
    """Record what the teacher did with a suggestion, so acceptance can be measured."""
    suggestion = await service.record_decision(suggestion_id, body)
    return DecisionResponse(suggestion_id=suggestion.id, decision=suggestion.decision)


_outline_access = require_any_permission("co.create", "course.update")


@router.post("/course-outline/read", response_model=OutlinePreview)
async def read_course_outline(
    curriculum_id: Annotated[UUID, Form()],
    course_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
    _: Annotated[Manifest, Depends(_outline_access)],
    service: Service,
):
    """Read a course outline (Word or text PDF) into a preview. Nothing is saved; the file is not kept."""
    data = await file.read()
    content_type = documents.normalize_content_type(file.content_type, file.filename)
    return await service.read_outline(curriculum_id, course_id, file.filename or "outline", content_type, data)


@router.post("/course-outline/suggestions/{suggestion_id}/apply", response_model=OutlineApplyResponse)
async def apply_course_outline(
    suggestion_id: UUID,
    body: OutlineApplyRequest,
    manifest: Annotated[Manifest, Depends(_outline_access)],
    service: Service,
):
    """Save the parts of the preview the teacher kept. Existing COs are never overwritten."""
    return await service.apply_outline(suggestion_id, body, manifest)
