from decimal import Decimal
from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field


# ── Student ───────────────────────────────────────────────────────────────────

class StudentCreate(BaseModel):
    student_id_number: str
    full_name: str
    batch_id: UUID
    email: Optional[str] = None
    program_id: Optional[UUID] = None


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
    batch_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime


class StudentBulkImportItem(BaseModel):
    student_id_number: str
    full_name: str
    batch_id: UUID
    email: Optional[str] = None
    program_id: Optional[UUID] = None


class StudentBulkImportRequest(BaseModel):
    students: list[StudentBulkImportItem]


class StudentBulkImportError(BaseModel):
    row: int
    student_id_number: str
    message: str


class StudentBulkImportResponse(BaseModel):
    created: int
    updated: int
    errors: list[StudentBulkImportError]


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


class EnrollmentWithStudentResponse(BaseModel):
    id: UUID
    student_id: UUID
    student_id_number: str
    full_name: str
    email: Optional[str]
    status: str
    enrolled_at: datetime


class EnrollmentBulkCreate(BaseModel):
    section_offering_id: UUID
    student_ids: list[UUID]


class EnrollmentBulkResponse(BaseModel):
    enrolled: int
    already_enrolled: int
    not_found: int


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


class ResultSubmissionListItem(BaseModel):
    model_config = {"from_attributes": True}

    section_offering_id: UUID
    course_id: UUID
    course_code: str
    course_title: str
    batch_id: UUID
    batch_name: str
    academic_term_id: UUID
    term_name: str
    term_year: int
    term_season: str
    section_id: UUID
    section_name: str
    result_publication_id: Optional[UUID]
    status: str
    submitted_at: Optional[datetime]
    ml_rejection_comment: Optional[str]
    student_count: int
    end_report_status: Optional[str] = None


class BulkApproveMLRequest(BaseModel):
    course_id: UUID
    batch_id: Optional[UUID] = None
    academic_term_id: Optional[UUID] = None


class BulkApproveMLResponse(BaseModel):
    approved_count: int


class BulkApprovePCRequest(BaseModel):
    course_id: UUID
    batch_id: Optional[UUID] = None
    academic_term_id: Optional[UUID] = None


class BulkApprovePCResponse(BaseModel):
    published_count: int


# ── Student results (CO/PO attainment) ────────────────────────────────────────

class StudentCOResult(BaseModel):
    co_code: str
    co_statement: str
    attainment_percentage: float
    threshold: float
    is_threshold_met: bool


class StudentPOResult(BaseModel):
    po_code: str
    po_statement: Optional[str] = None
    attainment_percentage: float
    threshold: float
    is_threshold_met: bool


class StudentCourseResult(BaseModel):
    course_code: str
    course_title: str
    term_name: str
    result_status: str
    total_marks_obtained: float
    total_marks: float
    percentage: float
    grade: Optional[str] = None
    co_results: list[StudentCOResult] = Field(default_factory=list)
    po_results: list[StudentPOResult] = Field(default_factory=list)


class PublicStudentResults(BaseModel):
    """Public (unauthenticated) result lookup payload."""

    student_id_number: str
    full_name: str
    results: list[StudentCourseResult] = Field(default_factory=list)


# ── Marksheet ─────────────────────────────────────────────────────────────────

class MarksheetQuestionInput(BaseModel):
    id: Optional[UUID] = None
    label: str
    max_marks: Decimal
    course_outcome_id: Optional[UUID] = None
    order_index: int


class MarksheetQuestionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    section_offering_id: UUID
    exam_type: str
    label: str
    max_marks: Decimal
    course_outcome_id: Optional[UUID]
    order_index: int


class MarksheetQuestionsUpdate(BaseModel):
    questions: list[MarksheetQuestionInput]


class MarksheetCellUpdate(BaseModel):
    question_id: UUID
    student_enrollment_id: UUID
    marks_obtained: Optional[Decimal] = None
    is_absent: bool = False


class MarksheetMarkResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    question_id: UUID
    student_enrollment_id: UUID
    marks_obtained: Optional[Decimal]
    is_absent: bool


class MarksheetMarkCell(BaseModel):
    mark_id: Optional[UUID] = None
    marks_obtained: Optional[Decimal] = None
    is_absent: bool = False


class MarksheetStudentRow(BaseModel):
    enrollment_id: UUID
    student_id_number: str
    full_name: str
    marks: dict[str, MarksheetMarkCell]
    total: Decimal


class MarksheetGridResponse(BaseModel):
    section_offering_id: UUID
    exam_type: str
    questions: list[MarksheetQuestionResponse]
    students: list[MarksheetStudentRow]


class COAttainmentPreview(BaseModel):
    course_outcome_id: UUID
    co_code: str
    max_marks: Decimal
    average_attainment_pct: Decimal
    students_above_threshold: int
    total_students: int
    is_attained: bool


class POAttainmentPreview(BaseModel):
    program_outcome_id: UUID
    po_code: str
    max_marks: Decimal
    attainment_pct: Decimal
    contributing_co_count: int
    students_above_threshold: int
    total_students: int
    is_attained: bool


class StudentAttainmentRow(BaseModel):
    enrollment_id: UUID
    student_id_number: str
    full_name: str
    co_results: dict[str, bool]
    po_results: dict[str, bool]
    co_marks: dict[str, Decimal]
    co_pct: dict[str, Decimal]
    po_marks: dict[str, Decimal]
    po_pct: dict[str, Decimal]


class MarksheetAttainmentResponse(BaseModel):
    threshold_co_score_pct: Decimal
    threshold_student_pct: Decimal
    cos: list[COAttainmentPreview]
    pos: list[POAttainmentPreview]
    students: list[StudentAttainmentRow]


# ── Course End Report ─────────────────────────────────────────────────────────

GRADES = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "D", "F"]


class UnattainedCOExplanation(BaseModel):
    co_code: str
    reason: str
    suggestion: str


class CombinedEndReportPdfRequest(BaseModel):
    """Module Leader's input when generating the combined course end report PDF."""

    course_id: UUID
    batch_id: UUID
    academic_term_id: UUID
    ml_feedback: str = ""
    # ML's justification for each unattained CO (combined attainment below threshold).
    unattained_justifications: list[UnattainedCOExplanation] = Field(default_factory=list)


class CourseEndReportCreate(BaseModel):
    grade_distribution: dict[str, int] = Field(default_factory=dict)
    co_attainment: dict[str, float] = Field(default_factory=dict)
    unattained_co_explanations: list[UnattainedCOExplanation] = Field(default_factory=list)
    teacher_feedback: str | None = None


class CourseEndReportSubmit(BaseModel):
    grade_distribution: dict[str, int] = Field(default_factory=dict)
    co_attainment: dict[str, float] = Field(default_factory=dict)
    unattained_co_explanations: list[UnattainedCOExplanation] = Field(default_factory=list)
    teacher_feedback: str | None = None


class CourseEndReportResponse(BaseModel):
    id: UUID
    organization_id: UUID
    section_offering_id: UUID
    created_by_user_id: UUID | None
    grade_distribution: dict[str, int]
    co_attainment: dict[str, float]
    unattained_co_explanations: list[UnattainedCOExplanation]
    teacher_feedback: str | None
    status: str
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
