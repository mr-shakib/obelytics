from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.audit.repository import AuditLogRepository


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AuditLogRepository(session)

    async def list_for_entity(
        self, entity_type: str, entity_id: UUID, limit: int = 50
    ) -> list[AuditLog]:
        return await self._repo.list_for_entity(entity_type, entity_id, limit)

    async def list_for_org(
        self,
        org_id: UUID,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        return await self._repo.list_for_org(org_id, entity_type, limit)
