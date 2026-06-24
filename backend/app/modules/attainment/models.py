import sqlalchemy as sa
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index,
    Integer, Numeric, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class AttainmentConfig(Base):
    __tablename__ = "attainment_configs"
    __table_args__ = (
        UniqueConstraint("organization_id", "program_id", name="uq_attainment_config_org_program"),
        Index(
            "uq_attainment_config_org_default",
            "organization_id",
            unique=True,
            postgresql_where=sa.text("program_id IS NULL"),
        ),
        {"schema": "attainment"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    program_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.programs.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    threshold_student_pct = Column(Numeric(5, 2), nullable=False, server_default=sa.text("50.00"))
    threshold_co_score_pct = Column(Numeric(5, 2), nullable=False, server_default=sa.text("50.00"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class COAttainmentResult(Base):
    __tablename__ = "co_attainment_results"
    __table_args__ = (
        UniqueConstraint(
            "section_offering_id", "course_outcome_id",
            name="uq_attainment_co_result_offering_co",
        ),
        {"schema": "attainment"},
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
    course_outcome_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    average_attainment_pct = Column(Numeric(5, 2), nullable=False)
    students_above_threshold = Column(Integer, nullable=False)
    total_students = Column(Integer, nullable=False)
    is_attained = Column(Boolean, nullable=False)
    calculated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class POAttainmentResult(Base):
    __tablename__ = "po_attainment_results"
    __table_args__ = (
        UniqueConstraint(
            "section_offering_id", "program_outcome_id",
            name="uq_attainment_po_result_offering_po",
        ),
        {"schema": "attainment"},
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
    program_outcome_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.program_outcomes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    attainment_pct = Column(Numeric(5, 2), nullable=False)
    contributing_co_count = Column(Integer, nullable=False)
    students_above_threshold = Column(Integer, nullable=False, server_default=sa.text("0"))
    total_students = Column(Integer, nullable=False, server_default=sa.text("0"))
    is_attained = Column(Boolean, nullable=False)
    calculated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )
