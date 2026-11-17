"""Workforce readiness: job postings and skill-coverage analyses

Revision ID: 0061_workforce_market
Revises: 0060_outline_import
Create Date: 2026-11-12 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0061_workforce_market"
down_revision: Union[str, None] = "0060_outline_import"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UUID = sa.dialects.postgresql.UUID(as_uuid=True)
_JSONB = sa.dialects.postgresql.JSONB()


def upgrade() -> None:
    op.create_table(
        "market_postings",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", _UUID,
                  sa.ForeignKey("org.organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("program_id", _UUID, sa.ForeignKey("org.programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("employer", sa.String(255), nullable=True),
        sa.Column("source", sa.String(500), nullable=True),
        sa.Column("posted_on", sa.Date(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("skills", _JSONB, nullable=True),
        sa.Column("skills_model", sa.String(100), nullable=True),
        sa.Column("skills_prompt_version", sa.String(50), nullable=True),
        sa.Column("created_by_user_id", _UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="obe",
    )
    op.create_index("ix_obe_market_postings_organization_id", "market_postings", ["organization_id"], schema="obe")
    op.create_index("ix_obe_market_postings_program_id", "market_postings", ["program_id"], schema="obe")

    op.create_table(
        "market_analyses",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", _UUID,
                  sa.ForeignKey("org.organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("program_id", _UUID, sa.ForeignKey("org.programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("curriculum_id", _UUID,
                  sa.ForeignKey("curriculum.curricula.id", ondelete="CASCADE"), nullable=False),
        sa.Column("posting_count", sa.Integer(), nullable=False),
        sa.Column("result", _JSONB, nullable=False),
        sa.Column("provider", sa.String(10), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("created_by_user_id", _UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="obe",
    )
    op.create_index("ix_obe_market_analyses_organization_id", "market_analyses", ["organization_id"], schema="obe")
    op.create_index("ix_obe_market_analyses_curriculum_id", "market_analyses", ["curriculum_id"], schema="obe")


def downgrade() -> None:
    op.drop_index("ix_obe_market_analyses_curriculum_id", table_name="market_analyses", schema="obe")
    op.drop_index("ix_obe_market_analyses_organization_id", table_name="market_analyses", schema="obe")
    op.drop_table("market_analyses", schema="obe")
    op.drop_index("ix_obe_market_postings_program_id", table_name="market_postings", schema="obe")
    op.drop_index("ix_obe_market_postings_organization_id", table_name="market_postings", schema="obe")
    op.drop_table("market_postings", schema="obe")
