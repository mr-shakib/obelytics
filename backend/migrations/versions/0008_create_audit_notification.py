"""Create audit and notification schema tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as pg

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")
    op.execute("CREATE SCHEMA IF NOT EXISTS notification")

    # ── audit.audit_logs ──────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", pg(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "organization_id",
            pg(as_uuid=True),
            sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("actor_user_id", pg(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", pg(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("before_status", sa.String(30), nullable=True),
        sa.Column("after_status", sa.String(30), nullable=True),
        sa.Column("extra", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="audit",
    )
    op.create_index("ix_audit_log_org", "audit_logs", ["organization_id"], schema="audit")
    op.create_index("ix_audit_log_entity", "audit_logs", ["entity_type", "entity_id"], schema="audit")
    op.create_index("ix_audit_log_actor", "audit_logs", ["actor_user_id"], schema="audit")

    # ── notification.notifications ────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", pg(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "organization_id",
            pg(as_uuid=True),
            sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("recipient_user_id", pg(as_uuid=True), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", pg(as_uuid=True), nullable=True),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        schema="notification",
    )
    op.create_index("ix_notification_org", "notifications", ["organization_id"], schema="notification")
    op.create_index(
        "ix_notification_recipient",
        "notifications",
        ["recipient_user_id", "is_read"],
        schema="notification",
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS audit CASCADE")
    op.execute("DROP SCHEMA IF EXISTS notification CASCADE")
