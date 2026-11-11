from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ExamType = Literal["MID", "FINAL"]


class AuditableSection(BaseModel):
    id: UUID
    course_code: str
    course_title: str
    section_name: str
    term_name: str
    batch_name: str


class ExtractedQuestion(BaseModel):
    label: str
    text: str
    context: str | None = None
    marks: float | None = None
    co: str | None = None
    figure: str | None = None
    # Set when the wording could not be found in the uploaded document.
    warning: str | None = None
    # The marksheet question with the same label, if there is one.
    matched_question_id: UUID | None = None


class QuestionPaperResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exam_type: str
    original_filename: str
    content_type: str
    file_size_bytes: int
    page_count: int | None
    extraction_method: str | None
    extraction_status: str
    extraction_error: str | None
    extraction_model: str | None
    extraction_prompt_version: str | None
    updated_at: datetime
    questions: list[ExtractedQuestion] = []


class QuestionTextItem(BaseModel):
    question_id: UUID
    question_text: str | None = Field(default=None, max_length=5000)


class QuestionTextsUpdate(BaseModel):
    items: list[QuestionTextItem] = Field(min_length=1)


class BloomLevelRef(BaseModel):
    id: UUID
    code: str
    name: str


class CourseOutcomeRef(BaseModel):
    id: UUID
    code: str
    statement: str


class QuestionAuditResponse(BaseModel):
    id: UUID
    alignment: str
    confidence: float | None
    raw_confidence: float | None = None
    # Share of the independent judgments that agree with the result, and how many there were.
    agreement: float | None = None
    samples: int | None = None
    rationale: str | None
    evidence_quote: str | None
    ai_bloom_level: BloomLevelRef | None
    ai_course_outcome: CourseOutcomeRef | None
    model: str
    prompt_version: str
    review_status: str
    override_reason: str | None
    reviewed_at: datetime | None
    created_at: datetime


class AuditedQuestion(BaseModel):
    question_id: UUID
    label: str
    max_marks: float
    question_text: str | None
    declared_bloom_level: BloomLevelRef | None
    declared_course_outcome: CourseOutcomeRef | None
    audit: QuestionAuditResponse | None


class IntegritySummary(BaseModel):
    questions: int
    with_text: int
    audited: int
    aligned: int
    partial: int
    misaligned: int
    abstained: int
    pending_review: int


class IntegrityJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: Literal["READ_PAPER", "AUDIT"]
    status: Literal["QUEUED", "RUNNING", "DONE", "FAILED"]
    progress_done: int
    progress_total: int | None
    error: str | None
    result: dict | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class IntegrityOverview(BaseModel):
    section: AuditableSection
    exam_type: str
    paper: QuestionPaperResponse | None
    questions: list[AuditedQuestion]
    summary: IntegritySummary
    # The latest background job for this exam (reading or auditing), if any.
    job: IntegrityJobResponse | None = None


class AuditReviewRequest(BaseModel):
    decision: Literal["ACCEPT", "OVERRIDE"]
    reason: str | None = Field(default=None, max_length=2000)
