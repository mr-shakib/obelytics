from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: UUID
    organization_id: UUID | None
    actor_user_id: UUID | None
    entity_type: str
    entity_id: UUID
    action: str
    before_status: str | None
    after_status: str | None
    extra: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
