"""add po_versions table and po_version_id to program_outcomes and programs

Revision ID: 0036
Revises: 0035
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "po_versions",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", PGUUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "name", name="uq_obe_po_version_org_name"),
        schema="obe",
    )

    op.add_column(
        "program_outcomes",
        sa.Column("po_version_id", PGUUID(as_uuid=True), sa.ForeignKey("obe.po_versions.id", ondelete="RESTRICT"), nullable=True, index=True),
        schema="obe",
    )

    op.add_column(
        "programs",
        sa.Column("po_version_id", PGUUID(as_uuid=True), nullable=True, index=True),
        schema="org",
    )


def downgrade() -> None:
    op.drop_column("programs", "po_version_id", schema="org")
    op.drop_column("program_outcomes", "po_version_id", schema="obe")
    op.drop_table("po_versions", schema="obe")
