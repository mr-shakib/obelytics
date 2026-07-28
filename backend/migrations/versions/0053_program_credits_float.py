"""Allow fractional program total credits (e.g. 136.5) — was whole-number only

Revision ID: 0053_program_credits_float
Revises: 0052_remove_co_workflow
Create Date: 2026-07-28 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0053_program_credits_float"
down_revision: Union[str, None] = "0052_remove_co_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "programs", "total_credits",
        existing_type=sa.SmallInteger(),
        type_=sa.Float(),
        existing_nullable=False,
        schema="org",
    )


def downgrade() -> None:
    # Rounds any fractional credits to the nearest whole number.
    op.alter_column(
        "programs", "total_credits",
        existing_type=sa.Float(),
        type_=sa.SmallInteger(),
        existing_nullable=False,
        postgresql_using="round(total_credits)::smallint",
        schema="org",
    )
