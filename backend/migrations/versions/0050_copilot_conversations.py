"""Add copilot conversations and messages

Revision ID: 0050_copilot_conversations
Revises: 0049_seed_batch_delete_perm
Create Date: 2026-07-16 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0050_copilot_conversations"
down_revision: Union[str, None] = "0049_seed_batch_delete_perm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS copilot")
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), server_default="New conversation", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["org.organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["iam.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="copilot",
    )
    op.create_index(
        "ix_copilot_conversations_owner",
        "conversations",
        ["organization_id", "user_id", "updated_at"],
        schema="copilot",
    )
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="COMPLETE", nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("token_usage", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tool_calls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["copilot.conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="copilot",
    )
    op.create_index(
        "ix_copilot_messages_conversation_created",
        "messages",
        ["conversation_id", "created_at"],
        schema="copilot",
    )


def downgrade() -> None:
    op.drop_table("messages", schema="copilot")
    op.drop_table("conversations", schema="copilot")
    op.execute("DROP SCHEMA IF EXISTS copilot")
