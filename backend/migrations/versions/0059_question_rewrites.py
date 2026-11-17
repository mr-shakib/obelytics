"""Question rewrites: AI rewrites of a question, verified by the auditor

Revision ID: 0059_question_rewrites
Revises: 0058_outcome_authoring
Create Date: 2026-11-12 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0059_question_rewrites"
down_revision: Union[str, None] = "0058_outcome_authoring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UUID = sa.dialects.postgresql.UUID(as_uuid=True)
_JSONB = sa.dialects.postgresql.JSONB()


def upgrade() -> None:
    op.create_table(
        "question_rewrites",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", _UUID,
                  sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("question_id", _UUID,
                  sa.ForeignKey("assessment.marksheet_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_course_outcome_id", _UUID,
                  sa.ForeignKey("obe.course_outcomes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_bloom_code", sa.String(10), nullable=True),
        sa.Column("instruction", sa.Text(), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("rewritten_text", sa.Text(), nullable=False),
        sa.Column("changes", _JSONB, nullable=True),
        sa.Column("attempts", _JSONB, nullable=False),
        sa.Column("verified_alignment", sa.String(20), nullable=False),
        sa.Column("verified_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("decision", sa.String(10), nullable=True),
        sa.Column("created_by_user_id", _UUID, nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(
            "verified_alignment IN ('ALIGNED','PARTIAL','MISALIGNED','ABSTAINED')",
            name="chk_integrity_question_rewrite_alignment",
        ),
        sa.CheckConstraint(
            "decision IS NULL OR decision IN ('KEPT','DISCARDED')",
            name="chk_integrity_question_rewrite_decision",
        ),
        schema="integrity",
    )
    op.create_index("ix_integrity_question_rewrites_organization_id", "question_rewrites",
                    ["organization_id"], schema="integrity")
    op.create_index("ix_integrity_question_rewrites_question_id", "question_rewrites",
                    ["question_id"], schema="integrity")


def downgrade() -> None:
    op.drop_index("ix_integrity_question_rewrites_question_id", table_name="question_rewrites",
                  schema="integrity")
    op.drop_index("ix_integrity_question_rewrites_organization_id", table_name="question_rewrites",
                  schema="integrity")
    op.drop_table("question_rewrites", schema="integrity")
