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


class RewriteAttempt(BaseModel):
    text: str
    changes: list[str] = Field(default_factory=list)
    judged_bloom: str | None
    judged_co: str | None
    alignment: str
    confidence: float | None
    rationale: str | None
    evidence: str | None = None


class QuestionRewriteResponse(BaseModel):
    id: UUID
    question_id: UUID
    target_course_outcome: CourseOutcomeRef | None
    target_bloom_code: str | None
    original_text: str
    rewritten_text: str
    changes: list[str]
    # How the auditor, not told the target, judged the final wording.
    verified_alignment: str
    verified_confidence: float | None
    attempts: list[RewriteAttempt]
    model: str
    prompt_version: str
    decision: str | None
    created_at: datetime


class AuditedQuestion(BaseModel):
    question_id: UUID
    label: str
    max_marks: float
    question_text: str | None
    declared_bloom_level: BloomLevelRef | None
    declared_course_outcome: CourseOutcomeRef | None
    audit: QuestionAuditResponse | None
    # The latest rewrite the teacher kept for the next paper, if any.
    kept_rewrite: QuestionRewriteResponse | None = None


class QuestionRewriteRequest(BaseModel):
    # Default: the CO and Bloom level the question is mapped to.
    target_course_outcome_id: UUID | None = None
    target_bloom_code: Literal["C1", "C2", "C3", "C4", "C5", "C6"] | None = None
    instruction: str | None = Field(default=None, max_length=500)


class RewriteDecisionRequest(BaseModel):
    decision: Literal["KEPT", "DISCARDED"]


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


# ── Evidence-weighted attainment ──────────────────────────────────────────────

class COFigures(BaseModel):
    max_marks: float
    average_pct: float
    students_above: int
    total_students: int
    # Share of students at or above the threshold; the CO is attained when this reaches it.
    attained_share_pct: float
    is_attained: bool


class EvidenceQuestion(BaseModel):
    question_id: UUID
    label: str
    exam_type: str
    max_marks: float
    # SUPPORTED | CONTRADICTED | UNVERIFIED
    status: str
    alignment: str | None
    review_status: str | None
    ai_course_outcome: CourseOutcomeRef | None


class EvidenceOutcome(BaseModel):
    course_outcome: CourseOutcomeRef
    reported: COFigures
    # None when every question mapped to this CO is contradicted by the audit.
    evidence: COFigures | None
    # UNCHANGED | LOWER | NOT_SUPPORTED (reported attained, evidence not) | NO_EVIDENCE
    verdict: str
    # Share of this CO's marks on questions the audit judged (supported or contradicted).
    judged_marks_share: float
    questions: list[EvidenceQuestion]


class EvidenceSummary(BaseModel):
    outcomes: int
    reported_attained: int
    evidence_attained: int
    not_supported: int
    contradicted_questions: int
    contradicted_pending_review: int


class EvidenceAttainment(BaseModel):
    section: AuditableSection
    threshold_pct: float
    total_students: int
    outcomes: list[EvidenceOutcome]
    summary: EvidenceSummary
