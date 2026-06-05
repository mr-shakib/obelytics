"""Create assessment schema tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── assessment.students ───────────────────────────────────────────────────
    op.create_table(
        "students",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("student_id_number", sa.String(50), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("program_id", UUID(as_uuid=True), sa.ForeignKey("org.programs.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("batch_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.batches.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="assessment",
    )
    op.create_index("ix_assessment_students_organization_id", "students", ["organization_id"], schema="assessment")
    op.create_index("ix_assessment_students_program_id", "students", ["program_id"], schema="assessment")
    op.create_index(
        "uq_assessment_student_sid_active",
        "students",
        ["organization_id", "student_id_number"],
        unique=True,
        postgresql_where=sa.text("status != 'WITHDRAWN'"),
        schema="assessment",
    )

    # ── assessment.student_enrollments ────────────────────────────────────────
    op.create_table(
        "student_enrollments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("student_id", UUID(as_uuid=True), sa.ForeignKey("assessment.students.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("section_offering_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.section_offerings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("student_id", "section_offering_id", name="uq_assessment_enrollment_student_offering"),
        schema="assessment",
    )
    op.create_index("ix_assessment_student_enrollments_student_id", "student_enrollments", ["student_id"], schema="assessment")
    op.create_index("ix_assessment_student_enrollments_section_offering_id", "student_enrollments", ["section_offering_id"], schema="assessment")

    # ── assessment.assessments ────────────────────────────────────────────────
    op.create_table(
        "assessments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("section_offering_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.section_offerings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assessment_type_id", UUID(as_uuid=True), sa.ForeignKey("config.assessment_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("total_marks", sa.Numeric(6, 2), nullable=False),
        sa.Column("weightage_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="CONFIGURED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="assessment",
    )
    op.create_index("ix_assessment_assessments_organization_id", "assessments", ["organization_id"], schema="assessment")
    op.create_index("ix_assessment_assessments_section_offering_id", "assessments", ["section_offering_id"], schema="assessment")

    # ── assessment.assessment_co_weights ──────────────────────────────────────
    op.create_table(
        "assessment_co_weights",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("assessment_id", UUID(as_uuid=True), sa.ForeignKey("assessment.assessments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("contribution_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("assessment_id", "course_outcome_id", name="uq_assessment_co_weight"),
        schema="assessment",
    )
    op.create_index("ix_assessment_assessment_co_weights_assessment_id", "assessment_co_weights", ["assessment_id"], schema="assessment")
    op.create_index("ix_assessment_assessment_co_weights_course_outcome_id", "assessment_co_weights", ["course_outcome_id"], schema="assessment")

    # ── assessment.student_marks ──────────────────────────────────────────────
    op.create_table(
        "student_marks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assessment_id", UUID(as_uuid=True), sa.ForeignKey("assessment.assessments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("student_enrollment_id", UUID(as_uuid=True), sa.ForeignKey("assessment.student_enrollments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("marks_obtained", sa.Numeric(6, 2), nullable=True),
        sa.Column("is_absent", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("entered_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("assessment_id", "student_enrollment_id", name="uq_assessment_student_mark"),
        sa.CheckConstraint(
            "(is_absent = TRUE AND marks_obtained IS NULL) OR (is_absent = FALSE AND marks_obtained IS NOT NULL)",
            name="ck_assessment_student_marks_absent_or_marks",
        ),
        schema="assessment",
    )
    op.create_index("ix_assessment_student_marks_assessment_id", "student_marks", ["assessment_id"], schema="assessment")
    op.create_index("ix_assessment_student_marks_student_enrollment_id", "student_marks", ["student_enrollment_id"], schema="assessment")

    # ── assessment.result_publications ───────────────────────────────────────
    op.create_table(
        "result_publications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("section_offering_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.section_offerings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("submitted_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ml_approved_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("ml_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ml_rejection_comment", sa.Text(), nullable=True),
        sa.Column("pc_approved_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("pc_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("section_offering_id", name="uq_assessment_result_pub_offering"),
        schema="assessment",
    )
    op.create_index("ix_assessment_result_publications_section_offering_id", "result_publications", ["section_offering_id"], schema="assessment")


def downgrade() -> None:
    op.drop_table("result_publications", schema="assessment")
    op.drop_table("student_marks", schema="assessment")
    op.drop_table("assessment_co_weights", schema="assessment")
    op.drop_table("assessments", schema="assessment")
    op.drop_table("student_enrollments", schema="assessment")
    op.drop_table("students", schema="assessment")
