from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: UUID
    actor_name: str
    actor_email: str | None
    action: str
    entity_type: str
    entity_id: UUID
    timestamp: datetime
    changes: dict[str, dict[str, str | None]] | None = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    pages: int
