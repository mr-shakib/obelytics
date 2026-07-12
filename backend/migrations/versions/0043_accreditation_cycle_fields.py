"""Rename accreditation cycle year fields to dates; add criterion status/assignee

Revision ID: 0043_accreditation_cycle_fields
Revises: 0042_report_runs
Create Date: 2026-07-12 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0043_accreditation_cycle_fields"
down_revision: Union[str, None] = "0042_report_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "accreditation_cycles", "accreditation_body",
        new_column_name="body",
        schema="accreditation",
    )
    op.add_column(
        "accreditation_cycles",
        sa.Column("start_date", sa.Date(), nullable=True),
        schema="accreditation",
    )
    op.add_column(
        "accreditation_cycles",
        sa.Column("end_date", sa.Date(), nullable=True),
        schema="accreditation",
    )
    op.execute(
        "UPDATE accreditation.accreditation_cycles "
        "SET start_date = make_date(cycle_start_year, 1, 1), "
        "    end_date = make_date(cycle_end_year, 12, 31)"
    )
    op.alter_column("accreditation_cycles", "start_date", nullable=False, schema="accreditation")
    op.drop_column("accreditation_cycles", "cycle_start_year", schema="accreditation")
    op.drop_column("accreditation_cycles", "cycle_end_year", schema="accreditation")

    op.add_column(
        "accreditation_criteria",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="NOT_STARTED"),
        schema="accreditation",
    )
    op.add_column(
        "accreditation_criteria",
        # user_id stored without ORM FK — avoids cross-schema model coupling with IAM
        sa.Column("assigned_to_user_id", UUID(as_uuid=True), nullable=True),
        schema="accreditation",
    )
    op.create_check_constraint(
        "chk_accreditation_criterion_status",
        "accreditation_criteria",
        "status IN ('NOT_STARTED','IN_PROGRESS','COMPLETED')",
        schema="accreditation",
    )


def downgrade() -> None:
    op.drop_constraint(
        "chk_accreditation_criterion_status", "accreditation_criteria", schema="accreditation"
    )
    op.drop_column("accreditation_criteria", "assigned_to_user_id", schema="accreditation")
    op.drop_column("accreditation_criteria", "status", schema="accreditation")

    op.add_column(
        "accreditation_cycles",
        sa.Column("cycle_start_year", sa.SmallInteger(), nullable=True),
        schema="accreditation",
    )
    op.add_column(
        "accreditation_cycles",
        sa.Column("cycle_end_year", sa.SmallInteger(), nullable=True),
        schema="accreditation",
    )
    op.execute(
        "UPDATE accreditation.accreditation_cycles "
        "SET cycle_start_year = EXTRACT(YEAR FROM start_date)::smallint, "
        "    cycle_end_year = EXTRACT(YEAR FROM end_date)::smallint"
    )
    op.alter_column("accreditation_cycles", "cycle_start_year", nullable=False, schema="accreditation")
    op.alter_column("accreditation_cycles", "cycle_end_year", nullable=False, schema="accreditation")
    op.drop_column("accreditation_cycles", "end_date", schema="accreditation")
    op.drop_column("accreditation_cycles", "start_date", schema="accreditation")
    op.alter_column(
        "accreditation_cycles", "body",
        new_column_name="accreditation_body",
        schema="accreditation",
    )
