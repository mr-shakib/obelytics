from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AttainmentConfigResponse(BaseModel):
    id: UUID
    organization_id: UUID
    program_id: UUID | None
    threshold_student_pct: Decimal
    threshold_co_score_pct: Decimal
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AttainmentConfigUpdate(BaseModel):
    threshold_student_pct: Decimal | None = None
    threshold_co_score_pct: Decimal | None = None


class COAttainmentResultResponse(BaseModel):
    id: UUID
    organization_id: UUID
    section_offering_id: UUID
    course_outcome_id: UUID
    average_attainment_pct: Decimal
    students_above_threshold: int
    total_students: int
    is_attained: bool
    calculated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class POAttainmentResultResponse(BaseModel):
    id: UUID
    organization_id: UUID
    section_offering_id: UUID
    program_outcome_id: UUID
    attainment_pct: Decimal
    contributing_co_count: int
    is_attained: bool
    calculated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AttainmentSummary(BaseModel):
    section_offering_id: UUID
    co_results: list[COAttainmentResultResponse]
    po_results: list[POAttainmentResultResponse]
