"""Seed program.read permission and grant it to program-facing roles

Revision ID: 0037
Revises: 0036
Create Date: 2026-06-25
"""

from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO iam.permissions (code, description, tier, module)
        VALUES ('program.read', 'Read programs', 'SYSTEM', 'org')
        ON CONFLICT (code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO iam.role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM iam.roles r
        JOIN iam.permissions p ON p.code = 'program.read'
        WHERE r.name IN ('Program Coordinator', 'Module Leader', 'Section Teacher')
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM iam.role_permissions rp
        USING iam.permissions p
        WHERE rp.permission_id = p.id
          AND p.code = 'program.read'
        """
    )
    op.execute(
        """
        DELETE FROM iam.permissions
        WHERE code = 'program.read'
        """
    )
