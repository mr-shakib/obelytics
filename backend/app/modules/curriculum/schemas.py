from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Curriculum ────────────────────────────────────────────────────────────────

class CurriculumCreate(BaseModel):
    program_id: UUID
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    effective_year: int = Field(ge=1900, le=2100)


class CurriculumUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class CurriculumResponse(BaseModel):
    id: UUID
    organization_id: UUID
    program_id: UUID
    name: str
    code: str
    effective_year: int
    version_number: int
    parent_curriculum_id: UUID | None
    status: str
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
    course_type_id: UUID
    code: str = Field(min_length=1, max_length=30)
    title: str = Field(min_length=1, max_length=255)
    credits: int = Field(ge=0, le=20)
    theory_hours: int = Field(default=0, ge=0)
    lab_hours: int = Field(default=0, ge=0)
    description: str | None = None


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    credits: int | None = Field(default=None, ge=0, le=20)
    description: str | None = None
    theory_hours: int | None = Field(default=None, ge=0)
    lab_hours: int | None = Field(default=None, ge=0)


class CourseResponse(BaseModel):
    id: UUID
    organization_id: UUID
    course_type_id: UUID
    code: str
    title: str
    credits: int
    theory_hours: int
    lab_hours: int
    description: str | None
    status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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
    credits: int
    theory_hours: int
    lab_hours: int
    is_elective: bool
    offerings: list[SectionOfferingInfo]


# ── Batch Semester Plan ───────────────────────────────────────────────────────

class BatchSemesterCourse(BaseModel):
    course_id: UUID
    code: str
    title: str
    credits: int
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
    total_credits: int
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
