from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.notification.schemas import NotificationCountResponse, NotificationResponse
from app.modules.notification.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])
_read_own = require_permission("notification.read.own")


@router.get("/me", response_model=list[NotificationResponse])
async def list_my_notifications(
    _: Annotated[PermissionManifestResponse, Depends(_read_own)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    unread_only: bool = False,
):
    svc = NotificationService(db)
    notifs = await svc.list_my_notifications(
        current_user.organization_id, current_user.id, unread_only
    )
    return [NotificationResponse.model_validate(n) for n in notifs]


@router.get("/me/count", response_model=NotificationCountResponse)
async def count_unread_notifications(
    _: Annotated[PermissionManifestResponse, Depends(_read_own)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = NotificationService(db)
    count = await svc.count_unread(current_user.organization_id, current_user.id)
    return NotificationCountResponse(unread_count=count)


@router.post("/read-all")
async def mark_all_notifications_read(
    _: Annotated[PermissionManifestResponse, Depends(_read_own)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = NotificationService(db)
    updated = await svc.mark_all_read(current_user.organization_id, current_user.id)
    return {"updated": updated}


@router.post("/{notif_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notif_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_read_own)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = NotificationService(db)
    notif = await svc.mark_read(
        current_user.organization_id, current_user.id, notif_id
    )
    await db.commit()
    return NotificationResponse.model_validate(notif)
