"""Create attainment schema tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS attainment")

    # ── attainment.attainment_configs ─────────────────────────────────────────
    op.create_table(
        "attainment_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("program_id", UUID(as_uuid=True), sa.ForeignKey("org.programs.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("threshold_student_pct", sa.Numeric(5, 2), nullable=False, server_default=sa.text("50.00")),
        sa.Column("threshold_co_score_pct", sa.Numeric(5, 2), nullable=False, server_default=sa.text("50.00")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "program_id", name="uq_attainment_config_org_program"),
        schema="attainment",
    )
    op.create_index("ix_attainment_configs_organization_id", "attainment_configs", ["organization_id"], schema="attainment")
    op.create_index("ix_attainment_configs_program_id", "attainment_configs", ["program_id"], schema="attainment")
    op.create_index(
        "uq_attainment_config_org_default",
        "attainment_configs",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("program_id IS NULL"),
        schema="attainment",
    )

    # ── attainment.co_attainment_results ──────────────────────────────────────
    op.create_table(
        "co_attainment_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("section_offering_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.section_offerings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("average_attainment_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("students_above_threshold", sa.Integer(), nullable=False),
        sa.Column("total_students", sa.Integer(), nullable=False),
        sa.Column("is_attained", sa.Boolean(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("section_offering_id", "course_outcome_id", name="uq_attainment_co_result_offering_co"),
        schema="attainment",
    )
    op.create_index("ix_attainment_co_attainment_results_section_offering_id", "co_attainment_results", ["section_offering_id"], schema="attainment")
    op.create_index("ix_attainment_co_attainment_results_course_outcome_id", "co_attainment_results", ["course_outcome_id"], schema="attainment")

    # ── attainment.po_attainment_results ──────────────────────────────────────
    op.create_table(
        "po_attainment_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("section_offering_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.section_offerings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("program_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.program_outcomes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("attainment_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("contributing_co_count", sa.Integer(), nullable=False),
        sa.Column("is_attained", sa.Boolean(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("section_offering_id", "program_outcome_id", name="uq_attainment_po_result_offering_po"),
        schema="attainment",
    )
    op.create_index("ix_attainment_po_attainment_results_section_offering_id", "po_attainment_results", ["section_offering_id"], schema="attainment")
    op.create_index("ix_attainment_po_attainment_results_program_outcome_id", "po_attainment_results", ["program_outcome_id"], schema="attainment")


def downgrade() -> None:
    op.drop_table("po_attainment_results", schema="attainment")
    op.drop_table("co_attainment_results", schema="attainment")
    op.drop_table("attainment_configs", schema="attainment")
    op.execute("DROP SCHEMA IF EXISTS attainment CASCADE")
