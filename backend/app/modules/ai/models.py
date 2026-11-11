"""
AI gateway records.

OrganizationAISettings — which provider each AI feature uses for one organization.
A NULL column means "use the server default" (AI_*_PROVIDER in settings).

AICall — one row per model call: who, which feature, which provider and model,
how many tokens, how long, what it cost, and how many personal-data matches were
redacted before the call. Prompts and outputs are not stored here; features keep
their own outputs (with model and prompt version) and write the audit log.
"""
import sqlalchemy as sa
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base

PROVIDERS = ("local", "hosted", "off")
FEATURES = ("integrity", "copilot")


class OrganizationAISettings(Base):
    __tablename__ = "organization_settings"
    __table_args__ = (
        CheckConstraint(
            "integrity_provider IS NULL OR integrity_provider IN ('local','hosted','off')",
            name="chk_ai_settings_integrity_provider",
        ),
        CheckConstraint(
            "copilot_provider IS NULL OR copilot_provider IN ('local','hosted','off')",
            name="chk_ai_settings_copilot_provider",
        ),
        {"schema": "ai"},
    )

    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    integrity_provider = Column(String(10), nullable=True)
    copilot_provider = Column(String(10), nullable=True)
    # Plain UUID — no FK constraint (cross-schema IAM)
    updated_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class AICall(Base):
    __tablename__ = "calls"
    __table_args__ = (
        Index("ix_ai_calls_organization_created", "organization_id", "created_at"),
        CheckConstraint("status IN ('OK','ERROR')", name="chk_ai_calls_status"),
        {"schema": "ai"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Plain UUID — no FK constraint (cross-schema IAM)
    user_id = Column(PGUUID(as_uuid=True), nullable=True)
    feature = Column(String(30), nullable=False)
    purpose = Column(String(50), nullable=False)
    provider = Column(String(10), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_version = Column(String(50), nullable=True)
    status = Column(String(10), nullable=False)
    error = Column(Text, nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    image_count = Column(Integer, nullable=False, server_default=sa.text("0"))
    redactions = Column(Integer, nullable=False, server_default=sa.text("0"))
    latency_ms = Column(Integer, nullable=False)
    cost_usd = Column(Numeric(12, 6), nullable=False, server_default=sa.text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
