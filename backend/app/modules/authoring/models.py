"""
OutcomeSuggestion — one AI suggestion for a course: drafted COs, a refined CO
statement, or a set of CO-PO links.

Suggestions are advisory. Nothing here changes a CO or a mapping; a teacher accepts
a suggestion through the normal CO and mapping endpoints (or the apply endpoint,
which re-checks every link against the mapping rules first). The row keeps what
was asked, what came back, the model and prompt version, and what the teacher did
with it, so suggestions can be traced and measured.
"""
import sqlalchemy as sa
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base

KINDS = ("CO_DRAFT", "CO_REFINE", "CO_PO_MAPPING", "OUTLINE_IMPORT")
DECISIONS = ("ACCEPTED", "EDITED", "PARTIAL", "REJECTED")


class OutcomeSuggestion(Base):
    __tablename__ = "outcome_suggestions"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('CO_DRAFT','CO_REFINE','CO_PO_MAPPING','OUTLINE_IMPORT')",
            name="chk_obe_outcome_suggestion_kind",
        ),
        CheckConstraint(
            "decision IS NULL OR decision IN ('ACCEPTED','EDITED','PARTIAL','REJECTED')",
            name="chk_obe_outcome_suggestion_decision",
        ),
        Index("ix_obe_outcome_suggestions_course", "curriculum_id", "course_id", "created_at"),
        {"schema": "obe"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    curriculum_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.curricula.id", ondelete="CASCADE"),
        nullable=False,
    )
    course_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Plain UUID — no FK constraint (cross-schema IAM)
    user_id = Column(PGUUID(as_uuid=True), nullable=True)
    kind = Column(String(20), nullable=False)
    # What the teacher asked for (instruction, statement to refine, count…)
    request = Column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    # What was shown to the teacher, after the rule and quality checks
    result = Column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    provider = Column(String(10), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_version = Column(String(50), nullable=False)
    decision = Column(String(10), nullable=True)
    # e.g. which drafts or links were accepted, and the final wording
    decision_detail = Column(JSONB, nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
