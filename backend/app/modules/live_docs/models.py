"""
Tables behind the public /docs page. The page belongs to the deployment, not to an
organization, so these rows carry no organization id.

- DocsSettings: one row (id 1) — on/off switch and publishing schedule.
- DocsSection: one row per section. Editors change the draft_* columns; publishing
  copies them to the published_* columns and records a DocsSectionVersion.
- DocsTeamMember: the team grid, with a photo already resized to a fixed square.
"""
import sqlalchemy as sa
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base

SCHEDULE_MODES = ("always", "window", "duration")
GROUPS = ("pitch", "product", "technical", "operations")
KINDS = (
    "markdown", "demo", "traction", "features", "diagram", "api",
    "analytics", "team", "contributors", "changelog",
)


class DocsSettings(Base):
    __tablename__ = "docs_settings"
    __table_args__ = (
        sa.CheckConstraint("id = 1", name="chk_docs_settings_singleton"),
        sa.CheckConstraint(
            "schedule_mode IN ('always','window','duration')", name="chk_docs_settings_mode"
        ),
        {"schema": "config"},
    )

    id = Column(Integer, primary_key=True, autoincrement=False)
    is_enabled = Column(Boolean, nullable=False, server_default=sa.text("true"))
    schedule_mode = Column(String(10), nullable=False, server_default=sa.text("'window'"))
    starts_at = Column(DateTime(timezone=True), nullable=True)
    ends_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    team_name = Column(String(150), nullable=True)
    updated_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class DocsSection(Base):
    __tablename__ = "docs_sections"
    __table_args__ = (
        sa.UniqueConstraint("key", name="uq_docs_sections_key"),
        {"schema": "config"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    key = Column(String(60), nullable=False)
    group = Column("section_group", String(20), nullable=False)
    kind = Column(String(20), nullable=False)
    position = Column(Integer, nullable=False, server_default=sa.text("0"))
    is_visible = Column(Boolean, nullable=False, server_default=sa.text("true"))
    is_builtin = Column(Boolean, nullable=False, server_default=sa.text("false"))
    draft_title = Column(String(200), nullable=False)
    draft_body = Column(Text, nullable=False, server_default=sa.text("''"))
    draft_data = Column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    published_title = Column(String(200), nullable=True)
    published_body = Column(Text, nullable=True)
    published_data = Column(JSONB, nullable=True)
    published_version = Column(Integer, nullable=False, server_default=sa.text("0"))
    published_at = Column(DateTime(timezone=True), nullable=True)
    updated_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )


class DocsSectionVersion(Base):
    __tablename__ = "docs_section_versions"
    __table_args__ = (
        sa.UniqueConstraint("section_id", "version", name="uq_docs_section_versions"),
        {"schema": "config"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    section_id = Column(
        PGUUID(as_uuid=True), ForeignKey("config.docs_sections.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSONB, nullable=False)
    published_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class DocsTeamMember(Base):
    __tablename__ = "docs_team_members"
    __table_args__ = {"schema": "config"}

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    full_name = Column(String(150), nullable=False)
    role = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False)
    position = Column(Integer, nullable=False, server_default=sa.text("0"))
    photo = Column(LargeBinary, nullable=True)
    photo_version = Column(Integer, nullable=False, server_default=sa.text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )
