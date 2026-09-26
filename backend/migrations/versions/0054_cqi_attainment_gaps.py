"""CQI attainment gaps — flag unattained COs and POs for corrective action (BR-20)

Revision ID: 0054_cqi_attainment_gaps
Revises: 0053_program_credits_float
Create Date: 2026-09-05 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0054_cqi_attainment_gaps"
down_revision: Union[str, None] = "0053_program_credits_float"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATUS_CHECK = "status IN ('OPEN','ADDRESSED','CLOSED','WAIVED')"

_PERMISSIONS = [
    ("cqi.read", "View attainment gaps and CQI summary"),
    ("cqi.gap.waive", "Waive an attainment gap with a documented reason"),
]


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS cqi")

    op.create_table(
        "co_attainment_gaps",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("section_offering_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("curriculum.section_offerings.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("course_outcome_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("obe.course_outcomes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attainment_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("average_score_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("threshold_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("students_above_threshold", sa.Integer(), nullable=False),
        sa.Column("total_students", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'OPEN'")),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("waived_by_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("waiver_reason", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("section_offering_id", "course_outcome_id",
                            name="uq_cqi_co_gap_offering_co"),
        sa.CheckConstraint(_STATUS_CHECK, name="chk_cqi_co_gap_status"),
        schema="cqi",
    )
    op.create_index("ix_cqi_co_attainment_gaps_organization_id", "co_attainment_gaps",
                    ["organization_id"], schema="cqi")
    op.create_index("ix_cqi_co_attainment_gaps_section_offering_id", "co_attainment_gaps",
                    ["section_offering_id"], schema="cqi")
    op.create_index("ix_cqi_co_attainment_gaps_course_outcome_id", "co_attainment_gaps",
                    ["course_outcome_id"], schema="cqi")
    op.create_index("ix_cqi_co_gaps_org_status", "co_attainment_gaps",
                    ["organization_id", "status"], schema="cqi")

    op.create_table(
        "po_attainment_gaps",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("program_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("org.programs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("academic_term_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("curriculum.academic_terms.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("program_outcome_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("obe.program_outcomes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("aggregate_attainment_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("threshold_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("contributing_offering_count", sa.Integer(), nullable=False),
        sa.Column("attained_offering_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'OPEN'")),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("waived_by_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("waiver_reason", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("program_id", "academic_term_id", "program_outcome_id",
                            name="uq_cqi_po_gap_program_term_po"),
        sa.CheckConstraint(_STATUS_CHECK, name="chk_cqi_po_gap_status"),
        schema="cqi",
    )
    op.create_index("ix_cqi_po_attainment_gaps_organization_id", "po_attainment_gaps",
                    ["organization_id"], schema="cqi")
    op.create_index("ix_cqi_po_attainment_gaps_program_id", "po_attainment_gaps",
                    ["program_id"], schema="cqi")
    op.create_index("ix_cqi_po_attainment_gaps_academic_term_id", "po_attainment_gaps",
                    ["academic_term_id"], schema="cqi")
    op.create_index("ix_cqi_po_attainment_gaps_program_outcome_id", "po_attainment_gaps",
                    ["program_outcome_id"], schema="cqi")
    op.create_index("ix_cqi_po_gaps_org_status", "po_attainment_gaps",
                    ["organization_id", "status"], schema="cqi")

    # ── Permissions ───────────────────────────────────────────────────────────
    for code, description in _PERMISSIONS:
        op.execute(
            sa.text(
                """
                INSERT INTO iam.permissions (code, description, tier, module)
                VALUES (:code, :description, 'SYSTEM', 'cqi')
                ON CONFLICT (code) DO NOTHING
                """
            ).bindparams(code=code, description=description)
        )

    # Super Admin and Program Coordinator hold every permission.
    op.execute(
        """
        INSERT INTO iam.role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM iam.roles r
        JOIN iam.permissions p ON p.code IN ('cqi.read', 'cqi.gap.waive')
        WHERE r.name IN ('Super Admin', 'Program Coordinator')
        ON CONFLICT DO NOTHING
        """
    )
    # Module Leaders and Section Teachers see gaps but cannot waive them.
    op.execute(
        """
        INSERT INTO iam.role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM iam.roles r
        JOIN iam.permissions p ON p.code = 'cqi.read'
        WHERE r.name IN ('Module Leader', 'Section Teacher')
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM iam.role_permissions rp
        USING iam.permissions p
        WHERE rp.permission_id = p.id
          AND p.code IN ('cqi.read', 'cqi.gap.waive')
        """
    )
    op.execute("DELETE FROM iam.permissions WHERE code IN ('cqi.read', 'cqi.gap.waive')")
    op.drop_table("po_attainment_gaps", schema="cqi")
    op.drop_table("co_attainment_gaps", schema="cqi")
    op.execute("DROP SCHEMA IF EXISTS cqi")
