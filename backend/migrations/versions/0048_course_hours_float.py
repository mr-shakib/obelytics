"""Allow fractional course theory/lab hours (e.g. 1.5) — was whole-number only

Revision ID: 0048_course_hours_float
Revises: 0047_course_credits_float
Create Date: 2026-07-14 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0048_course_hours_float"
down_revision: Union[str, None] = "0047_course_credits_float"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "courses", "theory_hours",
        existing_type=sa.SmallInteger(),
        type_=sa.Float(),
        schema="curriculum",
    )
    op.alter_column(
        "courses", "lab_hours",
        existing_type=sa.SmallInteger(),
        type_=sa.Float(),
        schema="curriculum",
    )


def downgrade() -> None:
    op.alter_column(
        "courses", "theory_hours",
        existing_type=sa.Float(),
        type_=sa.SmallInteger(),
        schema="curriculum",
    )
    op.alter_column(
        "courses", "lab_hours",
        existing_type=sa.Float(),
        type_=sa.SmallInteger(),
        schema="curriculum",
    )
