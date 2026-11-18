"""Public /docs page: settings, sections with versions, team; demo flag on organizations

Revision ID: 0064_live_docs
Revises: 0063_evidence_writer
Create Date: 2026-11-18 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0064_live_docs"
down_revision: Union[str, None] = "0063_evidence_writer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UUID = sa.dialects.postgresql.UUID(as_uuid=True)
_JSONB = sa.dialects.postgresql.JSONB()
_NOW = sa.text("now()")


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        schema="org",
    )
    # The demo organization is seeded with the short name DEMO (scripts.seed_superadmin).
    op.execute("UPDATE org.organizations SET is_demo = true WHERE short_name = 'DEMO'")

    op.create_table(
        "docs_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("schedule_mode", sa.String(10), nullable=False, server_default=sa.text("'window'")),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("team_name", sa.String(150), nullable=True),
        sa.Column("updated_by_user_id", _UUID, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
        sa.CheckConstraint("id = 1", name="chk_docs_settings_singleton"),
        sa.CheckConstraint("schedule_mode IN ('always','window','duration')",
                           name="chk_docs_settings_mode"),
        schema="config",
    )

    op.create_table(
        "docs_sections",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("key", sa.String(60), nullable=False),
        sa.Column("section_group", sa.String(20), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("draft_title", sa.String(200), nullable=False),
        sa.Column("draft_body", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("draft_data", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("published_title", sa.String(200), nullable=True),
        sa.Column("published_body", sa.Text(), nullable=True),
        sa.Column("published_data", _JSONB, nullable=True),
        sa.Column("published_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by_user_id", _UUID, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
        sa.UniqueConstraint("key", name="uq_docs_sections_key"),
        schema="config",
    )

    op.create_table(
        "docs_section_versions",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("section_id", _UUID,
                  sa.ForeignKey("config.docs_sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("data", _JSONB, nullable=False),
        sa.Column("published_by_user_id", _UUID, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
        sa.UniqueConstraint("section_id", "version", name="uq_docs_section_versions"),
        schema="config",
    )
    op.create_index("ix_config_docs_section_versions_section_id", "docs_section_versions",
                    ["section_id"], schema="config")

    op.create_table(
        "docs_team_members",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("role", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("photo", sa.LargeBinary(), nullable=True),
        sa.Column("photo_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW),
        schema="config",
    )


def downgrade() -> None:
    op.drop_table("docs_team_members", schema="config")
    op.drop_index("ix_config_docs_section_versions_section_id", table_name="docs_section_versions",
                  schema="config")
    op.drop_table("docs_section_versions", schema="config")
    op.drop_table("docs_sections", schema="config")
    op.drop_table("docs_settings", schema="config")
    op.drop_column("organizations", "is_demo", schema="org")
