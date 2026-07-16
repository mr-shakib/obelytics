"""Add justification field to CO-CA mapping table

Revision ID: 0051_add_co_ca_justification
Revises: 0050_copilot_conversations
Create Date: 2026-07-16 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0051_add_co_ca_justification"
down_revision: Union[str, None] = "0050_copilot_conversations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "co_ca_mappings",
        sa.Column("justification", sa.Text(), nullable=False, server_default="Justification pending."),
        schema="obe",
    )


def downgrade() -> None:
    op.drop_column("co_ca_mappings", "justification", schema="obe")
