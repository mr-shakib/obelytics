"""Seed Attendance assessment type for all existing organizations

Revision ID: 0031
Revises: 0030
Create Date: 2026-06-21
"""
import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO config.assessment_types (organization_id, name, is_sessional)
        SELECT id, 'Attendance', false
        FROM org.organizations
        ON CONFLICT (organization_id, name) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM config.assessment_types
        WHERE name = 'Attendance'
        """
    )
