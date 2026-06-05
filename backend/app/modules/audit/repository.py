from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_entity(
        self, entity_type: str, entity_id: UUID, limit: int = 50
    ) -> list[AuditLog]:
        result = await self._session.execute(
            select(AuditLog)
            .where(
                and_(
                    AuditLog.entity_type == entity_type,
                    AuditLog.entity_id == entity_id,
                )
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_for_org(
        self,
        org_id: UUID,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        q = select(AuditLog).where(AuditLog.organization_id == org_id)
        if entity_type is not None:
            q = q.where(AuditLog.entity_type == entity_type)
        q = q.order_by(AuditLog.created_at.desc()).limit(limit)
        result = await self._session.execute(q)
        return list(result.scalars().all())
