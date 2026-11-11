"""Assessment integrity foundation — question text, declared Bloom level, papers, AI audits

Revision ID: 0056_integrity_foundation
Revises: 0055_course_code_per_curriculum
Create Date: 2026-10-26 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0056_integrity_foundation"
down_revision: Union[str, None] = "0055_course_code_per_curriculum"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UUID = sa.dialects.postgresql.UUID(as_uuid=True)

_PERMISSIONS = [
    ("integrity.read", "View question papers and AI question audits"),
    ("integrity.manage", "Upload question papers, run audits, review AI judgments"),
]


def upgrade() -> None:
    # ── Marksheet questions: wording + declared Bloom level ───────────────────
    op.add_column("marksheet_questions", sa.Column("question_text", sa.Text(), nullable=True),
                  schema="assessment")
    op.add_column(
        "marksheet_questions",
        sa.Column("declared_bloom_level_id", _UUID,
                  sa.ForeignKey("config.bloom_levels.id", ondelete="RESTRICT"), nullable=True),
        schema="assessment",
    )
    op.create_index("ix_assessment_marksheet_questions_declared_bloom_level_id",
                    "marksheet_questions", ["declared_bloom_level_id"], schema="assessment")

    op.execute("CREATE SCHEMA IF NOT EXISTS integrity")

    # ── Question papers (extracted text only — the file is not stored) ────────
    op.create_table(
        "question_papers",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", _UUID,
                  sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("section_offering_id", _UUID,
                  sa.ForeignKey("curriculum.section_offerings.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("exam_type", sa.String(10), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("extracted_questions", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("extraction_model", sa.String(100), nullable=True),
        sa.Column("extraction_prompt_version", sa.String(50), nullable=True),
        sa.Column("extraction_status", sa.String(20), nullable=False,
                  server_default=sa.text("'PENDING'")),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column("uploaded_by_user_id", _UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("section_offering_id", "exam_type",
                            name="uq_integrity_question_paper_offering_exam"),
        sa.CheckConstraint("exam_type IN ('MID', 'FINAL')",
                           name="chk_integrity_question_paper_exam_type"),
        sa.CheckConstraint("extraction_status IN ('PENDING','EXTRACTED','FAILED')",
                           name="chk_integrity_question_paper_extraction_status"),
        schema="integrity",
    )
    op.create_index("ix_integrity_question_papers_organization_id", "question_papers",
                    ["organization_id"], schema="integrity")
    op.create_index("ix_integrity_question_papers_section_offering_id", "question_papers",
                    ["section_offering_id"], schema="integrity")

    # ── Question audits (advisory AI judgments, history kept) ─────────────────
    op.create_table(
        "question_audits",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", _UUID,
                  sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("question_id", _UUID,
                  sa.ForeignKey("assessment.marksheet_questions.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("question_paper_id", _UUID,
                  sa.ForeignKey("integrity.question_papers.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("ai_bloom_level_id", _UUID,
                  sa.ForeignKey("config.bloom_levels.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("ai_course_outcome_id", _UUID,
                  sa.ForeignKey("obe.course_outcomes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("alignment", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("evidence_quote", sa.Text(), nullable=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("review_status", sa.String(20), nullable=False,
                  server_default=sa.text("'PENDING'")),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", _UUID, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("alignment IN ('ALIGNED','PARTIAL','MISALIGNED','ABSTAINED')",
                           name="chk_integrity_question_audit_alignment"),
        sa.CheckConstraint("review_status IN ('PENDING','ACCEPTED','OVERRIDDEN')",
                           name="chk_integrity_question_audit_review_status"),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
                           name="chk_integrity_question_audit_confidence"),
        sa.CheckConstraint("review_status <> 'OVERRIDDEN' OR override_reason IS NOT NULL",
                           name="chk_integrity_question_audit_override_reason"),
        schema="integrity",
    )
    op.create_index("ix_integrity_question_audits_organization_id", "question_audits",
                    ["organization_id"], schema="integrity")
    op.create_index("ix_integrity_question_audits_question_id", "question_audits",
                    ["question_id"], schema="integrity")
    op.create_index("uq_integrity_question_audit_current", "question_audits", ["question_id"],
                    unique=True, postgresql_where=sa.text("is_current"), schema="integrity")

    # ── Permissions ───────────────────────────────────────────────────────────
    for code, description in _PERMISSIONS:
        op.execute(
            sa.text(
                """
                INSERT INTO iam.permissions (code, description, tier, module)
                VALUES (:code, :description, 'SYSTEM', 'integrity')
                ON CONFLICT (code) DO NOTHING
                """
            ).bindparams(code=code, description=description)
        )

    # Every staff role works with its own questions; students get nothing.
    op.execute(
        """
        INSERT INTO iam.role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM iam.roles r
        JOIN iam.permissions p ON p.code IN ('integrity.read', 'integrity.manage')
        WHERE r.name IN ('Super Admin', 'Program Coordinator', 'Module Leader', 'Section Teacher')
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM iam.role_permissions rp
        USING iam.permissions p
        WHERE rp.permission_id = p.id
          AND p.code IN ('integrity.read', 'integrity.manage')
        """
    )
    op.execute("DELETE FROM iam.permissions WHERE code IN ('integrity.read', 'integrity.manage')")
    op.drop_table("question_audits", schema="integrity")
    op.drop_table("question_papers", schema="integrity")
    op.execute("DROP SCHEMA IF EXISTS integrity")
    op.drop_index("ix_assessment_marksheet_questions_declared_bloom_level_id",
                  table_name="marksheet_questions", schema="assessment")
    op.drop_column("marksheet_questions", "declared_bloom_level_id", schema="assessment")
    op.drop_column("marksheet_questions", "question_text", schema="assessment")
