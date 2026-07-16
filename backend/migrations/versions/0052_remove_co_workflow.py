"""Remove CO / CO-mapping publishing workflow (status columns)

Course outcomes and their mappings no longer go through a
draft/submit/approve/publish lifecycle — a CO simply exists.

Revision ID: 0052_remove_co_workflow
Revises: 0051_add_co_ca_justification
Create Date: 2026-07-16 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0052_remove_co_workflow"
down_revision: Union[str, None] = "0051_add_co_ca_justification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_WORKFLOW_PERMISSIONS = (
    "co.submit",
    "co.approve",
    "co.reject",
    "co.publish",
    "co.lock",
    "mapping.co_po.publish",
    "mapping.co_cp.approve",
    "mapping.co_ca.approve",
    "mapping.co_kp.approve",
)


def upgrade() -> None:
    # course_outcomes
    op.drop_index(
        "ix_obe_co_curriculum_course_status", table_name="course_outcomes", schema="obe"
    )
    op.create_index(
        "ix_obe_co_curriculum_course",
        "course_outcomes",
        ["curriculum_id", "course_id"],
        schema="obe",
    )
    op.drop_column("course_outcomes", "status", schema="obe")
    op.drop_column("course_outcomes", "locked_at", schema="obe")

    # co_po_mapping_sets
    op.drop_column("co_po_mapping_sets", "status", schema="obe")
    op.drop_column("co_po_mapping_sets", "published_at", schema="obe")

    # co_cp / co_ca / co_kp mappings
    for table in ("co_cp_mappings", "co_ca_mappings", "co_kp_mappings"):
        op.drop_column(table, "status", schema="obe")
        op.drop_column(table, "approved_by_user_id", schema="obe")
        op.drop_column(table, "approved_at", schema="obe")

    # Remove now-unused workflow permissions (and their role grants)
    conn = op.get_bind()
    perms = ", ".join(f"'{p}'" for p in _WORKFLOW_PERMISSIONS)
    conn.execute(
        sa.text(
            f"DELETE FROM iam.role_permissions WHERE permission_id IN "
            f"(SELECT id FROM iam.permissions WHERE code IN ({perms}))"
        )
    )
    conn.execute(sa.text(f"DELETE FROM iam.permissions WHERE code IN ({perms})"))


def downgrade() -> None:
    for table in ("co_kp_mappings", "co_ca_mappings", "co_cp_mappings"):
        op.add_column(
            table,
            sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
            schema="obe",
        )
        op.add_column(
            table,
            sa.Column("approved_by_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
            schema="obe",
        )
        op.add_column(
            table,
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            schema="obe",
        )

    op.add_column(
        "co_po_mapping_sets",
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        schema="obe",
    )
    op.add_column(
        "co_po_mapping_sets",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        schema="obe",
    )

    op.add_column(
        "course_outcomes",
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        schema="obe",
    )
    op.add_column(
        "course_outcomes",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        schema="obe",
    )
    op.drop_index("ix_obe_co_curriculum_course", table_name="course_outcomes", schema="obe")
    op.create_index(
        "ix_obe_co_curriculum_course_status",
        "course_outcomes",
        ["curriculum_id", "course_id", "status"],
        schema="obe",
    )
    # Deleted permission rows are not restored on downgrade.
