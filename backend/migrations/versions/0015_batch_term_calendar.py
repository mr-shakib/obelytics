"""Add term_system/start_date/num_semesters to batches; create batch_term_calendar

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Alter curriculum.batches ──────────────────────────────────────────────
    op.alter_column("batches", "intake_year", nullable=True, schema="curriculum")
    op.add_column("batches", sa.Column("start_date", sa.Date(), nullable=True), schema="curriculum")
    op.add_column("batches", sa.Column("term_system", sa.String(20), nullable=True), schema="curriculum")
    op.add_column("batches", sa.Column("num_semesters", sa.SmallInteger(), nullable=True), schema="curriculum")

    # ── Create curriculum.batch_term_calendar ─────────────────────────────────
    op.create_table(
        "batch_term_calendar",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("batch_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("curriculum.batches.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("term_number", sa.SmallInteger(), nullable=False),
        sa.Column("academic_term_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("curriculum.academic_terms.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("batch_id", "term_number", name="uq_batch_term_calendar_batch_term"),
        schema="curriculum",
    )


def downgrade() -> None:
    op.drop_table("batch_term_calendar", schema="curriculum")
    op.drop_column("batches", "num_semesters", schema="curriculum")
    op.drop_column("batches", "term_system", schema="curriculum")
    op.drop_column("batches", "start_date", schema="curriculum")
    op.alter_column("batches", "intake_year", nullable=False, schema="curriculum")
