from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Program Outcomes ──────────────────────────────────────────────────────────

class ProgramOutcomeCreate(BaseModel):
    program_id: UUID
    bloom_domain_id: UUID | None = None
    code: str = Field(min_length=1, max_length=20)
    reference: str | None = Field(default=None, max_length=100)
    statement: str
    po_type: str | None = Field(default=None, max_length=100)
    order_index: int = Field(ge=0, le=32767)


class ProgramOutcomeUpdate(BaseModel):
    bloom_domain_id: UUID | None = None
    reference: str | None = Field(default=None, max_length=100)
    statement: str | None = None
    po_type: str | None = Field(default=None, max_length=100)
    order_index: int | None = Field(default=None, ge=0, le=32767)


class ProgramOutcomeResponse(BaseModel):
    id: UUID
    organization_id: UUID
    program_id: UUID
    bloom_domain_id: UUID | None
    code: str
    reference: str | None
    statement: str
    po_type: str | None
    order_index: int
    status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── PO Knowledge Profiles ─────────────────────────────────────────────────────

class POKnowledgeProfileCreate(BaseModel):
    knowledge_profile_id: UUID


class POKnowledgeProfileResponse(BaseModel):
    id: UUID
    program_outcome_id: UUID
    knowledge_profile_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Course Outcomes ───────────────────────────────────────────────────────────

class CourseOutcomeCreate(BaseModel):
    curriculum_id: UUID
    course_id: UUID
    bloom_level_ids: list[UUID] = Field(default_factory=list)
    code: str = Field(min_length=1, max_length=20)
    statement: str


class CourseOutcomeUpdate(BaseModel):
    bloom_level_ids: list[UUID] | None = None
    code: str | None = Field(default=None, min_length=1, max_length=20)
    statement: str | None = None


class CourseOutcomeResponse(BaseModel):
    id: UUID
    organization_id: UUID
    curriculum_id: UUID
    course_id: UUID
    bloom_level_ids: list[UUID] = Field(default_factory=list)
    code: str
    statement: str
    status: str
    created_by_user_id: UUID | None
    locked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── CO Delivery Methods ───────────────────────────────────────────────────────

class CODeliveryMethodCreate(BaseModel):
    delivery_method_id: UUID


class CODeliveryMethodResponse(BaseModel):
    id: UUID
    course_outcome_id: UUID
    delivery_method_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ── CO-PO Mapping Sets ────────────────────────────────────────────────────────

class COPOMappingSetCreate(BaseModel):
    curriculum_id: UUID
    course_id: UUID


class COPOMappingSetResponse(BaseModel):
    id: UUID
    organization_id: UUID
    curriculum_id: UUID
    course_id: UUID
    status: str
    created_by_user_id: UUID | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── CO-PO Mapping Entries ─────────────────────────────────────────────────────

class COPOMappingEntryUpsert(BaseModel):
    course_outcome_id: UUID
    program_outcome_id: UUID
    weight: int = Field(ge=1, le=3)


class COPOMappingEntryResponse(BaseModel):
    id: UUID
    mapping_set_id: UUID
    course_outcome_id: UUID
    program_outcome_id: UUID
    weight: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── CO-CP Mappings ────────────────────────────────────────────────────────────

class COCPMappingCreate(BaseModel):
    course_outcome_id: UUID
    complex_problem_id: UUID


class COCPMappingResponse(BaseModel):
    id: UUID
    organization_id: UUID
    course_outcome_id: UUID
    complex_problem_id: UUID
    status: str
    created_by_user_id: UUID | None
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── CO-CA Mappings ────────────────────────────────────────────────────────────

class COCAMappingCreate(BaseModel):
    course_outcome_id: UUID
    complex_activity_id: UUID


class COCAMappingResponse(BaseModel):
    id: UUID
    organization_id: UUID
    course_outcome_id: UUID
    complex_activity_id: UUID
    status: str
    created_by_user_id: UUID | None
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── CO-KP Mappings ────────────────────────────────────────────────────────────

class COKPMappingCreate(BaseModel):
    course_outcome_id: UUID
    knowledge_profile_id: UUID


class COKPMappingResponse(BaseModel):
    id: UUID
    organization_id: UUID
    course_outcome_id: UUID
    knowledge_profile_id: UUID
    status: str
    created_by_user_id: UUID | None
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── CO-PO Mapping Validation (CEP/CEA requirements) ───────────────────────────

class COMappingValidationIssue(BaseModel):
    course_outcome_id: UUID
    course_outcome_code: str
    missing_cep: bool
    missing_cea: bool


class COPOMappingValidationResponse(BaseModel):
    is_valid: bool
    issues: list[COMappingValidationIssue]


# ── Program Missions ──────────────────────────────────────────────────────────

class ProgramMissionCreate(BaseModel):
    program_id: UUID
    code: str = Field(min_length=1, max_length=20)
    statement: str
    order_index: int = Field(ge=0, le=32767)


class ProgramMissionUpdate(BaseModel):
    statement: str | None = None
    order_index: int | None = Field(default=None, ge=0, le=32767)


class ProgramMissionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    program_id: UUID
    code: str
    statement: str
    order_index: int
    status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Program Educational Objectives (PEO) ─────────────────────────────────────

class PEOCreate(BaseModel):
    program_id: UUID
    code: str = Field(min_length=1, max_length=20)
    statement: str
    order_index: int = Field(ge=0, le=32767)


class PEOUpdate(BaseModel):
    statement: str | None = None
    order_index: int | None = Field(default=None, ge=0, le=32767)


class PEOResponse(BaseModel):
    id: UUID
    organization_id: UUID
    program_id: UUID
    code: str
    statement: str
    order_index: int
    status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── PEO-PO & PEO-Mission Mappings ─────────────────────────────────────────────

class PEOMappingSet(BaseModel):
    po_ids: list[UUID] = Field(default_factory=list)


class PEOMissionMappingSet(BaseModel):
    mission_ids: list[UUID] = Field(default_factory=list)


class PEOPOMappingResponse(BaseModel):
    id: UUID
    peo_id: UUID
    program_outcome_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class PEOMissionMappingResponse(BaseModel):
    id: UUID
    peo_id: UUID
    mission_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
