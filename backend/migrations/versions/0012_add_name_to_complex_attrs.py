"""Add nullable name column to config.complex_problems and config.complex_activities

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("complex_problems", sa.Column("name", sa.String(150), nullable=True), schema="config")
    op.add_column("complex_activities", sa.Column("name", sa.String(150), nullable=True), schema="config")


def downgrade() -> None:
    op.drop_column("complex_activities", "name", schema="config")
    op.drop_column("complex_problems", "name", schema="config")
