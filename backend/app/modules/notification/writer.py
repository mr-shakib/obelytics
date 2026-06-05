from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.models import Notification


def write_notification(
    session: AsyncSession,
    *,
    org_id: UUID,
    recipient_user_id: UUID,
    notification_type: str,
    title: str,
    body: str | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
) -> Notification:
    """Write a notification. Caller must flush/commit the session."""
    entry = Notification(
        organization_id=org_id,
        recipient_user_id=recipient_user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    session.add(entry)
    return entry
