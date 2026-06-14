"""Create curriculum.course_learning_materials

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_learning_materials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_type", sa.String(20), nullable=False),
        sa.Column("order_index", sa.SmallInteger(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("authors", sa.String(500), nullable=True),
        sa.Column("publisher", sa.String(255), nullable=True),
        sa.Column("edition_year", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "material_type IN ('TEXTBOOK', 'REFERENCE')",
            name="ck_curriculum_course_learning_material_type",
        ),
        schema="curriculum",
    )
    op.create_index(
        "ix_curriculum_course_learning_materials_course_id",
        "course_learning_materials",
        ["course_id"],
        schema="curriculum",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curriculum_course_learning_materials_course_id",
        table_name="course_learning_materials",
        schema="curriculum",
    )
    op.drop_table("course_learning_materials", schema="curriculum")
