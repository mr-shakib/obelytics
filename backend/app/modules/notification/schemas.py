from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    recipient_user_id: UUID
    notification_type: str
    title: str
    body: str | None
    entity_type: str | None
    entity_id: UUID | None
    is_read: bool
    created_at: datetime
    read_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class NotificationCountResponse(BaseModel):
    unread_count: int
