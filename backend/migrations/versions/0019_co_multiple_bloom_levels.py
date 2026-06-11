"""Allow course outcomes to have multiple Bloom levels

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_outcome_bloom_levels",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("course_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.course_outcomes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bloom_level_id", UUID(as_uuid=True), sa.ForeignKey("config.bloom_levels.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("course_outcome_id", "bloom_level_id", name="uq_obe_co_bloom_level"),
        schema="obe",
    )
    op.create_index(
        "ix_obe_co_bloom_levels_course_outcome_id",
        "course_outcome_bloom_levels",
        ["course_outcome_id"],
        schema="obe",
    )

    # ── Carry forward existing single bloom_level_id values ───────────────────
    op.execute(
        """
        INSERT INTO obe.course_outcome_bloom_levels (id, course_outcome_id, bloom_level_id, created_at)
        SELECT gen_random_uuid(), id, bloom_level_id, now()
        FROM obe.course_outcomes
        WHERE bloom_level_id IS NOT NULL
        """
    )

    op.drop_column("course_outcomes", "bloom_level_id", schema="obe")


def downgrade() -> None:
    op.add_column(
        "course_outcomes",
        sa.Column("bloom_level_id", UUID(as_uuid=True), sa.ForeignKey("config.bloom_levels.id", ondelete="RESTRICT"), nullable=True),
        schema="obe",
    )

    # Lossy: a CO may now have multiple bloom levels, so pick one arbitrarily.
    op.execute(
        """
        UPDATE obe.course_outcomes co
        SET bloom_level_id = sub.bloom_level_id
        FROM (
            SELECT DISTINCT ON (course_outcome_id) course_outcome_id, bloom_level_id
            FROM obe.course_outcome_bloom_levels
            ORDER BY course_outcome_id, created_at
        ) sub
        WHERE co.id = sub.course_outcome_id
        """
    )

    op.drop_index("ix_obe_co_bloom_levels_course_outcome_id", table_name="course_outcome_bloom_levels", schema="obe")
    op.drop_table("course_outcome_bloom_levels", schema="obe")
