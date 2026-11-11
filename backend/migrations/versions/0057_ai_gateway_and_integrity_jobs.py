"""AI gateway (per-org provider choice, usage log) and integrity background jobs

Revision ID: 0057_ai_gateway_integrity_jobs
Revises: 0056_integrity_foundation
Create Date: 2026-11-11 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0057_ai_gateway_integrity_jobs"
down_revision: Union[str, None] = "0056_integrity_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UUID = sa.dialects.postgresql.UUID(as_uuid=True)
_JSONB = sa.dialects.postgresql.JSONB()


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ai")

    # ── AI gateway ────────────────────────────────────────────────────────────
    op.create_table(
        "organization_settings",
        sa.Column("organization_id", _UUID,
                  sa.ForeignKey("org.organizations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("integrity_provider", sa.String(10), nullable=True),
        sa.Column("copilot_provider", sa.String(10), nullable=True),
        sa.Column("updated_by_user_id", _UUID, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(
            "integrity_provider IS NULL OR integrity_provider IN ('local','hosted','off')",
            name="chk_ai_settings_integrity_provider",
        ),
        sa.CheckConstraint(
            "copilot_provider IS NULL OR copilot_provider IN ('local','hosted','off')",
            name="chk_ai_settings_copilot_provider",
        ),
        schema="ai",
    )
    op.create_table(
        "calls",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", _UUID,
                  sa.ForeignKey("org.organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", _UUID, nullable=True),
        sa.Column("feature", sa.String(30), nullable=False),
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(10), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("image_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("redactions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('OK','ERROR')", name="chk_ai_calls_status"),
        schema="ai",
    )
    op.create_index("ix_ai_calls_organization_created", "calls",
                    ["organization_id", "created_at"], schema="ai")

    # ── Integrity: how a paper was read; how an audit reached its confidence ──
    op.add_column("question_papers", sa.Column("extraction_method", sa.String(20), nullable=True),
                  schema="integrity")
    op.add_column("question_audits", sa.Column("raw_confidence", sa.Numeric(4, 3), nullable=True),
                  schema="integrity")
    op.add_column("question_audits", sa.Column("details", _JSONB, nullable=True), schema="integrity")

    # ── Integrity background jobs ─────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", _UUID,
                  sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("section_offering_id", _UUID,
                  sa.ForeignKey("curriculum.section_offerings.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("exam_type", sa.String(10), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'QUEUED'")),
        sa.Column("progress_done", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("progress_total", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result", _JSONB, nullable=True),
        sa.Column("created_by_user_id", _UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('READ_PAPER','AUDIT')", name="chk_integrity_job_kind"),
        sa.CheckConstraint("status IN ('QUEUED','RUNNING','DONE','FAILED')",
                           name="chk_integrity_job_status"),
        sa.CheckConstraint("exam_type IN ('MID', 'FINAL')", name="chk_integrity_job_exam_type"),
        schema="integrity",
    )
    op.create_index("ix_integrity_jobs_organization_id", "jobs", ["organization_id"],
                    schema="integrity")
    op.create_index("ix_integrity_jobs_offering_exam_created", "jobs",
                    ["section_offering_id", "exam_type", "created_at"], schema="integrity")
    # At most one active job per exam.
    op.create_index(
        "uq_integrity_job_active", "jobs", ["section_offering_id", "exam_type"],
        unique=True, schema="integrity",
        postgresql_where=sa.text("status IN ('QUEUED','RUNNING')"),
    )


def downgrade() -> None:
    op.drop_index("uq_integrity_job_active", table_name="jobs", schema="integrity")
    op.drop_index("ix_integrity_jobs_offering_exam_created", table_name="jobs", schema="integrity")
    op.drop_index("ix_integrity_jobs_organization_id", table_name="jobs", schema="integrity")
    op.drop_table("jobs", schema="integrity")
    op.drop_column("question_audits", "details", schema="integrity")
    op.drop_column("question_audits", "raw_confidence", schema="integrity")
    op.drop_column("question_papers", "extraction_method", schema="integrity")
    op.drop_index("ix_ai_calls_organization_created", table_name="calls", schema="ai")
    op.drop_table("calls", schema="ai")
    op.drop_table("organization_settings", schema="ai")
    op.execute("DROP SCHEMA IF EXISTS ai")
