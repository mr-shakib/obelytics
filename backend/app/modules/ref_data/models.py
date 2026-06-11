import sqlalchemy as sa
from sqlalchemy import Column, String, SmallInteger, Boolean, DateTime, ForeignKey, UniqueConstraint, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from app.core.database import Base


class BloomDomain(Base):
    __tablename__ = "bloom_domains"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_config_bloom_domain_org_name"),
        {"schema": "config"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
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


class BloomLevel(Base):
    __tablename__ = "bloom_levels"
    __table_args__ = (
        UniqueConstraint("organization_id", "bloom_domain_id", "code", name="uq_config_bloom_level_org_domain_code"),
        {"schema": "config"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    bloom_domain_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("config.bloom_domains.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code = Column(String(10), nullable=False)
    name = Column(String(100), nullable=False)
    order_index = Column(SmallInteger, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class DeliveryMethod(Base):
    __tablename__ = "delivery_methods"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_config_delivery_method_org_name"),
        {"schema": "config"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
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


class CourseCategory(Base):
    __tablename__ = "course_categories"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_config_course_category_org_name"),
        {"schema": "config"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
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


class AssessmentType(Base):
    __tablename__ = "assessment_types"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_config_assessment_type_org_name"),
        {"schema": "config"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    is_sessional = Column(Boolean, nullable=False, server_default="false")
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class ComplexProblem(Base):
    __tablename__ = "complex_problems"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_config_complex_problem_org_code"),
        {"schema": "config"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    code = Column(String(20), nullable=False)
    name = Column(String(150), nullable=True)
    description = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class ComplexActivity(Base):
    __tablename__ = "complex_activities"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_config_complex_activity_org_code"),
        {"schema": "config"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    code = Column(String(20), nullable=False)
    name = Column(String(150), nullable=True)
    description = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class KnowledgeProfile(Base):
    __tablename__ = "knowledge_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_config_knowledge_profile_org_code"),
        {"schema": "config"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    code = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class POType(Base):
    __tablename__ = "po_types"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_config_po_type_org_name"),
        {"schema": "config"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class MappingWeightLabel(Base):
    __tablename__ = "mapping_weight_labels"
    __table_args__ = (
        UniqueConstraint("organization_id", "weight_value", name="uq_config_mapping_weight_org_value"),
        CheckConstraint("weight_value IN (1, 2, 3)", name="ck_config_mapping_weight_valid"),
        {"schema": "config"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    weight_value = Column(SmallInteger, nullable=False)
    label = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )
