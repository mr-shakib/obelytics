"""add students_above_threshold and total_students to po_attainment_results

Revision ID: 0035
Revises: 0034
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "po_attainment_results",
        sa.Column(
            "students_above_threshold",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        schema="attainment",
    )
    op.add_column(
        "po_attainment_results",
        sa.Column(
            "total_students",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        schema="attainment",
    )
    # Drop server defaults after backfill
    op.alter_column(
        "po_attainment_results",
        "students_above_threshold",
        schema="attainment",
        server_default=None,
    )
    op.alter_column(
        "po_attainment_results",
        "total_students",
        schema="attainment",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("po_attainment_results", "total_students", schema="attainment")
    op.drop_column("po_attainment_results", "students_above_threshold", schema="attainment")
