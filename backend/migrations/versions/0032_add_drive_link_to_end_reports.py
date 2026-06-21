"""Add course_drive_link to course_end_reports

Revision ID: 0032
Revises: 0031
Create Date: 2026-06-21
"""
import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "course_end_reports",
        sa.Column("course_drive_link", sa.String(500), nullable=True),
        schema="assessment",
    )


def downgrade() -> None:
    op.drop_column("course_end_reports", "course_drive_link", schema="assessment")
