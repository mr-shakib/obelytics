"""Create curriculum.course_lesson_plan_items + CO/PO join tables

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_lesson_plan_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("curriculum_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.curricula.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("week_number", sa.SmallInteger(), nullable=False),
        sa.Column("lesson_label", sa.String(100), nullable=True),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("tla", sa.Text(), nullable=True),
        sa.Column("assessment_strategy", sa.Text(), nullable=True),
        sa.Column("order_index", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="curriculum",
    )
    op.create_index(
        "ix_curriculum_lesson_plan_items_curriculum_course",
        "course_lesson_plan_items",
        ["curriculum_id", "course_id"],
        schema="curriculum",
    )

    op.create_table(
        "course_lesson_plan_item_cos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.course_lesson_plan_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("item_id", "course_outcome_id", name="uq_curriculum_lesson_plan_item_co"),
        schema="curriculum",
    )
    op.create_index(
        "ix_curriculum_lesson_plan_item_cos_item_id",
        "course_lesson_plan_item_cos",
        ["item_id"],
        schema="curriculum",
    )

    op.create_table(
        "course_lesson_plan_item_pos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.course_lesson_plan_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("program_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.program_outcomes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("item_id", "program_outcome_id", name="uq_curriculum_lesson_plan_item_po"),
        schema="curriculum",
    )
    op.create_index(
        "ix_curriculum_lesson_plan_item_pos_item_id",
        "course_lesson_plan_item_pos",
        ["item_id"],
        schema="curriculum",
    )


def downgrade() -> None:
    op.drop_index("ix_curriculum_lesson_plan_item_pos_item_id", table_name="course_lesson_plan_item_pos", schema="curriculum")
    op.drop_table("course_lesson_plan_item_pos", schema="curriculum")

    op.drop_index("ix_curriculum_lesson_plan_item_cos_item_id", table_name="course_lesson_plan_item_cos", schema="curriculum")
    op.drop_table("course_lesson_plan_item_cos", schema="curriculum")

    op.drop_index("ix_curriculum_lesson_plan_items_curriculum_course", table_name="course_lesson_plan_items", schema="curriculum")
    op.drop_table("course_lesson_plan_items", schema="curriculum")
