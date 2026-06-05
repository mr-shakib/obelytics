from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

EntityType = Literal["course_outcome", "result_publication", "co_po_mapping_set"]

VALID_ENTITY_TYPES = {"course_outcome", "result_publication", "co_po_mapping_set"}


class ReviewCommentCreate(BaseModel):
    comment: str


class ReviewCommentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    entity_type: str
    entity_id: UUID
    author_user_id: UUID
    comment: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# Inbox item — a summary of a pending entity
class InboxItem(BaseModel):
    entity_type: str
    entity_id: UUID
    description: str       # human-readable label (e.g., CO code, offering identifier)
    status: str            # current status
    submitted_at: datetime | None  # when it entered the current review state


class InboxResponse(BaseModel):
    pending_result_publications: list[InboxItem]
    pending_course_outcomes: list[InboxItem]
    pending_co_po_mapping_sets: list[InboxItem]
    total_count: int


class InboxCountsResponse(BaseModel):
    result_publications: int
    course_outcomes: int
    co_po_mapping_sets: int
    total: int
