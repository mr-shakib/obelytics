from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.models import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(
        self,
        org_id: UUID,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        q = select(Notification).where(
            and_(
                Notification.organization_id == org_id,
                Notification.recipient_user_id == user_id,
            )
        )
        if unread_only:
            q = q.where(Notification.is_read == False)  # noqa: E712
        q = q.order_by(Notification.created_at.desc()).limit(limit)
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def get_by_id(
        self, notif_id: UUID, org_id: UUID, user_id: UUID
    ) -> Notification | None:
        result = await self._session.execute(
            select(Notification).where(
                and_(
                    Notification.id == notif_id,
                    Notification.organization_id == org_id,
                    Notification.recipient_user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def mark_read(self, notif: Notification) -> Notification:
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)
        self._session.add(notif)
        await self._session.flush()
        await self._session.refresh(notif)
        return notif

    async def mark_all_read(self, org_id: UUID, user_id: UUID) -> int:
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            update(Notification)
            .where(
                and_(
                    Notification.organization_id == org_id,
                    Notification.recipient_user_id == user_id,
                    Notification.is_read == False,  # noqa: E712
                )
            )
            .values(is_read=True, read_at=now)
        )
        return result.rowcount

    async def count_unread(self, org_id: UUID, user_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).where(
                and_(
                    Notification.organization_id == org_id,
                    Notification.recipient_user_id == user_id,
                    Notification.is_read == False,  # noqa: E712
                )
            )
        )
        return result.scalar_one()
