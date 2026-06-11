"""Rename course_types to course_categories and add courses.course_type

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COURSE_TYPE_VALUES = ("THEORY", "LAB", "THEORY_LAB", "THESIS_DEFENSE")


def upgrade() -> None:
    # ── Rename config.course_types -> config.course_categories ────────────────
    op.rename_table("course_types", "course_categories", schema="config")
    op.execute(
        "ALTER INDEX config.ix_config_course_types_organization_id "
        "RENAME TO ix_config_course_categories_organization_id"
    )
    op.execute(
        "ALTER TABLE config.course_categories "
        "RENAME CONSTRAINT uq_config_course_type_org_name "
        "TO uq_config_course_category_org_name"
    )

    # ── Rename curriculum.courses.course_type_id -> course_category_id ────────
    op.alter_column(
        "courses",
        "course_type_id",
        new_column_name="course_category_id",
        schema="curriculum",
    )

    # ── Add new fixed-vocabulary curriculum.courses.course_type ────────────────
    op.add_column(
        "courses",
        sa.Column("course_type", sa.String(20), nullable=True),
        schema="curriculum",
    )
    op.execute(
        """
        UPDATE curriculum.courses SET course_type = CASE
            WHEN lab_hours > 0 AND theory_hours > 0 THEN 'THEORY_LAB'
            WHEN lab_hours > 0 AND theory_hours = 0 THEN 'LAB'
            ELSE 'THEORY'
        END
        """
    )
    op.alter_column("courses", "course_type", nullable=False, schema="curriculum")
    op.create_check_constraint(
        "ck_curriculum_course_type_valid",
        "courses",
        sa.column("course_type").in_(_COURSE_TYPE_VALUES),
        schema="curriculum",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_curriculum_course_type_valid", "courses", schema="curriculum", type_="check"
    )
    op.drop_column("courses", "course_type", schema="curriculum")

    op.alter_column(
        "courses",
        "course_category_id",
        new_column_name="course_type_id",
        schema="curriculum",
    )

    op.execute(
        "ALTER TABLE config.course_categories "
        "RENAME CONSTRAINT uq_config_course_category_org_name "
        "TO uq_config_course_type_org_name"
    )
    op.execute(
        "ALTER INDEX config.ix_config_course_categories_organization_id "
        "RENAME TO ix_config_course_types_organization_id"
    )
    op.rename_table("course_categories", "course_types", schema="config")
