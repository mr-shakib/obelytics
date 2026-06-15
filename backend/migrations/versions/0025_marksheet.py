"""Create assessment.marksheet_questions + assessment.marksheet_marks

Revision ID: 0025
Revises: 0024
Create Date: 2026-06-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marksheet_questions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("section_offering_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.section_offerings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("exam_type", sa.String(10), nullable=False),
        sa.Column("label", sa.String(50), nullable=False),
        sa.Column("max_marks", sa.Numeric(6, 2), nullable=False),
        sa.Column("course_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("exam_type IN ('MID', 'FINAL')", name="ck_assessment_marksheet_question_exam_type"),
        sa.UniqueConstraint("section_offering_id", "exam_type", "order_index", name="uq_assessment_marksheet_question_order"),
        schema="assessment",
    )
    op.create_index(
        "ix_assessment_marksheet_questions_organization_id",
        "marksheet_questions",
        ["organization_id"],
        schema="assessment",
    )
    op.create_index(
        "ix_assessment_marksheet_questions_section_offering_id",
        "marksheet_questions",
        ["section_offering_id"],
        schema="assessment",
    )
    op.create_index(
        "ix_assessment_marksheet_questions_course_outcome_id",
        "marksheet_questions",
        ["course_outcome_id"],
        schema="assessment",
    )

    op.create_table(
        "marksheet_marks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("question_id", UUID(as_uuid=True), sa.ForeignKey("assessment.marksheet_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_enrollment_id", UUID(as_uuid=True), sa.ForeignKey("assessment.student_enrollments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("marks_obtained", sa.Numeric(6, 2), nullable=True),
        sa.Column("is_absent", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("entered_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "(is_absent = TRUE AND marks_obtained IS NULL) OR (is_absent = FALSE AND marks_obtained IS NOT NULL)",
            name="ck_assessment_marksheet_mark_absent_or_marks",
        ),
        sa.UniqueConstraint("question_id", "student_enrollment_id", name="uq_assessment_marksheet_mark"),
        schema="assessment",
    )
    op.create_index(
        "ix_assessment_marksheet_marks_question_id",
        "marksheet_marks",
        ["question_id"],
        schema="assessment",
    )
    op.create_index(
        "ix_assessment_marksheet_marks_student_enrollment_id",
        "marksheet_marks",
        ["student_enrollment_id"],
        schema="assessment",
    )


def downgrade() -> None:
    op.drop_index("ix_assessment_marksheet_marks_student_enrollment_id", table_name="marksheet_marks", schema="assessment")
    op.drop_index("ix_assessment_marksheet_marks_question_id", table_name="marksheet_marks", schema="assessment")
    op.drop_table("marksheet_marks", schema="assessment")

    op.drop_index("ix_assessment_marksheet_questions_course_outcome_id", table_name="marksheet_questions", schema="assessment")
    op.drop_index("ix_assessment_marksheet_questions_section_offering_id", table_name="marksheet_questions", schema="assessment")
    op.drop_index("ix_assessment_marksheet_questions_organization_id", table_name="marksheet_questions", schema="assessment")
    op.drop_table("marksheet_questions", schema="assessment")
