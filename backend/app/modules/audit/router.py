from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.audit.schemas import AuditLogListResponse, AuditLogResponse
from app.modules.audit.service import AuditService
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse

router = APIRouter(prefix="/audit", tags=["Audit"])
_read = require_permission("system.audit.read")


@router.get("/logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    _: Annotated[PermissionManifestResponse, Depends(_read)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str | None = None,
    entity_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
):
    svc = AuditService(db)
    return await svc.list_for_org(current_user.organization_id, q, entity_type, page, page_size)


@router.get("/logs/{entity_type}/{entity_id}", response_model=list[AuditLogResponse])
async def list_entity_audit_logs(
    entity_type: str,
    entity_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_read)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
):
    svc = AuditService(db)
    return await svc.list_for_entity(entity_type, entity_id, limit)
