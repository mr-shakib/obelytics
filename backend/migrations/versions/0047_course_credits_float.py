"""Allow fractional course credits (e.g. 1.5, 0.75) — was whole-number only

Revision ID: 0047_course_credits_float
Revises: 0046_rm_theory_lab_type
Create Date: 2026-07-14 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0047_course_credits_float"
down_revision: Union[str, None] = "0046_rm_theory_lab_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "courses", "credits",
        existing_type=sa.SmallInteger(),
        type_=sa.Float(),
        schema="curriculum",
    )


def downgrade() -> None:
    op.alter_column(
        "courses", "credits",
        existing_type=sa.Float(),
        type_=sa.SmallInteger(),
        schema="curriculum",
    )
