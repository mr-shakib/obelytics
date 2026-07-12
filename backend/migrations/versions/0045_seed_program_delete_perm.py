"""Seed program.delete permission, granted to Super Admin only

Revision ID: 0045_seed_program_delete_perm
Revises: 0044_po_code_unique_by_program
Create Date: 2026-07-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0045_seed_program_delete_perm"
down_revision: Union[str, None] = "0044_po_code_unique_by_program"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO iam.permissions (code, description, tier, module)
        VALUES ('program.delete', 'Permanently delete a program', 'SYSTEM', 'org')
        ON CONFLICT (code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO iam.role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM iam.roles r
        JOIN iam.permissions p ON p.code = 'program.delete'
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
          AND p.code = 'program.delete'
        """
    )
    op.execute(
        """
        DELETE FROM iam.permissions
        WHERE code = 'program.delete'
        """
    )
