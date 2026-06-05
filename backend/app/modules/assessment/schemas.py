from decimal import Decimal
from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel


# ── Student ───────────────────────────────────────────────────────────────────

class StudentCreate(BaseModel):
    student_id_number: str
    full_name: str
    email: Optional[str] = None
    program_id: Optional[UUID] = None
    batch_id: Optional[UUID] = None


class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    program_id: Optional[UUID] = None
    batch_id: Optional[UUID] = None


class StudentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    organization_id: UUID
    student_id_number: str
    full_name: str
    email: Optional[str]
    program_id: Optional[UUID]
    batch_id: Optional[UUID]
    status: str
    created_at: datetime
    updated_at: datetime


# ── Enrollment ────────────────────────────────────────────────────────────────

class EnrollmentCreate(BaseModel):
    student_id: UUID
    section_offering_id: UUID


class EnrollmentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    organization_id: UUID
    student_id: UUID
    section_offering_id: UUID
    status: str
    enrolled_at: datetime
    created_at: datetime


# ── Assessment ────────────────────────────────────────────────────────────────

class AssessmentCreate(BaseModel):
    section_offering_id: UUID
    assessment_type_id: UUID
    name: str
    total_marks: Decimal
    weightage_percent: Decimal


class AssessmentUpdate(BaseModel):
    name: Optional[str] = None
    total_marks: Optional[Decimal] = None
    weightage_percent: Optional[Decimal] = None


class AssessmentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    organization_id: UUID
    section_offering_id: UUID
    assessment_type_id: UUID
    name: str
    total_marks: Decimal
    weightage_percent: Decimal
    status: str
    created_at: datetime
    updated_at: datetime


# ── Assessment CO Weight ──────────────────────────────────────────────────────

class AssessmentCOWeightCreate(BaseModel):
    course_outcome_id: UUID
    contribution_percent: Decimal


class AssessmentCOWeightResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    assessment_id: UUID
    course_outcome_id: UUID
    contribution_percent: Decimal
    created_at: datetime


# ── Marks ─────────────────────────────────────────────────────────────────────

class MarkCreate(BaseModel):
    assessment_id: UUID
    student_enrollment_id: UUID
    marks_obtained: Optional[Decimal] = None
    is_absent: bool = False


class MarkUpdate(BaseModel):
    marks_obtained: Optional[Decimal] = None
    is_absent: Optional[bool] = None


class MarkResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    organization_id: UUID
    assessment_id: UUID
    student_enrollment_id: UUID
    marks_obtained: Optional[Decimal]
    is_absent: bool
    entered_by_user_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime


# ── Result Publication ────────────────────────────────────────────────────────

class ResultPublicationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    organization_id: UUID
    section_offering_id: UUID
    status: str
    submitted_by_user_id: Optional[UUID]
    submitted_at: Optional[datetime]
    ml_approved_by_user_id: Optional[UUID]
    ml_approved_at: Optional[datetime]
    ml_rejection_comment: Optional[str]
    pc_approved_by_user_id: Optional[UUID]
    pc_approved_at: Optional[datetime]
    published_by_user_id: Optional[UUID]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class MLRejectRequest(BaseModel):
    comment: str
