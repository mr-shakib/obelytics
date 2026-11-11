"""
Assessment integrity — is reported attainment backed by what the exam tested?

A QuestionPaper is the exam paper a section offering actually sat. Only the
extracted text and a SHA-256 of the upload are kept; the file itself is not
stored, so an unreleased paper never sits in third-party object storage.

A QuestionAudit is one AI judgment of one marksheet question: the Bloom level
and course outcome the question actually exercises, compared with what the
teacher declared. Audits are advisory — they never change marks or official
attainment — and each records the model and prompt version that produced it.
Re-running an audit keeps the history; exactly one row per question is current.
"""
import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base

EXTRACTION_STATUSES = ("PENDING", "EXTRACTED", "FAILED")

# How the wording was obtained:
# VISION     — page images read by a vision model (scans, phone photos)
# TEXT_LAYER — the PDF's own text (born-digital), split into questions by a text model
# DOCX       — a Word document's text, split into questions by a text model
# MIXED      — some pages each way
EXTRACTION_METHODS = ("VISION", "TEXT_LAYER", "DOCX", "MIXED")

# READ_PAPER — read an uploaded paper into questions
# AUDIT      — judge every question that has wording
JOB_KINDS = ("READ_PAPER", "AUDIT")
JOB_STATUSES = ("QUEUED", "RUNNING", "DONE", "FAILED")
ACTIVE_JOB_STATUSES = ("QUEUED", "RUNNING")

# ALIGNED    — the question exercises the declared CO at the declared Bloom level
# PARTIAL    — right CO, but a lower or higher Bloom level than declared
# MISALIGNED — the question does not exercise the declared CO
# ABSTAINED  — the model was not confident enough to judge
ALIGNMENTS = ("ALIGNED", "PARTIAL", "MISALIGNED", "ABSTAINED")

# PENDING    — not yet seen by a teacher
# ACCEPTED   — a teacher agreed with the judgment
# OVERRIDDEN — a teacher disagreed and recorded why
REVIEW_STATUSES = ("PENDING", "ACCEPTED", "OVERRIDDEN")


class QuestionPaper(Base):
    __tablename__ = "question_papers"
    __table_args__ = (
        UniqueConstraint(
            "section_offering_id", "exam_type",
            name="uq_integrity_question_paper_offering_exam",
        ),
        CheckConstraint("exam_type IN ('MID', 'FINAL')", name="chk_integrity_question_paper_exam_type"),
        CheckConstraint(
            "extraction_status IN ('PENDING','EXTRACTED','FAILED')",
            name="chk_integrity_question_paper_extraction_status",
        ),
        {"schema": "integrity"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    section_offering_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.section_offerings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exam_type = Column(String(10), nullable=False)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    file_sha256 = Column(String(64), nullable=False)
    extracted_text = Column(Text, nullable=True)
    # The questions as the model read them: [{label, text, marks, co, context, figure}]
    extracted_questions = Column(JSONB, nullable=True)
    page_count = Column(Integer, nullable=True)
    extraction_method = Column(String(20), nullable=True)
    extraction_model = Column(String(100), nullable=True)
    extraction_prompt_version = Column(String(50), nullable=True)
    extraction_status = Column(String(20), nullable=False, server_default=sa.text("'PENDING'"))
    extraction_error = Column(Text, nullable=True)
    # Plain UUID — no FK constraint (cross-schema IAM)
    uploaded_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class QuestionAudit(Base):
    __tablename__ = "question_audits"
    __table_args__ = (
        Index(
            "uq_integrity_question_audit_current",
            "question_id",
            unique=True,
            postgresql_where=sa.text("is_current"),
        ),
        CheckConstraint(
            "alignment IN ('ALIGNED','PARTIAL','MISALIGNED','ABSTAINED')",
            name="chk_integrity_question_audit_alignment",
        ),
        CheckConstraint(
            "review_status IN ('PENDING','ACCEPTED','OVERRIDDEN')",
            name="chk_integrity_question_audit_review_status",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="chk_integrity_question_audit_confidence",
        ),
        # A teacher may disagree with the AI, but must say why.
        CheckConstraint(
            "review_status <> 'OVERRIDDEN' OR override_reason IS NOT NULL",
            name="chk_integrity_question_audit_override_reason",
        ),
        {"schema": "integrity"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("assessment.marksheet_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_paper_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("integrity.question_papers.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Both judgments are NULL when the model abstained.
    ai_bloom_level_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("config.bloom_levels.id", ondelete="RESTRICT"),
        nullable=True,
    )
    ai_course_outcome_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.course_outcomes.id", ondelete="SET NULL"),
        nullable=True,
    )
    alignment = Column(String(20), nullable=False)
    # confidence: after calibration (what the threshold uses); raw_confidence: before it.
    confidence = Column(Numeric(4, 3), nullable=True)
    raw_confidence = Column(Numeric(4, 3), nullable=True)
    # How the judgment was reached: the independent samples, their agreement, calibration.
    details = Column(JSONB, nullable=True)
    rationale = Column(Text, nullable=True)
    evidence_quote = Column(Text, nullable=True)
    model = Column(String(100), nullable=False)
    prompt_version = Column(String(50), nullable=False)
    is_current = Column(Boolean, nullable=False, server_default=sa.text("TRUE"))
    review_status = Column(String(20), nullable=False, server_default=sa.text("'PENDING'"))
    override_reason = Column(Text, nullable=True)
    # Plain UUID — no FK constraint (cross-schema IAM)
    reviewed_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class IntegrityJob(Base):
    """
    Background work for one exam of one section: reading a paper or running an audit.
    At most one job per exam is active at a time (enforced by the database), and the
    page shows its progress while it runs.
    """
    __tablename__ = "jobs"
    __table_args__ = (
        Index(
            "uq_integrity_job_active",
            "section_offering_id",
            "exam_type",
            unique=True,
            postgresql_where=sa.text("status IN ('QUEUED','RUNNING')"),
        ),
        Index("ix_integrity_jobs_offering_exam_created", "section_offering_id", "exam_type", "created_at"),
        CheckConstraint("kind IN ('READ_PAPER','AUDIT')", name="chk_integrity_job_kind"),
        CheckConstraint(
            "status IN ('QUEUED','RUNNING','DONE','FAILED')", name="chk_integrity_job_status"
        ),
        CheckConstraint("exam_type IN ('MID', 'FINAL')", name="chk_integrity_job_exam_type"),
        {"schema": "integrity"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    section_offering_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.section_offerings.id", ondelete="CASCADE"),
        nullable=False,
    )
    exam_type = Column(String(10), nullable=False)
    kind = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, server_default=sa.text("'QUEUED'"))
    progress_done = Column(Integer, nullable=False, server_default=sa.text("0"))
    progress_total = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    # A short outcome for the page, e.g. {"questions": 12} or {"audited": 9}
    result = Column(JSONB, nullable=True)
    # Plain UUID — no FK constraint (cross-schema IAM)
    created_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
