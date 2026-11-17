from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.ai.gateway import BackendFactory, get_backend_factory
from app.modules.evidence.schemas import (
    DraftDecision,
    DraftRequest,
    DraftResponse,
    ReferenceDocumentResponse,
)
from app.modules.evidence.service import MAX_DOCUMENT_BYTES, EvidenceService
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse

router = APIRouter(prefix="/evidence", tags=["Accreditation evidence writer"])

Manifest = PermissionManifestResponse
_read = require_permission("accreditation.read")
_manage = require_permission("accreditation.manage")


def _service(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    backend_factory: Annotated[BackendFactory, Depends(get_backend_factory)],
) -> EvidenceService:
    return EvidenceService(db, current_user, backend_factory)


Service = Annotated[EvidenceService, Depends(_service)]


@router.get("/documents", response_model=list[ReferenceDocumentResponse])
async def list_reference_documents(_: Annotated[Manifest, Depends(_read)], service: Service):
    return await service.list_documents()


@router.post("/documents", response_model=ReferenceDocumentResponse, status_code=status.HTTP_201_CREATED)
async def add_reference_document(
    _: Annotated[Manifest, Depends(_manage)],
    service: Service,
    file: Annotated[UploadFile, File(description="Accreditation manual or template: PDF, Word or text")],
    title: Annotated[str | None, Form()] = None,
):
    """Split a document into passages and index them for search. The file itself is not kept."""
    data = await file.read(MAX_DOCUMENT_BYTES + 1)
    return await service.add_document(title, file.filename or "document", file.content_type, data)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reference_document(document_id: UUID, _: Annotated[Manifest, Depends(_manage)], service: Service):
    await service.delete_document(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/programs/{program_id}/drafts", response_model=DraftResponse)
async def draft_criterion_section(
    program_id: UUID, body: DraftRequest, _: Annotated[Manifest, Depends(_manage)], service: Service,
):
    """Draft one report section. Every sentence cites program records or manual passages,
    and code flags sentences whose citations or numbers it cannot find. Advisory."""
    return await service.draft(program_id, body)


@router.get("/programs/{program_id}/drafts", response_model=list[DraftResponse])
async def list_criterion_drafts(
    program_id: UUID, curriculum_id: UUID, _: Annotated[Manifest, Depends(_read)], service: Service,
):
    return await service.list_drafts(program_id, curriculum_id)


@router.post("/drafts/{draft_id}/decision", response_model=DraftResponse)
async def decide_criterion_draft(
    draft_id: UUID, body: DraftDecision, _: Annotated[Manifest, Depends(_manage)], service: Service,
):
    return await service.decide(draft_id, body.decision, body.edited_text)
