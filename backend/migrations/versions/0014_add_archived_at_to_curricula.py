"""Add nullable archived_at column to curriculum.curricula

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "curricula",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        schema="curriculum",
    )


def downgrade() -> None:
    op.drop_column("curricula", "archived_at", schema="curriculum")
