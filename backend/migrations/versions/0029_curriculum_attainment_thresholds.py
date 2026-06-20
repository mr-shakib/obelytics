"""Add per-curriculum attainment thresholds

Revision ID: 0029
Revises: 0028
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0029"
down_revision: Union[str, None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "curricula",
        sa.Column("threshold_co_score_pct", sa.Numeric(5, 2), nullable=False, server_default=sa.text("50.00")),
        schema="curriculum",
    )
    op.add_column(
        "curricula",
        sa.Column("threshold_student_pct", sa.Numeric(5, 2), nullable=False, server_default=sa.text("50.00")),
        schema="curriculum",
    )


def downgrade() -> None:
    op.drop_column("curricula", "threshold_student_pct", schema="curriculum")
    op.drop_column("curricula", "threshold_co_score_pct", schema="curriculum")
