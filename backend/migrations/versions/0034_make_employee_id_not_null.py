"""Make employee_id NOT NULL on iam.users

Revision ID: 0034
Revises: 0033
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill any existing null employee_id with a placeholder
    op.execute(
        "UPDATE iam.users SET employee_id = 'PENDING-' || id::text WHERE employee_id IS NULL"
    )
    op.alter_column(
        "users", "employee_id",
        schema="iam",
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users", "employee_id",
        schema="iam",
        nullable=True,
    )
