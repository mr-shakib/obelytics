import sqlalchemy as sa
from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey,
    Index, Numeric, String, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        Index(
            "uq_assessment_student_sid_active",
            "organization_id", "student_id_number",
            unique=True,
            postgresql_where=sa.text("status != 'WITHDRAWN'"),
        ),
        {"schema": "assessment"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id_number = Column(String(50), nullable=False)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    program_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.programs.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    batch_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.batches.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status = Column(String(20), nullable=False, server_default="ACTIVE")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class StudentEnrollment(Base):
    __tablename__ = "student_enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "section_offering_id", name="uq_assessment_enrollment_student_offering"),
        {"schema": "assessment"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    student_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("assessment.students.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    section_offering_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.section_offerings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status = Column(String(20), nullable=False, server_default="ACTIVE")
    enrolled_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = {"schema": "assessment"}

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    section_offering_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.section_offerings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assessment_type_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("config.assessment_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    total_marks = Column(Numeric(6, 2), nullable=False)
    weightage_percent = Column(Numeric(5, 2), nullable=False)
    status = Column(String(20), nullable=False, server_default="CONFIGURED")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class AssessmentCOWeight(Base):
    __tablename__ = "assessment_co_weights"
    __table_args__ = (
        UniqueConstraint("assessment_id", "course_outcome_id", name="uq_assessment_co_weight"),
        {"schema": "assessment"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    assessment_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("assessment.assessments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    course_outcome_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    contribution_percent = Column(Numeric(5, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class StudentMark(Base):
    __tablename__ = "student_marks"
    __table_args__ = (
        UniqueConstraint("assessment_id", "student_enrollment_id", name="uq_assessment_student_mark"),
        CheckConstraint(
            "(is_absent = TRUE AND marks_obtained IS NULL) OR (is_absent = FALSE AND marks_obtained IS NOT NULL)",
            name="ck_assessment_student_marks_absent_or_marks",
        ),
        {"schema": "assessment"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assessment_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("assessment.assessments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_enrollment_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("assessment.student_enrollments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    marks_obtained = Column(Numeric(6, 2), nullable=True)
    is_absent = Column(Boolean, nullable=False, server_default=sa.text("FALSE"))
    # Plain UUID — no FK constraint (cross-schema IAM)
    entered_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class MarksheetQuestion(Base):
    __tablename__ = "marksheet_questions"
    __table_args__ = (
        UniqueConstraint(
            "section_offering_id", "exam_type", "order_index",
            name="uq_assessment_marksheet_question_order",
        ),
        CheckConstraint("exam_type IN ('MID', 'FINAL')", name="ck_assessment_marksheet_question_exam_type"),
        {"schema": "assessment"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    section_offering_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.section_offerings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    exam_type = Column(String(10), nullable=False)
    label = Column(String(50), nullable=False)
    max_marks = Column(Numeric(6, 2), nullable=False)
    course_outcome_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    order_index = Column(sa.Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class MarksheetMark(Base):
    __tablename__ = "marksheet_marks"
    __table_args__ = (
        UniqueConstraint("question_id", "student_enrollment_id", name="uq_assessment_marksheet_mark"),
        CheckConstraint(
            "(is_absent = TRUE AND marks_obtained IS NULL) OR (is_absent = FALSE AND marks_obtained IS NOT NULL)",
            name="ck_assessment_marksheet_mark_absent_or_marks",
        ),
        {"schema": "assessment"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    question_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("assessment.marksheet_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_enrollment_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("assessment.student_enrollments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    marks_obtained = Column(Numeric(6, 2), nullable=True)
    is_absent = Column(Boolean, nullable=False, server_default=sa.text("FALSE"))
    # Plain UUID — no FK constraint (cross-schema IAM)
    entered_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class ResultPublication(Base):
    __tablename__ = "result_publications"
    __table_args__ = (
        UniqueConstraint("section_offering_id", name="uq_assessment_result_pub_offering"),
        {"schema": "assessment"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    section_offering_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.section_offerings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status = Column(String(20), nullable=False, server_default="DRAFT")
    # Plain UUIDs — no FK constraints (cross-schema IAM)
    submitted_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    ml_approved_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    ml_approved_at = Column(DateTime(timezone=True), nullable=True)
    ml_rejection_comment = Column(sa.Text, nullable=True)
    pc_approved_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    pc_approved_at = Column(DateTime(timezone=True), nullable=True)
    published_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )
