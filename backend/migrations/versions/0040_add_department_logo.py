"""Add logo field to departments

Revision ID: 0040_add_department_logo
Revises: 0039_add_mapping_justifications
Create Date: 2026-06-30 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0040_add_department_logo"
down_revision: Union[str, None] = "0039_add_mapping_justifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "departments",
        sa.Column("logo_file_key", sa.String(length=500), nullable=True),
        schema="org",
    )


def downgrade() -> None:
    op.drop_column("departments", "logo_file_key", schema="org")
