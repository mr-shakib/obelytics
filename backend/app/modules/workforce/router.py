from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_any_permission, require_permission
from app.modules.ai.gateway import BackendFactory, get_backend_factory
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.workforce.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    PostingCreate,
    PostingResponse,
)
from app.modules.workforce.service import WorkforceService

router = APIRouter(prefix="/workforce", tags=["Workforce readiness"])

Manifest = PermissionManifestResponse
_read = require_permission("po.read")
_manage = require_any_permission("po.update", "curriculum.update")


def _service(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    backend_factory: Annotated[BackendFactory, Depends(get_backend_factory)],
) -> WorkforceService:
    return WorkforceService(db, current_user, backend_factory)


Service = Annotated[WorkforceService, Depends(_service)]


@router.get("/programs/{program_id}/postings", response_model=list[PostingResponse])
async def list_job_postings(program_id: UUID, _: Annotated[Manifest, Depends(_read)], service: Service):
    return await service.list_postings(program_id)


@router.post(
    "/programs/{program_id}/postings",
    response_model=PostingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_job_posting(
    program_id: UUID, body: PostingCreate, _: Annotated[Manifest, Depends(_manage)], service: Service
):
    """Save a job posting; the AI reads its skills now if it can, otherwise at the next analysis."""
    return await service.create_posting(program_id, body)


@router.delete("/postings/{posting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_posting(posting_id: UUID, _: Annotated[Manifest, Depends(_manage)], service: Service):
    await service.delete_posting(posting_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/programs/{program_id}/analysis", response_model=AnalysisResponse)
async def analyze_market_coverage(
    program_id: UUID, body: AnalysisRequest, _: Annotated[Manifest, Depends(_manage)], service: Service
):
    """Which COs develop the skills employers ask for most. Advisory: nothing is changed."""
    return await service.analyze(program_id, body.curriculum_id)


@router.get("/programs/{program_id}/analysis", response_model=AnalysisResponse | None)
async def latest_market_analysis(
    program_id: UUID, curriculum_id: UUID, _: Annotated[Manifest, Depends(_read)], service: Service
):
    return await service.latest(program_id, curriculum_id)
