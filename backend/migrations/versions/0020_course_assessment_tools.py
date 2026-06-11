"""Add curriculum.course_assessment_tools and seed 'Lab Final' assessment type

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Seed "Lab Final" assessment type for every existing org ────────────────
    op.execute(
        """
        INSERT INTO config.assessment_types (id, organization_id, name, is_sessional, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), o.id, 'Lab Final', true, true, now(), now()
        FROM org.organizations o
        WHERE NOT EXISTS (
            SELECT 1 FROM config.assessment_types at
            WHERE at.organization_id = o.id AND at.name = 'Lab Final'
        )
        """
    )

    # ── curriculum.course_assessment_tools ──────────────────────────────────────
    op.create_table(
        "course_assessment_tools",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("curriculum_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.curricula.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assessment_type_id", UUID(as_uuid=True), sa.ForeignKey("config.assessment_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("curriculum_id", "course_id", "assessment_type_id", name="uq_curriculum_course_assessment_tool"),
        schema="curriculum",
    )
    op.create_index(
        "ix_curriculum_course_assessment_tools_curriculum_course",
        "course_assessment_tools",
        ["curriculum_id", "course_id"],
        schema="curriculum",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curriculum_course_assessment_tools_curriculum_course",
        table_name="course_assessment_tools",
        schema="curriculum",
    )
    op.drop_table("course_assessment_tools", schema="curriculum")

    # Note: the seeded "Lab Final" assessment type is intentionally left in
    # place — it may already be referenced elsewhere (e.g. assessments).
