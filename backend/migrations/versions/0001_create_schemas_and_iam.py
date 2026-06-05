"""Create all DB schemas, events outbox, and IAM tables

Revision ID: 0001
Revises:
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Create all schemas ────────────────────────────────────────────────────
    for schema in [
        "events", "iam", "org", "config",
        "curriculum", "obe", "assessment", "attainment",
        "approval", "notification", "audit", "accreditation", "reporting",
    ]:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    # ── events.domain_events (transactional outbox) ───────────────────────────
    op.create_table(
        "domain_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", UUID(as_uuid=True), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        schema="events",
    )
    op.create_index("ix_events_domain_events_event_type", "domain_events", ["event_type"], schema="events")
    op.create_index("ix_events_domain_events_status", "domain_events", ["status"], schema="events")

    # ── iam.permissions ───────────────────────────────────────────────────────
    op.create_table(
        "permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("tier", sa.String(20), nullable=False, server_default="SYSTEM"),
        sa.Column("module", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("code", name="uq_iam_permissions_code"),
        schema="iam",
    )

    # ── iam.roles ─────────────────────────────────────────────────────────────
    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "name", name="uq_iam_roles_org_name"),
        schema="iam",
    )
    op.create_index("ix_iam_roles_organization_id", "roles", ["organization_id"], schema="iam")

    # ── iam.role_permissions ──────────────────────────────────────────────────
    op.create_table(
        "role_permissions",
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("iam.roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", UUID(as_uuid=True), sa.ForeignKey("iam.permissions.id", ondelete="CASCADE"), primary_key=True),
        schema="iam",
    )

    # ── iam.users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("linked_student_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("email", name="uq_iam_users_email"),
        schema="iam",
    )
    op.create_index("ix_iam_users_organization_id", "users", ["organization_id"], schema="iam")
    op.execute(
        "CREATE UNIQUE INDEX uq_iam_users_linked_student_id "
        "ON iam.users (linked_student_id) "
        "WHERE linked_student_id IS NOT NULL"
    )

    # ── iam.password_credentials ──────────────────────────────────────────────
    op.create_table(
        "password_credentials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("iam.users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="iam",
    )

    # ── iam.refresh_tokens ────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("iam.users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="iam",
    )
    op.create_index("ix_iam_refresh_tokens_user_id", "refresh_tokens", ["user_id"], schema="iam")

    # ── iam.user_role_assignments ─────────────────────────────────────────────
    op.create_table(
        "user_role_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("iam.users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("iam.roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("scope_id", UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_by", UUID(as_uuid=True), sa.ForeignKey("iam.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        schema="iam",
    )
    op.create_index("ix_iam_user_role_assignments_user_id", "user_role_assignments", ["user_id"], schema="iam")


def downgrade() -> None:
    op.drop_table("user_role_assignments", schema="iam")
    op.drop_table("refresh_tokens", schema="iam")
    op.drop_table("password_credentials", schema="iam")
    op.drop_table("users", schema="iam")
    op.drop_table("role_permissions", schema="iam")
    op.drop_table("roles", schema="iam")
    op.drop_table("permissions", schema="iam")
    op.drop_table("domain_events", schema="events")

    for schema in [
        "reporting", "accreditation", "audit", "notification",
        "approval", "attainment", "assessment", "obe",
        "curriculum", "config", "org", "iam", "events",
    ]:
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
