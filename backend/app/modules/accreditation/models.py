import sqlalchemy as sa
from sqlalchemy import (
    Column, DateTime, ForeignKey, SmallInteger, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class AccreditationCycle(Base):
    __tablename__ = "accreditation_cycles"
    __table_args__ = {"schema": "accreditation"}

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
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    accreditation_body = Column(String(50), nullable=False)
    cycle_start_year = Column(SmallInteger, nullable=False)
    cycle_end_year = Column(SmallInteger, nullable=False)
    status = Column(String(20), nullable=False, server_default=sa.text("'DRAFT'"))
    created_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class AccreditationCriterion(Base):
    __tablename__ = "accreditation_criteria"
    __table_args__ = (
        UniqueConstraint("cycle_id", "code", name="uq_accreditation_criterion_cycle_code"),
        {"schema": "accreditation"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    cycle_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("accreditation.accreditation_cycles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code = Column(String(30), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order_index = Column(SmallInteger, nullable=False, server_default=sa.text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class CriterionPOMapping(Base):
    __tablename__ = "criterion_po_mappings"
    __table_args__ = (
        UniqueConstraint("criterion_id", "program_outcome_id", name="uq_accreditation_criterion_po"),
        {"schema": "accreditation"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    criterion_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("accreditation.accreditation_criteria.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_outcome_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.program_outcomes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
