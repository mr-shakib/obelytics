"""Outcome authoring: AI provider choice for the feature and the suggestions it makes

Revision ID: 0058_outcome_authoring
Revises: 0057_ai_gateway_integrity_jobs
Create Date: 2026-11-12 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0058_outcome_authoring"
down_revision: Union[str, None] = "0057_ai_gateway_integrity_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UUID = sa.dialects.postgresql.UUID(as_uuid=True)
_JSONB = sa.dialects.postgresql.JSONB()


def upgrade() -> None:
    op.add_column(
        "organization_settings",
        sa.Column("authoring_provider", sa.String(10), nullable=True),
        schema="ai",
    )
    op.create_check_constraint(
        "chk_ai_settings_authoring_provider",
        "organization_settings",
        "authoring_provider IS NULL OR authoring_provider IN ('local','hosted','off')",
        schema="ai",
    )

    op.create_table(
        "outcome_suggestions",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", _UUID,
                  sa.ForeignKey("org.organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("curriculum_id", _UUID,
                  sa.ForeignKey("curriculum.curricula.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", _UUID,
                  sa.ForeignKey("curriculum.courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", _UUID, nullable=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("request", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result", _JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("provider", sa.String(10), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("decision", sa.String(10), nullable=True),
        sa.Column("decision_detail", _JSONB, nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(
            "kind IN ('CO_DRAFT','CO_REFINE','CO_PO_MAPPING')",
            name="chk_obe_outcome_suggestion_kind",
        ),
        sa.CheckConstraint(
            "decision IS NULL OR decision IN ('ACCEPTED','EDITED','PARTIAL','REJECTED')",
            name="chk_obe_outcome_suggestion_decision",
        ),
        schema="obe",
    )
    op.create_index(
        "ix_obe_outcome_suggestions_organization_id", "outcome_suggestions",
        ["organization_id"], schema="obe",
    )
    op.create_index(
        "ix_obe_outcome_suggestions_course", "outcome_suggestions",
        ["curriculum_id", "course_id", "created_at"], schema="obe",
    )


def downgrade() -> None:
    op.drop_index("ix_obe_outcome_suggestions_course", table_name="outcome_suggestions", schema="obe")
    op.drop_index(
        "ix_obe_outcome_suggestions_organization_id", table_name="outcome_suggestions", schema="obe"
    )
    op.drop_table("outcome_suggestions", schema="obe")
    op.drop_constraint(
        "chk_ai_settings_authoring_provider", "organization_settings", schema="ai", type_="check"
    )
    op.drop_column("organization_settings", "authoring_provider", schema="ai")
