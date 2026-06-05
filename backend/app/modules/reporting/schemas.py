from pydantic import BaseModel
from uuid import UUID
from decimal import Decimal


# Assessment Summary Report
class AssessmentStatRow(BaseModel):
    assessment_id: UUID
    name: str
    total_marks: Decimal
    weightage_percent: Decimal
    status: str
    enrolled_count: int
    marks_entered_count: int
    absent_count: int
    scored_count: int
    average_score: Decimal | None
    max_score: Decimal | None
    min_score: Decimal | None
    pass_count: int
    pass_rate: Decimal | None


class AssessmentSummaryReport(BaseModel):
    section_offering_id: UUID
    organization_id: UUID
    total_enrolled: int
    assessments: list[AssessmentStatRow]


# CO Attainment Report
class COAttainmentRow(BaseModel):
    course_outcome_id: UUID
    average_attainment_pct: Decimal
    students_above_threshold: int
    total_students: int
    is_attained: bool


class POAttainmentRow(BaseModel):
    program_outcome_id: UUID
    attainment_pct: Decimal
    contributing_co_count: int
    is_attained: bool


class COAttainmentReport(BaseModel):
    section_offering_id: UUID
    co_attainments: list[COAttainmentRow]
    po_attainments: list[POAttainmentRow]


# Program PO Attainment Report
class ProgramPORow(BaseModel):
    program_outcome_id: UUID
    avg_attainment_pct: Decimal
    offering_count: int
    attained_count: int


class ProgramPOAttainmentReport(BaseModel):
    program_id: UUID
    academic_term_id: UUID
    organization_id: UUID
    po_rows: list[ProgramPORow]
