from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.audit.schemas import AuditLogResponse
from app.modules.audit.service import AuditService
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse

router = APIRouter(prefix="/audit", tags=["Audit"])
_read = require_permission("system.audit.read")


@router.get("/logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    _: Annotated[PermissionManifestResponse, Depends(_read)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    limit: int = 50,
):
    svc = AuditService(db)
    if entity_id is not None:
        logs = await svc.list_for_entity(entity_type or "course_outcome", entity_id, limit)
    else:
        logs = await svc.list_for_org(
            current_user.organization_id, entity_type, limit
        )
    return [AuditLogResponse.model_validate(log) for log in logs]
