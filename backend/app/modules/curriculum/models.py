import sqlalchemy as sa
from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index,
    SmallInteger, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class Curriculum(Base):
    __tablename__ = "curricula"
    __table_args__ = (
        UniqueConstraint("program_id", "code", "version_number", name="uq_curriculum_program_code_version"),
        {"schema": "curriculum"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    program_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.programs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    effective_year = Column(SmallInteger, nullable=False)
    version_number = Column(SmallInteger, nullable=False, server_default=sa.text("1"))
    parent_curriculum_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.curricula.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status = Column(String(20), nullable=False, server_default="DRAFT")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class CurriculumTermDefinition(Base):
    __tablename__ = "curriculum_term_definitions"
    __table_args__ = (
        UniqueConstraint("curriculum_id", "term_number", name="uq_curriculum_term_def_curriculum_term"),
        {"schema": "curriculum"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    curriculum_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.curricula.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    term_number = Column(SmallInteger, nullable=False)
    name = Column(String(100), nullable=False)
    total_credit_hours = Column(SmallInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        Index(
            "uq_curriculum_course_org_code_active",
            "organization_id", "code",
            unique=True,
            postgresql_where=sa.text("status = 'ACTIVE'"),
        ),
        {"schema": "curriculum"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    course_type_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("config.course_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code = Column(String(30), nullable=False)
    title = Column(String(255), nullable=False)
    credits = Column(SmallInteger, nullable=False)
    theory_hours = Column(SmallInteger, nullable=False, server_default=sa.text("0"))
    lab_hours = Column(SmallInteger, nullable=False, server_default=sa.text("0"))
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, server_default="ACTIVE")
    archived_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class CurriculumCourseSlot(Base):
    __tablename__ = "curriculum_course_slots"
    __table_args__ = (
        UniqueConstraint("curriculum_id", "course_id", name="uq_curriculum_course_slot_curriculum_course"),
        {"schema": "curriculum"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    curriculum_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.curricula.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    curriculum_term_definition_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.curriculum_term_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    course_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.courses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    is_elective = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class CoursePrerequisite(Base):
    __tablename__ = "course_prerequisites"
    __table_args__ = (
        UniqueConstraint("course_id", "prerequisite_course_id", name="uq_curriculum_course_prereq"),
        CheckConstraint("course_id != prerequisite_course_id", name="ck_curriculum_prereq_no_self"),
        {"schema": "curriculum"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    course_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.courses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    prerequisite_course_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.courses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class Batch(Base):
    __tablename__ = "batches"
    __table_args__ = (
        UniqueConstraint("curriculum_id", "name", name="uq_curriculum_batch_curriculum_name"),
        {"schema": "curriculum"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    curriculum_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.curricula.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    intake_year = Column(SmallInteger, nullable=False)
    graduation_year = Column(SmallInteger, nullable=True)
    status = Column(String(20), nullable=False, server_default="ACTIVE")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class AcademicTerm(Base):
    __tablename__ = "academic_terms"
    __table_args__ = (
        UniqueConstraint("organization_id", "year", "season", name="uq_curriculum_academic_term_org_year_season"),
        {"schema": "curriculum"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    year = Column(SmallInteger, nullable=False)
    season = Column(String(20), nullable=False)
    start_date = Column(sa.Date, nullable=False)
    end_date = Column(sa.Date, nullable=False)
    status = Column(String(20), nullable=False, server_default="UPCOMING")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class Section(Base):
    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_curriculum_section_org_name"),
        {"schema": "curriculum"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name = Column(String(50), nullable=False)
    capacity = Column(SmallInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class SectionOffering(Base):
    __tablename__ = "section_offerings"
    __table_args__ = (
        UniqueConstraint(
            "batch_id", "course_id", "academic_term_id", "section_id",
            name="uq_curriculum_section_offering_batch_course_term_section",
        ),
        {"schema": "curriculum"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    curriculum_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.curricula.id", ondelete="RESTRICT"),
        nullable=False,
    )
    batch_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.batches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    course_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.courses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    academic_term_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.academic_terms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    section_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.sections.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status = Column(String(20), nullable=False, server_default="UPCOMING")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class FacultyAssignment(Base):
    __tablename__ = "faculty_assignments"
    __table_args__ = (
        Index(
            "uq_curriculum_faculty_assignment_active",
            "section_offering_id", "user_id", "role_in_course",
            unique=True,
            postgresql_where=sa.text("removed_at IS NULL"),
        ),
        {"schema": "curriculum"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    section_offering_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.section_offerings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # user_id stored without ORM FK — avoids cross-schema model coupling with IAM
    user_id = Column(PGUUID(as_uuid=True), nullable=False)
    role_in_course = Column(String(30), nullable=False)
    assigned_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    removed_at = Column(DateTime(timezone=True), nullable=True)
