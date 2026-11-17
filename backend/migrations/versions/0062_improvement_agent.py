"""Improvement agent: plans per section, and its AI provider choice

Revision ID: 0062_improvement_agent
Revises: 0061_workforce_market
Create Date: 2026-11-12 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0062_improvement_agent"
down_revision: Union[str, None] = "0061_workforce_market"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UUID = sa.dialects.postgresql.UUID(as_uuid=True)
_JSONB = sa.dialects.postgresql.JSONB()


def upgrade() -> None:
    op.add_column("organization_settings", sa.Column("improvement_provider", sa.String(10), nullable=True),
                  schema="ai")
    op.create_check_constraint(
        "chk_ai_settings_improvement_provider", "organization_settings",
        "improvement_provider IS NULL OR improvement_provider IN ('local','hosted','off')", schema="ai",
    )
    op.create_table(
        "improvement_plans",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", _UUID,
                  sa.ForeignKey("org.organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_offering_id", _UUID,
                  sa.ForeignKey("curriculum.section_offerings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", _UUID, sa.ForeignKey("curriculum.courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("follow_up", sa.Text(), nullable=True),
        sa.Column("diagnoses", _JSONB, nullable=False),
        sa.Column("steps", _JSONB, nullable=False),
        sa.Column("decisions", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("provider", sa.String(10), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("created_by_user_id", _UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="cqi",
    )
    for column in ("organization_id", "section_offering_id", "course_id"):
        op.create_index(f"ix_cqi_improvement_plans_{column}", "improvement_plans", [column], schema="cqi")


def downgrade() -> None:
    for column in ("organization_id", "section_offering_id", "course_id"):
        op.drop_index(f"ix_cqi_improvement_plans_{column}", table_name="improvement_plans", schema="cqi")
    op.drop_table("improvement_plans", schema="cqi")
    op.drop_constraint("chk_ai_settings_improvement_provider", "organization_settings", schema="ai", type_="check")
    op.drop_column("organization_settings", "improvement_provider", schema="ai")
