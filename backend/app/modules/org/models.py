import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = {"schema": "org"}

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    name = Column(String(255), nullable=False)
    short_name = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    vision = Column(Text, nullable=True)
    mission = Column(Text, nullable=True)
    logo_file_key = Column(String(500), nullable=True)
    website = Column(String(255), nullable=True)
    address_street = Column(String(255), nullable=True)
    address_city = Column(String(100), nullable=True)
    address_country = Column(String(100), nullable=True)
    address_postal_code = Column(String(20), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    email_validation_regex = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, server_default="ACTIVE")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (
        Index(
            "uq_org_dept_short_name_active",
            "organization_id",
            "short_name",
            unique=True,
            postgresql_where=sa.text("status = 'ACTIVE'"),
        ),
        {"schema": "org"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name = Column(String(200), nullable=False)
    short_name = Column(String(30), nullable=False)
    year_established = Column(SmallInteger, nullable=True)
    description = Column(Text, nullable=True)
    vision = Column(Text, nullable=True)
    mission = Column(Text, nullable=True)
    logo_file_key = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, server_default="ACTIVE")
    archived_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class DepartmentHeadHistory(Base):
    __tablename__ = "department_head_history"
    __table_args__ = (
        Index(
            "uq_org_dept_current_hod",
            "department_id",
            unique=True,
            postgresql_where=sa.text("effective_to IS NULL"),
        ),
        {"schema": "org"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    department_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.departments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # user_id stored without ORM FK — avoids cross-schema model coupling with IAM
    user_id = Column(PGUUID(as_uuid=True), nullable=False)
    effective_from = Column(sa.Date, nullable=False)
    effective_to = Column(sa.Date, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class ProgramCoordinatorHistory(Base):
    __tablename__ = "program_coordinator_history"
    __table_args__ = (
        Index(
            "uq_org_program_current_coordinator",
            "program_id",
            unique=True,
            postgresql_where=sa.text("effective_to IS NULL"),
        ),
        {"schema": "org"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    program_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.programs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # user_id stored without ORM FK — avoids cross-schema model coupling with IAM
    user_id = Column(PGUUID(as_uuid=True), nullable=False)
    effective_from = Column(sa.Date, nullable=False)
    effective_to = Column(sa.Date, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class Program(Base):
    __tablename__ = "programs"
    __table_args__ = (
        Index(
            "uq_org_program_acronym_active",
            "organization_id",
            "acronym",
            unique=True,
            postgresql_where=sa.text("status = 'ACTIVE'"),
        ),
        {"schema": "org"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    department_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.departments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    acronym = Column(String(20), nullable=False)
    program_type = Column(String(20), nullable=False)  # UNDERGRADUATE, POSTGRADUATE, PHD
    minimum_duration_semesters = Column(SmallInteger, nullable=False)
    total_credits = Column(SmallInteger, nullable=False)
    study_mode = Column(String(20), nullable=False)  # FULL_TIME, PART_TIME
    description = Column(Text, nullable=True)
    po_version_id = Column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    status = Column(String(20), nullable=False, server_default="ACTIVE")
    archived_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )
