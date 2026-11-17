"""Outline import: allow OUTLINE_IMPORT suggestions

Revision ID: 0060_outline_import
Revises: 0059_question_rewrites
Create Date: 2026-11-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0060_outline_import"
down_revision: Union[str, None] = "0059_question_rewrites"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NAME = "chk_obe_outcome_suggestion_kind"


def upgrade() -> None:
    op.drop_constraint(_NAME, "outcome_suggestions", schema="obe", type_="check")
    op.create_check_constraint(
        _NAME, "outcome_suggestions",
        "kind IN ('CO_DRAFT','CO_REFINE','CO_PO_MAPPING','OUTLINE_IMPORT')", schema="obe",
    )


def downgrade() -> None:
    op.execute("DELETE FROM obe.outcome_suggestions WHERE kind = 'OUTLINE_IMPORT'")
    op.drop_constraint(_NAME, "outcome_suggestions", schema="obe", type_="check")
    op.create_check_constraint(
        _NAME, "outcome_suggestions", "kind IN ('CO_DRAFT','CO_REFINE','CO_PO_MAPPING')", schema="obe",
    )
