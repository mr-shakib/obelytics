"""Add syllabus_content to curriculum.courses and create course_objectives

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "courses",
        sa.Column("syllabus_content", sa.Text(), nullable=True),
        schema="curriculum",
    )

    op.create_table(
        "course_objectives",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_index", sa.SmallInteger(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="curriculum",
    )
    op.create_index(
        "ix_curriculum_course_objectives_course_id",
        "course_objectives",
        ["course_id"],
        schema="curriculum",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curriculum_course_objectives_course_id",
        table_name="course_objectives",
        schema="curriculum",
    )
    op.drop_table("course_objectives", schema="curriculum")
    op.drop_column("courses", "syllabus_content", schema="curriculum")
