"""Create curriculum.course_co_marks + curriculum.course_bloom_marks

Revision ID: 0024
Revises: 0023
Create Date: 2026-06-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_co_marks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("curriculum_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.curricula.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assessment_type_id", UUID(as_uuid=True), sa.ForeignKey("config.assessment_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("marks", sa.Numeric(5, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="curriculum",
    )
    op.create_index(
        "ix_curriculum_course_co_marks_curriculum_course",
        "course_co_marks",
        ["curriculum_id", "course_id"],
        schema="curriculum",
    )

    op.create_table(
        "course_bloom_marks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("curriculum_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.curricula.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assessment_type_id", UUID(as_uuid=True), sa.ForeignKey("config.assessment_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("bloom_level_id", UUID(as_uuid=True), sa.ForeignKey("config.bloom_levels.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("component", sa.String(10), nullable=False),
        sa.Column("marks", sa.Numeric(5, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("component IN ('CIE', 'SEE')", name="ck_curriculum_course_bloom_marks_component"),
        schema="curriculum",
    )
    op.create_index(
        "ix_curriculum_course_bloom_marks_curriculum_course",
        "course_bloom_marks",
        ["curriculum_id", "course_id"],
        schema="curriculum",
    )


def downgrade() -> None:
    op.drop_index("ix_curriculum_course_bloom_marks_curriculum_course", table_name="course_bloom_marks", schema="curriculum")
    op.drop_table("course_bloom_marks", schema="curriculum")

    op.drop_index("ix_curriculum_course_co_marks_curriculum_course", table_name="course_co_marks", schema="curriculum")
    op.drop_table("course_co_marks", schema="curriculum")
