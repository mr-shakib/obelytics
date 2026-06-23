"""make po program_id nullable and update unique index

Revision ID: 0033
Revises: 0032
Create Date: 2026-06-23
"""
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old per-program unique index
    op.drop_index(
        "uq_obe_po_program_code_active",
        table_name="program_outcomes",
        schema="obe",
    )
    # Make program_id nullable
    op.alter_column(
        "program_outcomes", "program_id",
        schema="obe",
        nullable=True,
    )
    # Create new org-wide unique index
    op.create_index(
        "uq_obe_po_org_code_active",
        "program_outcomes",
        ["organization_id", "code"],
        unique=True,
        schema="obe",
        postgresql_where="status = 'ACTIVE'",
    )


def downgrade() -> None:
    op.drop_index(
        "uq_obe_po_org_code_active",
        table_name="program_outcomes",
        schema="obe",
    )
    op.alter_column(
        "program_outcomes", "program_id",
        schema="obe",
        nullable=False,
    )
    op.create_index(
        "uq_obe_po_program_code_active",
        "program_outcomes",
        ["program_id", "code"],
        unique=True,
        schema="obe",
        postgresql_where="status = 'ACTIVE'",
    )
