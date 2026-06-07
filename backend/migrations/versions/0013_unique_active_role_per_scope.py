"""Enforce one active role per (user, scope) via a partial unique index

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_iam_user_role_assignments_active_scope",
        "user_role_assignments",
        ["user_id", "scope_type", "scope_id"],
        unique=True,
        schema="iam",
        postgresql_where=sa.text("removed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_iam_user_role_assignments_active_scope",
        table_name="user_role_assignments",
        schema="iam",
    )
