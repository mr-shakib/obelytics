from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.models import Notification
from app.modules.notification.repository import NotificationRepository


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = NotificationRepository(session)

    async def list_my_notifications(
        self,
        org_id: UUID,
        user_id: UUID,
        unread_only: bool = False,
    ) -> list[Notification]:
        return await self._repo.list_for_user(org_id, user_id, unread_only)

    async def count_unread(self, org_id: UUID, user_id: UUID) -> int:
        return await self._repo.count_unread(org_id, user_id)

    async def mark_read(
        self, org_id: UUID, user_id: UUID, notif_id: UUID
    ) -> Notification:
        notif = await self._repo.get_by_id(notif_id, org_id, user_id)
        if notif is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )
        return await self._repo.mark_read(notif)

    async def mark_all_read(self, org_id: UUID, user_id: UUID) -> int:
        count = await self._repo.mark_all_read(org_id, user_id)
        await self._session.commit()
        return count
