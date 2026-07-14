"""Seed batch.delete permission, granted to Super Admin only

Revision ID: 0049_seed_batch_delete_perm
Revises: 0048_course_hours_float
Create Date: 2026-07-14 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0049_seed_batch_delete_perm"
down_revision: Union[str, None] = "0048_course_hours_float"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO iam.permissions (code, description, tier, module)
        VALUES ('batch.delete', 'Permanently delete a batch', 'SYSTEM', 'curriculum')
        ON CONFLICT (code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO iam.role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM iam.roles r
        JOIN iam.permissions p ON p.code = 'batch.delete'
        WHERE r.name = 'Super Admin'
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM iam.role_permissions rp
        USING iam.permissions p
        WHERE rp.permission_id = p.id
          AND p.code = 'batch.delete'
        """
    )
    op.execute(
        """
        DELETE FROM iam.permissions
        WHERE code = 'batch.delete'
        """
    )
