"""Add program coordinator history

Revision ID: 0041_program_coordinator_history
Revises: 0040_add_department_logo
Create Date: 2026-07-12 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0041_program_coordinator_history"
down_revision: Union[str, None] = "0040_add_department_logo"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "program_coordinator_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("program_id", UUID(as_uuid=True), sa.ForeignKey("org.programs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="org",
    )
    op.create_index(
        "ix_org_program_coordinator_history_program_id",
        "program_coordinator_history",
        ["program_id"],
        schema="org",
    )
    op.create_index(
        "uq_org_program_current_coordinator",
        "program_coordinator_history",
        ["program_id"],
        unique=True,
        postgresql_where=sa.text("effective_to IS NULL"),
        schema="org",
    )


def downgrade() -> None:
    op.drop_table("program_coordinator_history", schema="org")
