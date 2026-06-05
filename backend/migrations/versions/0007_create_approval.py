"""Create approval schema tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as pg

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS approval")

    op.create_table(
        "review_comments",
        sa.Column("id", pg(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("organization_id", pg(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", pg(as_uuid=True), nullable=False),
        sa.Column("author_user_id", pg(as_uuid=True), nullable=False),
        sa.Column("comment", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="approval",
    )
    op.create_index("ix_approval_review_comment_entity", "review_comments", ["entity_type", "entity_id"], schema="approval")
    op.create_index("ix_approval_review_comment_org", "review_comments", ["organization_id"], schema="approval")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS approval CASCADE")
