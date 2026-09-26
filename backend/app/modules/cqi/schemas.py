from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class COAttainmentGapResponse(BaseModel):
    id: UUID
    organization_id: UUID
    section_offering_id: UUID
    course_outcome_id: UUID
    attainment_pct: Decimal
    average_score_pct: Decimal
    threshold_pct: Decimal
    students_above_threshold: int
    total_students: int
    status: str
    detected_at: datetime
    resolved_at: datetime | None
    waived_by_user_id: UUID | None
    waiver_reason: str | None
    model_config = ConfigDict(from_attributes=True)


class POAttainmentGapResponse(BaseModel):
    id: UUID
    organization_id: UUID
    program_id: UUID
    academic_term_id: UUID
    program_outcome_id: UUID
    aggregate_attainment_pct: Decimal
    threshold_pct: Decimal
    contributing_offering_count: int
    attained_offering_count: int
    status: str
    detected_at: datetime
    resolved_at: datetime | None
    waived_by_user_id: UUID | None
    waiver_reason: str | None
    model_config = ConfigDict(from_attributes=True)


class GapWaiveRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)


class GapStatusCounts(BaseModel):
    open: int = 0
    addressed: int = 0
    closed: int = 0
    waived: int = 0


class CQISummary(BaseModel):
    """Program-level CQI posture for a term (or for all terms when unfiltered)."""
    program_id: UUID | None
    academic_term_id: UUID | None
    co_gaps: GapStatusCounts
    po_gaps: GapStatusCounts
