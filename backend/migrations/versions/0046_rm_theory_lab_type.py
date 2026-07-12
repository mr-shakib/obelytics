"""Remove THEORY_LAB course type — courses are now strictly THEORY or LAB

Revision ID: 0046_rm_theory_lab_type
Revises: 0045_seed_program_delete_perm
Create Date: 2026-07-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0046_rm_theory_lab_type"
down_revision: Union[str, None] = "0045_seed_program_delete_perm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Any existing THEORY_LAB course becomes THEORY — callers are expected to
    # split out a paired LAB/sessional course where the lab component matters.
    op.execute("UPDATE curriculum.courses SET course_type = 'THEORY' WHERE course_type = 'THEORY_LAB'")
    op.drop_constraint("ck_curriculum_course_type_valid", "courses", schema="curriculum", type_="check")
    op.create_check_constraint(
        "ck_curriculum_course_type_valid",
        "courses",
        "course_type IN ('THEORY', 'LAB', 'THESIS_DEFENSE')",
        schema="curriculum",
    )


def downgrade() -> None:
    op.drop_constraint("ck_curriculum_course_type_valid", "courses", schema="curriculum", type_="check")
    op.create_check_constraint(
        "ck_curriculum_course_type_valid",
        "courses",
        "course_type IN ('THEORY', 'LAB', 'THEORY_LAB', 'THESIS_DEFENSE')",
        schema="curriculum",
    )
