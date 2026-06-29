"""Add justification fields to CO mapping tables

Revision ID: 0039_add_mapping_justifications
Revises: 0038
Create Date: 2026-06-30 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0039_add_mapping_justifications"
down_revision: Union[str, None] = "0038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "co_po_mapping_entries",
        sa.Column("justification", sa.Text(), nullable=False, server_default="Justification pending."),
        schema="obe",
    )
    op.add_column(
        "co_cp_mappings",
        sa.Column("justification", sa.Text(), nullable=False, server_default="Justification pending."),
        schema="obe",
    )
    op.add_column(
        "co_kp_mappings",
        sa.Column("justification", sa.Text(), nullable=False, server_default="Justification pending."),
        schema="obe",
    )


def downgrade() -> None:
    op.drop_column("co_kp_mappings", "justification", schema="obe")
    op.drop_column("co_cp_mappings", "justification", schema="obe")
    op.drop_column("co_po_mapping_entries", "justification", schema="obe")
