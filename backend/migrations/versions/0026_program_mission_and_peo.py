"""Add program_missions and program_educational_objectives tables with PEO-PO and PEO-Mission mappings

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0026"
down_revision: Union[str, None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "program_missions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("program_id", UUID(as_uuid=True), sa.ForeignKey("org.programs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("order_index", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="obe",
    )
    op.create_index("ix_obe_program_missions_organization_id", "program_missions", ["organization_id"], schema="obe")
    op.create_index("ix_obe_program_missions_program_id", "program_missions", ["program_id"], schema="obe")
    op.create_index(
        "uq_obe_mission_program_code_active",
        "program_missions",
        ["program_id", "code"],
        unique=True,
        schema="obe",
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "program_educational_objectives",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("program_id", UUID(as_uuid=True), sa.ForeignKey("org.programs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("order_index", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="obe",
    )
    op.create_index("ix_obe_peos_organization_id", "program_educational_objectives", ["organization_id"], schema="obe")
    op.create_index("ix_obe_peos_program_id", "program_educational_objectives", ["program_id"], schema="obe")
    op.create_index(
        "uq_obe_peo_program_code_active",
        "program_educational_objectives",
        ["program_id", "code"],
        unique=True,
        schema="obe",
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "peo_po_mappings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("peo_id", UUID(as_uuid=True), sa.ForeignKey("obe.program_educational_objectives.id", ondelete="CASCADE"), nullable=False),
        sa.Column("program_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.program_outcomes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("peo_id", "program_outcome_id", name="uq_obe_peo_po"),
        schema="obe",
    )
    op.create_index("ix_obe_peo_po_mappings_peo_id", "peo_po_mappings", ["peo_id"], schema="obe")

    op.create_table(
        "peo_mission_mappings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("peo_id", UUID(as_uuid=True), sa.ForeignKey("obe.program_educational_objectives.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mission_id", UUID(as_uuid=True), sa.ForeignKey("obe.program_missions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("peo_id", "mission_id", name="uq_obe_peo_mission"),
        schema="obe",
    )
    op.create_index("ix_obe_peo_mission_mappings_peo_id", "peo_mission_mappings", ["peo_id"], schema="obe")


def downgrade() -> None:
    op.drop_table("peo_mission_mappings", schema="obe")
    op.drop_table("peo_po_mappings", schema="obe")
    op.drop_index("uq_obe_peo_program_code_active", table_name="program_educational_objectives", schema="obe")
    op.drop_index("ix_obe_peos_program_id", table_name="program_educational_objectives", schema="obe")
    op.drop_index("ix_obe_peos_organization_id", table_name="program_educational_objectives", schema="obe")
    op.drop_table("program_educational_objectives", schema="obe")
    op.drop_index("uq_obe_mission_program_code_active", table_name="program_missions", schema="obe")
    op.drop_index("ix_obe_program_missions_program_id", table_name="program_missions", schema="obe")
    op.drop_index("ix_obe_program_missions_organization_id", table_name="program_missions", schema="obe")
    op.drop_table("program_missions", schema="obe")
