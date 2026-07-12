"""Scope program_outcomes code-uniqueness by program, not just org

Revision ID: 0044_po_code_unique_by_program
Revises: 0043_accreditation_cycle_fields
Create Date: 2026-07-12 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0044_po_code_unique_by_program"
down_revision: Union[str, None] = "0043_accreditation_cycle_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("uq_obe_po_org_code_active", table_name="program_outcomes", schema="obe")
    op.create_index(
        "uq_obe_po_org_program_code_active",
        "program_outcomes",
        ["organization_id", "program_id", "code"],
        unique=True,
        schema="obe",
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index("uq_obe_po_org_program_code_active", table_name="program_outcomes", schema="obe")
    op.create_index(
        "uq_obe_po_org_code_active",
        "program_outcomes",
        ["organization_id", "code"],
        unique=True,
        schema="obe",
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
