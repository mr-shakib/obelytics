from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ── Organization ──────────────────────────────────────────────────────────────


class OrgUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    short_name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = None
    vision: str | None = None
    mission: str | None = None
    logo_file_key: str | None = None
    website: str | None = None
    address_street: str | None = None
    address_city: str | None = None
    address_country: str | None = None
    address_postal_code: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    email_validation_regex: str | None = None


class OrgResponse(BaseModel):
    id: UUID
    name: str
    short_name: str
    description: str | None
    vision: str | None
    mission: str | None
    logo_file_key: str | None
    logo_url: str | None = None
    website: str | None
    address_street: str | None
    address_city: str | None
    address_country: str | None
    address_postal_code: str | None
    contact_email: str | None
    contact_phone: str | None
    email_validation_regex: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Department ────────────────────────────────────────────────────────────────


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    short_name: str = Field(min_length=1, max_length=30)
    year_established: int | None = None
    description: str | None = None
    vision: str | None = None
    mission: str | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    short_name: str | None = Field(default=None, min_length=1, max_length=30)
    year_established: int | None = None
    description: str | None = None
    vision: str | None = None
    mission: str | None = None
    logo_file_key: str | None = None


class DepartmentHeadInfo(BaseModel):
    user_id: UUID
    full_name: str


class DepartmentHeadHistoryEntry(BaseModel):
    user_id: UUID
    full_name: str
    effective_from: date
    effective_to: date | None


class AssignDepartmentHead(BaseModel):
    user_id: UUID


class DepartmentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    short_name: str
    year_established: int | None
    description: str | None
    vision: str | None
    mission: str | None
    logo_file_key: str | None
    logo_url: str | None = None
    status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    current_hod: DepartmentHeadInfo | None = None
    hod_history: list[DepartmentHeadHistoryEntry] = []

    model_config = {"from_attributes": True}


# ── Program ───────────────────────────────────────────────────────────────────


class ProgramCreate(BaseModel):
    department_id: UUID
    title: str = Field(min_length=1, max_length=255)
    acronym: str = Field(min_length=1, max_length=20)
    program_type: str = Field(pattern="^(UNDERGRADUATE|POSTGRADUATE|PHD)$")
    minimum_duration_semesters: int = Field(ge=1, le=20)
    total_credits: float = Field(ge=1, le=500)
    study_mode: str = Field(pattern="^(FULL_TIME|PART_TIME)$")
    description: str | None = None
    po_version_id: UUID | None = None


class ProgramUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    acronym: str | None = Field(default=None, min_length=1, max_length=20)
    program_type: str | None = Field(default=None, pattern="^(UNDERGRADUATE|POSTGRADUATE|PHD)$")
    minimum_duration_semesters: int | None = Field(default=None, ge=1, le=20)
    total_credits: float | None = Field(default=None, ge=1, le=500)
    study_mode: str | None = Field(default=None, pattern="^(FULL_TIME|PART_TIME)$")
    description: str | None = None
    po_version_id: UUID | None = None


class ProgramCoordinatorInfo(BaseModel):
    user_id: UUID
    full_name: str


class ProgramCoordinatorHistoryEntry(BaseModel):
    user_id: UUID
    full_name: str
    effective_from: date
    effective_to: date | None


class AssignProgramCoordinator(BaseModel):
    user_id: UUID


class ProgramResponse(BaseModel):
    id: UUID
    organization_id: UUID
    department_id: UUID
    title: str
    acronym: str
    program_type: str
    minimum_duration_semesters: int
    total_credits: float
    study_mode: str
    description: str | None
    po_version_id: UUID | None
    status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    current_coordinator: ProgramCoordinatorInfo | None = None
    coordinator_history: list[ProgramCoordinatorHistoryEntry] = []

    model_config = {"from_attributes": True}
