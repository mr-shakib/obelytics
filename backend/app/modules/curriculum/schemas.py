from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, computed_field


# ── Curriculum ────────────────────────────────────────────────────────────────

class CurriculumCreate(BaseModel):
    program_id: UUID
    name: str = Field(min_length=1, max_length=255)
    effective_year: int = Field(ge=1900, le=2100)
    threshold_co_score_pct: Decimal = Field(default=Decimal("50"), ge=0, le=100)


class CurriculumUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    threshold_co_score_pct: Decimal | None = Field(default=None, ge=0, le=100)


class CurriculumResponse(BaseModel):
    id: UUID
    organization_id: UUID
    program_id: UUID
    name: str
    effective_year: int
    version_number: int
    parent_curriculum_id: UUID | None
    status: str
    threshold_co_score_pct: Decimal
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Curriculum Term Definition ─────────────────────────────────────────────────

class CurriculumTermDefinitionCreate(BaseModel):
    # Supplied via the URL path (`/curricula/{curriculum_id}/terms`) and injected
    # server-side — optional here so clients don't have to repeat it in the body.
    curriculum_id: UUID | None = None
    term_number: int = Field(ge=1, le=20)
    name: str = Field(min_length=1, max_length=100)
    total_credit_hours: int | None = Field(default=None, ge=0)


class CurriculumTermDefinitionResponse(BaseModel):
    id: UUID
    curriculum_id: UUID
    term_number: int
    name: str
    total_credit_hours: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Course ────────────────────────────────────────────────────────────────────

class CourseCreate(BaseModel):
    course_category_id: UUID
    course_type: Literal["THEORY", "LAB", "THESIS_DEFENSE"]
    code: str = Field(min_length=1, max_length=30)
    title: str = Field(min_length=1, max_length=255)
    credits: float = Field(ge=0, le=20)
    theory_hours: int = Field(default=0, ge=0)
    lab_hours: int = Field(default=0, ge=0)
    description: str | None = None


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    credits: float | None = Field(default=None, ge=0, le=20)
    description: str | None = None
    syllabus_content: str | None = None
    theory_hours: int | None = Field(default=None, ge=0)
    lab_hours: int | None = Field(default=None, ge=0)


class CourseResponse(BaseModel):
    id: UUID
    organization_id: UUID
    course_category_id: UUID
    course_type: str
    code: str
    title: str
    credits: float
    theory_hours: int
    lab_hours: int
    description: str | None
    syllabus_content: str | None
    status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Course Bulk Import ────────────────────────────────────────────────────────

class CourseBulkImportItem(BaseModel):
    course_category_id: UUID
    course_type: Literal["THEORY", "LAB", "THESIS_DEFENSE"]
    code: str = Field(min_length=1, max_length=30)
    title: str = Field(min_length=1, max_length=255)
    credits: float = Field(ge=0, le=20)
    theory_hours: int = Field(default=0, ge=0)
    lab_hours: int = Field(default=0, ge=0)
    description: str | None = None


class CourseBulkImportRequest(BaseModel):
    courses: list[CourseBulkImportItem]


class CourseBulkImportError(BaseModel):
    row: int
    code: str
    message: str


class CourseBulkImportResponse(BaseModel):
    created: int
    errors: list[CourseBulkImportError]


# ── Course Objectives ─────────────────────────────────────────────────────────

class CourseObjectiveResponse(BaseModel):
    id: UUID
    course_id: UUID
    order_index: int
    statement: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseObjectivesUpdate(BaseModel):
    statements: list[str] = Field(default_factory=list)


# ── Course Learning Materials ─────────────────────────────────────────────────

class CourseLearningMaterialResponse(BaseModel):
    id: UUID
    course_id: UUID
    material_type: Literal["TEXTBOOK", "REFERENCE"]
    order_index: int
    title: str
    authors: str | None
    publisher: str | None
    edition_year: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseLearningMaterialInput(BaseModel):
    material_type: Literal["TEXTBOOK", "REFERENCE"]
    title: str = Field(min_length=1, max_length=500)
    authors: str | None = Field(default=None, max_length=500)
    publisher: str | None = Field(default=None, max_length=255)
    edition_year: str | None = Field(default=None, max_length=100)


class CourseLearningMaterialsUpdate(BaseModel):
    materials: list[CourseLearningMaterialInput] = Field(default_factory=list)


# ── Course Lesson Plan ────────────────────────────────────────────────────────

class LessonPlanItemInput(BaseModel):
    week_number: int = Field(ge=1, le=52)
    lesson_label: str | None = Field(default=None, max_length=100)
    topic: str = Field(min_length=1)
    tla: str | None = None
    assessment_strategy: str | None = None
    co_ids: list[UUID] = Field(default_factory=list)
    po_ids: list[UUID] = Field(default_factory=list)


class LessonPlanItemResponse(BaseModel):
    id: UUID
    curriculum_id: UUID
    course_id: UUID
    week_number: int
    lesson_label: str | None
    topic: str
    tla: str | None
    assessment_strategy: str | None
    order_index: int
    co_ids: list[UUID] = Field(default_factory=list)
    po_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LessonPlanItemsUpdate(BaseModel):
    items: list[LessonPlanItemInput] = Field(default_factory=list)


# ── Course Bloom Domains ──────────────────────────────────────────────────────

class CourseBloomDomainsUpdate(BaseModel):
    bloom_domain_ids: list[UUID]


# ── Course Assessment Tools ──────────────────────────────────────────────────

class CourseAssessmentToolResponse(BaseModel):
    id: UUID
    curriculum_id: UUID
    course_id: UUID
    assessment_type_id: UUID
    assessment_type_name: str
    is_sessional: bool
    is_locked: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseAssessmentToolsUpdate(BaseModel):
    assessment_type_ids: list[UUID]


# ── Course Assessment Pattern (CO-wise marks) ─────────────────────────────────

class CourseCOMarkInput(BaseModel):
    assessment_type_id: UUID
    course_outcome_id: UUID | None = None
    marks: Decimal = Field(ge=0, le=999)


class CourseCOMarkResponse(BaseModel):
    id: UUID
    curriculum_id: UUID
    course_id: UUID
    assessment_type_id: UUID
    course_outcome_id: UUID | None
    marks: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseCOMarksUpdate(BaseModel):
    marks: list[CourseCOMarkInput] = Field(default_factory=list)


# ── Course Bloom Marks (CIE/SEE breakdown) ────────────────────────────────────

class CourseBloomMarkInput(BaseModel):
    assessment_type_id: UUID
    bloom_level_id: UUID
    component: Literal["CIE", "SEE"]
    marks: Decimal = Field(ge=0, le=999)


class CourseBloomMarkResponse(BaseModel):
    id: UUID
    curriculum_id: UUID
    course_id: UUID
    assessment_type_id: UUID
    bloom_level_id: UUID
    component: Literal["CIE", "SEE"]
    marks: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseBloomMarksUpdate(BaseModel):
    marks: list[CourseBloomMarkInput] = Field(default_factory=list)


# ── Course Slot ───────────────────────────────────────────────────────────────

class CourseSlotCreate(BaseModel):
    # Supplied via the URL path (`/curricula/{curriculum_id}/course-slots`) and
    # injected server-side — optional here so clients don't have to repeat it.
    curriculum_id: UUID | None = None
    curriculum_term_definition_id: UUID
    course_id: UUID
    is_elective: bool = False


class CourseSlotResponse(BaseModel):
    id: UUID
    curriculum_id: UUID
    curriculum_term_definition_id: UUID
    course_id: UUID
    is_elective: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Prerequisite ──────────────────────────────────────────────────────────────

class PrerequisiteCreate(BaseModel):
    # Supplied via the URL path (`/courses/{course_id}/prerequisites`) and injected
    # server-side — optional here so clients don't have to repeat it.
    course_id: UUID | None = None
    prerequisite_course_id: UUID


class PrerequisiteResponse(BaseModel):
    id: UUID
    organization_id: UUID
    course_id: UUID
    prerequisite_course_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Batch ─────────────────────────────────────────────────────────────────────

class BatchCreate(BaseModel):
    curriculum_id: UUID
    name: str = Field(min_length=1, max_length=100)
    start_date: date
    term_system: str = Field(pattern="^(TRIMESTER|SEMESTER)$")
    num_semesters: int = Field(ge=1, le=30)


class BatchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    status: str | None = Field(default=None, pattern="^(ACTIVE|GRADUATED|ARCHIVED)$")
    curriculum_id: UUID | None = None


class BatchTermCalendarEntry(BaseModel):
    term_number: int
    academic_term_id: UUID
    name: str
    year: int
    season: str
    start_date: date
    end_date: date
    status: str


class BatchResponse(BaseModel):
    id: UUID
    organization_id: UUID
    curriculum_id: UUID
    name: str
    intake_year: int | None
    start_date: date | None
    term_system: str | None
    num_semesters: int | None
    status: str
    created_at: datetime
    updated_at: datetime
    term_calendar: list[BatchTermCalendarEntry] = []

    model_config = {"from_attributes": True}


# ── Batch Term Offerings ──────────────────────────────────────────────────────

class AddSectionOfferingBody(BaseModel):
    course_id: UUID
    section_name: str = Field(min_length=1, max_length=20)


class SectionOfferingInfo(BaseModel):
    id: UUID
    section_id: UUID
    section_name: str
    capacity: int | None
    status: str


class BatchTermOfferingCourse(BaseModel):
    course_id: UUID
    curriculum_term_definition_id: UUID
    code: str
    title: str
    credits: float
    theory_hours: int
    lab_hours: int
    is_elective: bool
    offerings: list[SectionOfferingInfo]


# ── Batch Semester Plan ───────────────────────────────────────────────────────

class BatchSemesterCourse(BaseModel):
    course_id: UUID
    code: str
    title: str
    credits: float
    theory_hours: int
    lab_hours: int
    is_elective: bool


class BatchSemesterPlanItem(BaseModel):
    term_number: int
    academic_term_id: UUID
    name: str
    year: int
    season: str
    start_date: date
    end_date: date
    status: str
    total_credits: float
    courses: list[BatchSemesterCourse]


# ── Academic Term ─────────────────────────────────────────────────────────────

class AcademicTermCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1900, le=9999)
    season: str = Field(pattern="^(SPRING|SUMMER|FALL|WINTER)$")
    start_date: date
    end_date: date


class AcademicTermUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = Field(default=None, pattern="^(UPCOMING|ACTIVE|COMPLETED)$")


class AcademicTermResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    year: int
    season: str
    start_date: date
    end_date: date
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Section ───────────────────────────────────────────────────────────────────

class SectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    capacity: int | None = Field(default=None, ge=1)


class SectionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    capacity: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Section Offering ──────────────────────────────────────────────────────────

class SectionOfferingCreate(BaseModel):
    curriculum_id: UUID
    batch_id: UUID
    course_id: UUID
    academic_term_id: UUID
    section_id: UUID


class SectionOfferingUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(UPCOMING|ACTIVE|COMPLETED)$")


class SectionOfferingResponse(BaseModel):
    id: UUID
    organization_id: UUID
    curriculum_id: UUID
    batch_id: UUID
    course_id: UUID
    academic_term_id: UUID
    section_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SectionOfferingDependents(BaseModel):
    """Counts of records that reference a section offering. Used to warn the user
    before a cascade delete."""

    enrolled_students: int = 0
    assessments: int = 0
    marksheet_questions: int = 0
    student_marks: int = 0
    result_publications: int = 0
    course_end_reports: int = 0
    co_attainment_results: int = 0
    po_attainment_results: int = 0
    faculty_assignments: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> int:
        return (
            self.enrolled_students
            + self.assessments
            + self.marksheet_questions
            + self.student_marks
            + self.result_publications
            + self.course_end_reports
            + self.co_attainment_results
            + self.po_attainment_results
            + self.faculty_assignments
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_dependents(self) -> bool:
        return self.total > 0


# ── Faculty Assignment ────────────────────────────────────────────────────────

class FacultyAssignmentCreate(BaseModel):
    section_offering_id: UUID
    user_id: UUID
    role_in_course: str = Field(pattern="^(MODULE_LEADER|SECTION_TEACHER)$")


class FacultyAssignmentResponse(BaseModel):
    id: UUID
    section_offering_id: UUID
    user_id: UUID
    role_in_course: str
    assigned_at: datetime
    removed_at: datetime | None

    model_config = {"from_attributes": True}


class MySectionResponse(BaseModel):
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
    status: str
    result_status: str
    student_count: int

    model_config = {"from_attributes": True}


# ── Module Leader Assignment ─────────────────────────────────────────────────

class ModuleLeaderAssignmentCreate(BaseModel):
    batch_id: UUID
    academic_term_id: UUID
    course_id: UUID
    user_id: UUID


class ModuleLeaderAssignmentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    batch_id: UUID
    academic_term_id: UUID
    course_id: UUID
    user_id: UUID
    assigned_at: datetime
    removed_at: datetime | None

    model_config = {"from_attributes": True}
