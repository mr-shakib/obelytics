from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.approval.exceptions import InvalidEntityType
from app.modules.approval.schemas import (
    InboxCountsResponse,
    InboxResponse,
    ReviewCommentCreate,
    ReviewCommentResponse,
)
from app.modules.approval.service import ApprovalInboxService, ReviewCommentService
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse

router = APIRouter(prefix="/approval", tags=["Approval"])
_inbox_read = require_permission("approval.inbox.read")


@router.get("/inbox", response_model=InboxResponse)
async def get_inbox(
    manifest: Annotated[PermissionManifestResponse, Depends(_inbox_read)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ApprovalInboxService(db)
    data = await svc.get_inbox(current_user.organization_id, manifest)
    return InboxResponse(**data)


@router.get("/inbox/counts", response_model=InboxCountsResponse)
async def get_inbox_counts(
    manifest: Annotated[PermissionManifestResponse, Depends(_inbox_read)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ApprovalInboxService(db)
    data = await svc.get_counts(current_user.organization_id, manifest)
    return InboxCountsResponse(**data)


@router.get(
    "/comments/{entity_type}/{entity_id}",
    response_model=list[ReviewCommentResponse],
)
async def list_comments(
    entity_type: str,
    entity_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_inbox_read)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ReviewCommentService(db)
    comments = await svc.list_comments(current_user.organization_id, entity_type, entity_id)
    return [ReviewCommentResponse.model_validate(c) for c in comments]


@router.post(
    "/comments/{entity_type}/{entity_id}",
    response_model=ReviewCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    entity_type: str,
    entity_id: UUID,
    body: ReviewCommentCreate,
    _: Annotated[PermissionManifestResponse, Depends(_inbox_read)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ReviewCommentService(db)
    try:
        comment = await svc.add_comment(
            org_id=current_user.organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            author_user_id=current_user.id,
            comment=body.comment,
        )
    except InvalidEntityType as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return ReviewCommentResponse.model_validate(comment)
