"""Course codes unique per curriculum instead of per organization

A code can now be reused by a different course (e.g. CSE214 is Algorithms in the
2019 curriculum and OOP in the 2021 one). Uniqueness within a curriculum is
enforced by CourseSlotService when a course is placed into a curriculum.

Revision ID: 0055_course_code_per_curriculum
Revises: 0054_cqi_attainment_gaps
Create Date: 2026-09-27 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0055_course_code_per_curriculum"
down_revision: Union[str, None] = "0054_cqi_attainment_gaps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("uq_curriculum_course_org_code_active", table_name="courses", schema="curriculum")
    op.create_index(
        "ix_curriculum_courses_org_code", "courses", ["organization_id", "code"], schema="curriculum"
    )


def downgrade() -> None:
    # Fails if duplicate active codes exist; resolve them before downgrading.
    op.drop_index("ix_curriculum_courses_org_code", table_name="courses", schema="curriculum")
    op.execute(
        "CREATE UNIQUE INDEX uq_curriculum_course_org_code_active "
        "ON curriculum.courses (organization_id, code) WHERE status = 'ACTIVE'"
    )
