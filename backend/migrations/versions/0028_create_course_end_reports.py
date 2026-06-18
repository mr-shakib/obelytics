"""Create course_end_reports table

Revision ID: 0028
Revises: 0027
Create Date: 2026-06-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0028"
down_revision: Union[str, None] = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_end_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("section_offering_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.section_offerings.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("grade_distribution", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("co_attainment", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("unattained_co_explanations", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("teacher_feedback", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("section_offering_id", name="uq_end_report_offering"),
        sa.CheckConstraint("status IN ('DRAFT', 'SUBMITTED')", name="ck_end_report_status"),
        schema="assessment",
    )
    op.create_index("ix_end_report_org", "course_end_reports", ["organization_id"], schema="assessment")
    op.create_index("ix_end_report_offering", "course_end_reports", ["section_offering_id"], schema="assessment")


def downgrade() -> None:
    op.drop_table("course_end_reports", schema="assessment")
