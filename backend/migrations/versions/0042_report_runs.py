"""Add reporting.report_runs table for async report generation

Revision ID: 0042_report_runs
Revises: 0041_program_coordinator_history
Create Date: 2026-07-12 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0042_report_runs"
down_revision: Union[str, None] = "0041_program_coordinator_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("definition_id", sa.String(length=50), nullable=False),
        sa.Column("definition_name", sa.String(length=255), nullable=False),
        sa.Column("requested_by_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("params", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("summary", JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("output_file_key", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('PENDING','RUNNING','DONE','FAILED')", name="chk_report_run_status"),
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_report_runs_org_user",
        "report_runs",
        ["organization_id", "requested_by_user_id"],
        schema="reporting",
    )


def downgrade() -> None:
    op.drop_table("report_runs", schema="reporting")
