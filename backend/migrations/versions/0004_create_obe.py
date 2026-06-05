"""Create OBE schema tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── obe.program_outcomes ──────────────────────────────────────────────────
    op.create_table(
        "program_outcomes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("program_id", UUID(as_uuid=True), sa.ForeignKey("org.programs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("bloom_domain_id", UUID(as_uuid=True), sa.ForeignKey("config.bloom_domains.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("po_type", sa.String(100), nullable=True),
        sa.Column("order_index", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="obe",
    )
    op.create_index("ix_obe_program_outcomes_organization_id", "program_outcomes", ["organization_id"], schema="obe")
    op.create_index("ix_obe_program_outcomes_program_id", "program_outcomes", ["program_id"], schema="obe")
    op.create_index(
        "uq_obe_po_program_code_active",
        "program_outcomes",
        ["program_id", "code"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        schema="obe",
    )

    # ── obe.po_knowledge_profiles ─────────────────────────────────────────────
    op.create_table(
        "po_knowledge_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("program_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.program_outcomes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("knowledge_profile_id", UUID(as_uuid=True), sa.ForeignKey("config.knowledge_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("program_outcome_id", "knowledge_profile_id", name="uq_obe_po_kp"),
        schema="obe",
    )
    op.create_index("ix_obe_po_knowledge_profiles_program_outcome_id", "po_knowledge_profiles", ["program_outcome_id"], schema="obe")

    # ── obe.course_outcomes ───────────────────────────────────────────────────
    op.create_table(
        "course_outcomes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("curriculum_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.curricula.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.courses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("bloom_level_id", UUID(as_uuid=True), sa.ForeignKey("config.bloom_levels.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("curriculum_id", "course_id", "code", name="uq_obe_co_curriculum_course_code"),
        schema="obe",
    )
    op.create_index("ix_obe_course_outcomes_organization_id", "course_outcomes", ["organization_id"], schema="obe")
    op.create_index("ix_obe_course_outcomes_curriculum_id", "course_outcomes", ["curriculum_id"], schema="obe")
    op.create_index("ix_obe_course_outcomes_course_id", "course_outcomes", ["course_id"], schema="obe")
    op.create_index("ix_obe_co_curriculum_course_status", "course_outcomes", ["curriculum_id", "course_id", "status"], schema="obe")

    # ── obe.co_delivery_methods ───────────────────────────────────────────────
    op.create_table(
        "co_delivery_methods",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("course_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("delivery_method_id", UUID(as_uuid=True), sa.ForeignKey("config.delivery_methods.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("course_outcome_id", "delivery_method_id", name="uq_obe_co_dm"),
        schema="obe",
    )
    op.create_index("ix_obe_co_delivery_methods_course_outcome_id", "co_delivery_methods", ["course_outcome_id"], schema="obe")

    # ── obe.co_po_mapping_sets ────────────────────────────────────────────────
    op.create_table(
        "co_po_mapping_sets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("curriculum_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.curricula.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.courses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("curriculum_id", "course_id", name="uq_obe_co_po_mapping_set_curriculum_course"),
        schema="obe",
    )
    op.create_index("ix_obe_co_po_mapping_sets_organization_id", "co_po_mapping_sets", ["organization_id"], schema="obe")
    op.create_index("ix_obe_co_po_mapping_sets_curriculum_id", "co_po_mapping_sets", ["curriculum_id"], schema="obe")
    op.create_index("ix_obe_co_po_mapping_sets_course_id", "co_po_mapping_sets", ["course_id"], schema="obe")

    # ── obe.co_po_mapping_entries ─────────────────────────────────────────────
    op.create_table(
        "co_po_mapping_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mapping_set_id", UUID(as_uuid=True), sa.ForeignKey("obe.co_po_mapping_sets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("program_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.program_outcomes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("weight", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("mapping_set_id", "course_outcome_id", "program_outcome_id", name="uq_obe_co_po_mapping_entry"),
        sa.CheckConstraint("weight IN (1, 2, 3)", name="ck_obe_co_po_mapping_entry_weight"),
        schema="obe",
    )
    op.create_index("ix_obe_co_po_mapping_entries_mapping_set_id", "co_po_mapping_entries", ["mapping_set_id"], schema="obe")
    op.create_index("ix_obe_co_po_mapping_entries_course_outcome_id", "co_po_mapping_entries", ["course_outcome_id"], schema="obe")
    op.create_index("ix_obe_co_po_mapping_entries_program_outcome_id", "co_po_mapping_entries", ["program_outcome_id"], schema="obe")

    # ── obe.co_cp_mappings ────────────────────────────────────────────────────
    op.create_table(
        "co_cp_mappings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("complex_problem_id", UUID(as_uuid=True), sa.ForeignKey("config.complex_problems.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("course_outcome_id", "complex_problem_id", name="uq_obe_co_cp"),
        schema="obe",
    )
    op.create_index("ix_obe_co_cp_mappings_course_outcome_id", "co_cp_mappings", ["course_outcome_id"], schema="obe")

    # ── obe.co_ca_mappings ────────────────────────────────────────────────────
    op.create_table(
        "co_ca_mappings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("complex_activity_id", UUID(as_uuid=True), sa.ForeignKey("config.complex_activities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("course_outcome_id", "complex_activity_id", name="uq_obe_co_ca"),
        schema="obe",
    )
    op.create_index("ix_obe_co_ca_mappings_course_outcome_id", "co_ca_mappings", ["course_outcome_id"], schema="obe")

    # ── obe.co_kp_mappings ────────────────────────────────────────────────────
    op.create_table(
        "co_kp_mappings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_outcome_id", UUID(as_uuid=True), sa.ForeignKey("obe.course_outcomes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("knowledge_profile_id", UUID(as_uuid=True), sa.ForeignKey("config.knowledge_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("course_outcome_id", "knowledge_profile_id", name="uq_obe_co_kp"),
        schema="obe",
    )
    op.create_index("ix_obe_co_kp_mappings_course_outcome_id", "co_kp_mappings", ["course_outcome_id"], schema="obe")


def downgrade() -> None:
    op.drop_table("co_kp_mappings", schema="obe")
    op.drop_table("co_ca_mappings", schema="obe")
    op.drop_table("co_cp_mappings", schema="obe")
    op.drop_table("co_po_mapping_entries", schema="obe")
    op.drop_table("co_po_mapping_sets", schema="obe")
    op.drop_table("co_delivery_methods", schema="obe")
    op.drop_table("course_outcomes", schema="obe")
    op.drop_table("po_knowledge_profiles", schema="obe")
    op.drop_table("program_outcomes", schema="obe")
