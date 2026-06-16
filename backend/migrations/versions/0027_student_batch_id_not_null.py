"""Make student batch_id NOT NULL

Revision ID: 0027
Revises: 0026
Create Date: 2026-06-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0027"
down_revision: Union[str, None] = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "students",
        "batch_id",
        existing_type=UUID(as_uuid=True),
        nullable=False,
        schema="assessment",
    )
    op.create_index(
        "ix_assessment_students_batch_id",
        "students",
        ["batch_id"],
        schema="assessment",
    )


def downgrade() -> None:
    op.drop_index("ix_assessment_students_batch_id", table_name="students", schema="assessment")
    op.alter_column(
        "students",
        "batch_id",
        existing_type=UUID(as_uuid=True),
        nullable=True,
        schema="assessment",
    )
