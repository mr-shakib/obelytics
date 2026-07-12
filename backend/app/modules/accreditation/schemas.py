from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Cycles ────────────────────────────────────────────────────────────────────

class AccreditationCycleCreate(BaseModel):
    program_id: UUID
    name: str
    body: str
    start_date: date
    end_date: date | None = None


class AccreditationCycleResponse(BaseModel):
    id: UUID
    organization_id: UUID
    program_id: UUID
    program_name: str | None = None
    name: str
    body: str
    start_date: date
    end_date: date | None
    status: str
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccreditationCycleUpdate(BaseModel):
    name: str | None = None
    body: str | None = None
    start_date: date | None = None
    end_date: date | None = None


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
    status: str
    assigned_to_user_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccreditationCriterionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    order_index: int | None = None
    status: str | None = Field(default=None, pattern="^(NOT_STARTED|IN_PROGRESS|COMPLETED)$")
    assigned_to_user_id: UUID | None = None


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


# ── Cycle detail (with nested criteria for the cycle detail page) ─────────────

class CycleCriterionInfo(BaseModel):
    id: UUID
    criterion_code: str
    title: str
    status: str
    assigned_to_user_id: UUID | None = None
    assigned_to: str | None = None


class AccreditationCycleDetailResponse(AccreditationCycleResponse):
    criteria: list[CycleCriterionInfo] = []
    completion_pct: int = 0
