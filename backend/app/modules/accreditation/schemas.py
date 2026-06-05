from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ── Cycles ────────────────────────────────────────────────────────────────────

class AccreditationCycleCreate(BaseModel):
    program_id: UUID
    name: str
    accreditation_body: str
    cycle_start_year: int
    cycle_end_year: int


class AccreditationCycleResponse(BaseModel):
    id: UUID
    organization_id: UUID
    program_id: UUID
    name: str
    accreditation_body: str
    cycle_start_year: int
    cycle_end_year: int
    status: str
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccreditationCycleUpdate(BaseModel):
    name: str | None = None
    accreditation_body: str | None = None
    cycle_start_year: int | None = None
    cycle_end_year: int | None = None


# ── Criteria ──────────────────────────────────────────────────────────────────

class AccreditationCriterionCreate(BaseModel):
    code: str
    title: str
    description: str | None = None
    order_index: int = 0


class AccreditationCriterionResponse(BaseModel):
    id: UUID
    cycle_id: UUID
    code: str
    title: str
    description: str | None
    order_index: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccreditationCriterionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    order_index: int | None = None


# ── PO Mappings ───────────────────────────────────────────────────────────────

class CriterionPOMappingCreate(BaseModel):
    program_outcome_id: UUID
    notes: str | None = None


class CriterionPOMappingResponse(BaseModel):
    id: UUID
    criterion_id: UUID
    program_outcome_id: UUID
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
