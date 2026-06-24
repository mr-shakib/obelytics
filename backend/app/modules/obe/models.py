import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class POVersion(Base):
    __tablename__ = "po_versions"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_obe_po_version_org_name"),
        {"schema": "obe"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class ProgramOutcome(Base):
    __tablename__ = "program_outcomes"
    __table_args__ = (
        Index(
            "uq_obe_po_org_code_active",
            "organization_id",
            "code",
            unique=True,
            postgresql_where=sa.text("status = 'ACTIVE'"),
        ),
        {"schema": "obe"},
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
    po_version_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.po_versions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    bloom_domain_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("config.bloom_domains.id", ondelete="RESTRICT"),
        nullable=True,
    )
    code = Column(String(20), nullable=False)
    reference = Column(String(100), nullable=True)
    statement = Column(Text, nullable=False)
    po_type = Column(String(100), nullable=True)
    order_index = Column(SmallInteger, nullable=False)
    status = Column(String(20), nullable=False, server_default="ACTIVE")
    archived_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class POKnowledgeProfile(Base):
    __tablename__ = "po_knowledge_profiles"
    __table_args__ = (
        UniqueConstraint("program_outcome_id", "knowledge_profile_id", name="uq_obe_po_kp"),
        {"schema": "obe"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    program_outcome_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.program_outcomes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    knowledge_profile_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("config.knowledge_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class CourseOutcome(Base):
    __tablename__ = "course_outcomes"
    __table_args__ = (
        UniqueConstraint(
            "curriculum_id", "course_id", "code", name="uq_obe_co_curriculum_course_code"
        ),
        Index("ix_obe_co_curriculum_course_status", "curriculum_id", "course_id", "status"),
        {"schema": "obe"},
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
    course_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.courses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code = Column(String(20), nullable=False)
    statement = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, server_default="DRAFT")
    # Plain UUID — no FK constraint (cross-schema IAM)
    created_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class CourseOutcomeBloomLevel(Base):
    __tablename__ = "course_outcome_bloom_levels"
    __table_args__ = (
        UniqueConstraint("course_outcome_id", "bloom_level_id", name="uq_obe_co_bloom_level"),
        {"schema": "obe"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    course_outcome_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.course_outcomes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bloom_level_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("config.bloom_levels.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class CODeliveryMethod(Base):
    __tablename__ = "co_delivery_methods"
    __table_args__ = (
        UniqueConstraint("course_outcome_id", "delivery_method_id", name="uq_obe_co_dm"),
        {"schema": "obe"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    course_outcome_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    delivery_method_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("config.delivery_methods.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class COPOMappingSet(Base):
    __tablename__ = "co_po_mapping_sets"
    __table_args__ = (
        UniqueConstraint(
            "curriculum_id", "course_id", name="uq_obe_co_po_mapping_set_curriculum_course"
        ),
        {"schema": "obe"},
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
    course_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.courses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status = Column(String(20), nullable=False, server_default="DRAFT")
    # Plain UUID — no FK constraint
    created_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class COPOMappingEntry(Base):
    __tablename__ = "co_po_mapping_entries"
    __table_args__ = (
        UniqueConstraint(
            "mapping_set_id",
            "course_outcome_id",
            "program_outcome_id",
            name="uq_obe_co_po_mapping_entry",
        ),
        CheckConstraint("weight IN (1, 2, 3)", name="ck_obe_co_po_mapping_entry_weight"),
        {"schema": "obe"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    mapping_set_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.co_po_mapping_sets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    course_outcome_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    program_outcome_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.program_outcomes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    weight = Column(SmallInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class COCPMapping(Base):
    __tablename__ = "co_cp_mappings"
    __table_args__ = (
        UniqueConstraint("course_outcome_id", "complex_problem_id", name="uq_obe_co_cp"),
        {"schema": "obe"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    course_outcome_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    complex_problem_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("config.complex_problems.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status = Column(String(20), nullable=False, server_default="DRAFT")
    # Plain UUIDs — no FK constraints
    created_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    approved_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class COCAMapping(Base):
    __tablename__ = "co_ca_mappings"
    __table_args__ = (
        UniqueConstraint("course_outcome_id", "complex_activity_id", name="uq_obe_co_ca"),
        {"schema": "obe"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    course_outcome_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    complex_activity_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("config.complex_activities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status = Column(String(20), nullable=False, server_default="DRAFT")
    # Plain UUIDs — no FK constraints
    created_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    approved_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class COKPMapping(Base):
    __tablename__ = "co_kp_mappings"
    __table_args__ = (
        UniqueConstraint("course_outcome_id", "knowledge_profile_id", name="uq_obe_co_kp"),
        {"schema": "obe"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    course_outcome_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    knowledge_profile_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("config.knowledge_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status = Column(String(20), nullable=False, server_default="DRAFT")
    # Plain UUIDs — no FK constraints
    created_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    approved_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


# ── Program Missions ──────────────────────────────────────────────────────────


class ProgramMission(Base):
    __tablename__ = "program_missions"
    __table_args__ = (
        Index(
            "uq_obe_mission_program_code_active",
            "program_id",
            "code",
            unique=True,
            postgresql_where=sa.text("status = 'ACTIVE'"),
        ),
        {"schema": "obe"},
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
        nullable=False,
        index=True,
    )
    code = Column(String(20), nullable=False)
    statement = Column(Text, nullable=False)
    order_index = Column(SmallInteger, nullable=False)
    status = Column(String(20), nullable=False, server_default="ACTIVE")
    archived_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


# ── Program Educational Objectives (PEO) ─────────────────────────────────────


class ProgramEducationalObjective(Base):
    __tablename__ = "program_educational_objectives"
    __table_args__ = (
        Index(
            "uq_obe_peo_program_code_active",
            "program_id",
            "code",
            unique=True,
            postgresql_where=sa.text("status = 'ACTIVE'"),
        ),
        {"schema": "obe"},
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
        nullable=False,
        index=True,
    )
    code = Column(String(20), nullable=False)
    statement = Column(Text, nullable=False)
    order_index = Column(SmallInteger, nullable=False)
    status = Column(String(20), nullable=False, server_default="ACTIVE")
    archived_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


# ── PEO-PO Mapping ────────────────────────────────────────────────────────────


class PEOPOMapping(Base):
    __tablename__ = "peo_po_mappings"
    __table_args__ = (
        UniqueConstraint("peo_id", "program_outcome_id", name="uq_obe_peo_po"),
        {"schema": "obe"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    peo_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.program_educational_objectives.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_outcome_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.program_outcomes.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


# ── PEO-Mission Mapping ───────────────────────────────────────────────────────


class PEOMissionMapping(Base):
    __tablename__ = "peo_mission_mappings"
    __table_args__ = (
        UniqueConstraint("peo_id", "mission_id", name="uq_obe_peo_mission"),
        {"schema": "obe"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    peo_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.program_educational_objectives.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mission_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("obe.program_missions.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
