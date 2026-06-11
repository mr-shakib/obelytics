"""Create curriculum.module_leader_assignments

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "module_leader_assignments",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("batch_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("curriculum.batches.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("academic_term_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("curriculum.academic_terms.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("curriculum.courses.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        schema="curriculum",
    )
    op.create_index(
        "uq_curriculum_module_leader_active",
        "module_leader_assignments",
        ["batch_id", "academic_term_id", "course_id"],
        unique=True,
        schema="curriculum",
        postgresql_where=sa.text("removed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_curriculum_module_leader_active", table_name="module_leader_assignments", schema="curriculum")
    op.drop_table("module_leader_assignments", schema="curriculum")
