import math
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.audit.repository import AuditLogRepository
from app.modules.audit.schemas import AuditLogListResponse, AuditLogResponse


def _to_response(log: AuditLog, actor_name: str | None, actor_email: str | None) -> AuditLogResponse:
    changes = None
    if log.before_status is not None or log.after_status is not None:
        changes = {"status": {"from": log.before_status, "to": log.after_status}}
    return AuditLogResponse(
        id=log.id,
        actor_name=actor_name or "System",
        actor_email=actor_email,
        action=log.action,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        timestamp=log.created_at,
        changes=changes,
    )


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AuditLogRepository(session)

    async def list_for_entity(
        self, entity_type: str, entity_id: UUID, limit: int = 50
    ) -> list[AuditLogResponse]:
        rows = await self._repo.list_for_entity(entity_type, entity_id, limit)
        return [_to_response(log, name, email) for log, name, email in rows]

    async def list_for_org(
        self,
        org_id: UUID,
        q: str | None,
        entity_type: str | None,
        page: int,
        page_size: int,
    ) -> AuditLogListResponse:
        rows, total = await self._repo.list_for_org_paginated(org_id, q, entity_type, page, page_size)
        return AuditLogListResponse(
            items=[_to_response(log, name, email) for log, name, email in rows],
            total=total,
            page=page,
            pages=max(1, math.ceil(total / page_size)),
        )
