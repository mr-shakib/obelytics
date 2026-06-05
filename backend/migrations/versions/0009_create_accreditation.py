"""Create accreditation schema tables and ensure reporting schema exists

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as pg

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS accreditation")
    op.execute("CREATE SCHEMA IF NOT EXISTS reporting")

    # ── accreditation.accreditation_cycles ────────────────────────────────────
    op.create_table(
        "accreditation_cycles",
        sa.Column("id", pg(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "organization_id",
            pg(as_uuid=True),
            sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "program_id",
            pg(as_uuid=True),
            sa.ForeignKey("org.programs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("accreditation_body", sa.String(50), nullable=False),
        sa.Column("cycle_start_year", sa.SmallInteger, nullable=False),
        sa.Column("cycle_end_year", sa.SmallInteger, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'DRAFT'")),
        sa.Column("created_by_user_id", pg(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="accreditation",
    )
    op.create_index(
        "ix_accreditation_cycle_org",
        "accreditation_cycles",
        ["organization_id"],
        schema="accreditation",
    )
    op.create_index(
        "ix_accreditation_cycle_program",
        "accreditation_cycles",
        ["program_id"],
        schema="accreditation",
    )

    # ── accreditation.accreditation_criteria ──────────────────────────────────
    op.create_table(
        "accreditation_criteria",
        sa.Column("id", pg(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "cycle_id",
            pg(as_uuid=True),
            sa.ForeignKey("accreditation.accreditation_cycles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("order_index", sa.SmallInteger, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("cycle_id", "code", name="uq_accreditation_criterion_cycle_code"),
        schema="accreditation",
    )
    op.create_index(
        "ix_accreditation_criterion_cycle",
        "accreditation_criteria",
        ["cycle_id"],
        schema="accreditation",
    )

    # ── accreditation.criterion_po_mappings ───────────────────────────────────
    op.create_table(
        "criterion_po_mappings",
        sa.Column("id", pg(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "criterion_id",
            pg(as_uuid=True),
            sa.ForeignKey("accreditation.accreditation_criteria.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "program_outcome_id",
            pg(as_uuid=True),
            sa.ForeignKey("obe.program_outcomes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("criterion_id", "program_outcome_id", name="uq_accreditation_criterion_po"),
        schema="accreditation",
    )
    op.create_index(
        "ix_accreditation_criterion_po_criterion",
        "criterion_po_mappings",
        ["criterion_id"],
        schema="accreditation",
    )
    op.create_index(
        "ix_accreditation_criterion_po_po",
        "criterion_po_mappings",
        ["program_outcome_id"],
        schema="accreditation",
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS accreditation CASCADE")
    # Don't drop reporting in downgrade (no tables to drop)
