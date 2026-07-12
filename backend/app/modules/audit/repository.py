from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.iam.models import User


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_entity(
        self, entity_type: str, entity_id: UUID, limit: int = 50
    ) -> list[tuple[AuditLog, str | None, str | None]]:
        result = await self._session.execute(
            select(AuditLog, User.full_name, User.email)
            .outerjoin(User, User.id == AuditLog.actor_user_id)
            .where(
                and_(
                    AuditLog.entity_type == entity_type,
                    AuditLog.entity_id == entity_id,
                )
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return [(row[0], row[1], row[2]) for row in result.all()]

    def _org_query_filters(self, org_id: UUID, q: str | None, entity_type: str | None):
        filters = [AuditLog.organization_id == org_id]
        if entity_type is not None:
            filters.append(AuditLog.entity_type == entity_type)
        if q:
            pattern = f"%{q}%"
            filters.append(
                or_(
                    User.full_name.ilike(pattern),
                    User.email.ilike(pattern),
                    AuditLog.action.ilike(pattern),
                    AuditLog.entity_type.ilike(pattern),
                )
            )
        return and_(*filters)

    async def list_for_org_paginated(
        self,
        org_id: UUID,
        q: str | None,
        entity_type: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[AuditLog, str | None, str | None]], int]:
        where_clause = self._org_query_filters(org_id, q, entity_type)

        total = await self._session.scalar(
            select(func.count(AuditLog.id))
            .select_from(AuditLog)
            .outerjoin(User, User.id == AuditLog.actor_user_id)
            .where(where_clause)
        )

        result = await self._session.execute(
            select(AuditLog, User.full_name, User.email)
            .outerjoin(User, User.id == AuditLog.actor_user_id)
            .where(where_clause)
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = [(row[0], row[1], row[2]) for row in result.all()]
        return rows, total or 0
