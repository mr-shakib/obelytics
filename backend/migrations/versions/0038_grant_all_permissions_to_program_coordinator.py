"""Grant all permissions to Program Coordinator

Revision ID: 0038
Revises: 0037
Create Date: 2026-06-26
"""

from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO iam.role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM iam.roles r
        CROSS JOIN iam.permissions p
        WHERE r.name = 'Program Coordinator'
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    # Permission grants may have been customized after this migration. Avoid
    # destructively guessing which Program Coordinator grants should be removed.
    pass
