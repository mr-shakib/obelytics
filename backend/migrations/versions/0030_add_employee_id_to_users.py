"""Add employee_id to iam.users

Revision ID: 0030
Revises: 0029
Create Date: 2026-06-21
"""
import sqlalchemy as sa
from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("employee_id", sa.String(100), nullable=True),
        schema="iam",
    )


def downgrade() -> None:
    op.drop_column("users", "employee_id", schema="iam")
