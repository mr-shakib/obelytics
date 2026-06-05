"""Create org and config (reference data) tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── org.organizations ─────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("short_name", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("vision", sa.Text(), nullable=True),
        sa.Column("mission", sa.Text(), nullable=True),
        sa.Column("logo_file_key", sa.String(500), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("address_street", sa.String(255), nullable=True),
        sa.Column("address_city", sa.String(100), nullable=True),
        sa.Column("address_country", sa.String(100), nullable=True),
        sa.Column("address_postal_code", sa.String(20), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("email_validation_regex", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="org",
    )

    # ── org.departments ───────────────────────────────────────────────────────
    op.create_table(
        "departments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("short_name", sa.String(30), nullable=False),
        sa.Column("year_established", sa.SmallInteger(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("vision", sa.Text(), nullable=True),
        sa.Column("mission", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="org",
    )
    op.create_index("ix_org_departments_organization_id", "departments", ["organization_id"], schema="org")
    op.create_index(
        "uq_org_dept_short_name_active",
        "departments",
        ["organization_id", "short_name"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        schema="org",
    )

    # ── org.department_head_history ───────────────────────────────────────────
    op.create_table(
        "department_head_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("department_id", UUID(as_uuid=True), sa.ForeignKey("org.departments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="org",
    )
    op.create_index("ix_org_department_head_history_department_id", "department_head_history", ["department_id"], schema="org")
    op.create_index(
        "uq_org_dept_current_hod",
        "department_head_history",
        ["department_id"],
        unique=True,
        postgresql_where=sa.text("effective_to IS NULL"),
        schema="org",
    )

    # ── org.programs ──────────────────────────────────────────────────────────
    op.create_table(
        "programs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("department_id", UUID(as_uuid=True), sa.ForeignKey("org.departments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("acronym", sa.String(20), nullable=False),
        sa.Column("program_type", sa.String(20), nullable=False),
        sa.Column("minimum_duration_semesters", sa.SmallInteger(), nullable=False),
        sa.Column("total_credits", sa.SmallInteger(), nullable=False),
        sa.Column("study_mode", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="org",
    )
    op.create_index("ix_org_programs_organization_id", "programs", ["organization_id"], schema="org")
    op.create_index("ix_org_programs_department_id", "programs", ["department_id"], schema="org")
    op.create_index(
        "uq_org_program_acronym_active",
        "programs",
        ["organization_id", "acronym"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        schema="org",
    )

    # ── config.bloom_domains ──────────────────────────────────────────────────
    op.create_table(
        "bloom_domains",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "name", name="uq_config_bloom_domain_org_name"),
        schema="config",
    )
    op.create_index("ix_config_bloom_domains_organization_id", "bloom_domains", ["organization_id"], schema="config")

    # ── config.bloom_levels ───────────────────────────────────────────────────
    op.create_table(
        "bloom_levels",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("bloom_domain_id", UUID(as_uuid=True), sa.ForeignKey("config.bloom_domains.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("order_index", sa.SmallInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "bloom_domain_id", "code", name="uq_config_bloom_level_org_domain_code"),
        schema="config",
    )
    op.create_index("ix_config_bloom_levels_organization_id", "bloom_levels", ["organization_id"], schema="config")
    op.create_index("ix_config_bloom_levels_bloom_domain_id", "bloom_levels", ["bloom_domain_id"], schema="config")

    # ── config.delivery_methods ───────────────────────────────────────────────
    op.create_table(
        "delivery_methods",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "name", name="uq_config_delivery_method_org_name"),
        schema="config",
    )
    op.create_index("ix_config_delivery_methods_organization_id", "delivery_methods", ["organization_id"], schema="config")

    # ── config.course_types ───────────────────────────────────────────────────
    op.create_table(
        "course_types",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "name", name="uq_config_course_type_org_name"),
        schema="config",
    )
    op.create_index("ix_config_course_types_organization_id", "course_types", ["organization_id"], schema="config")

    # ── config.assessment_types ───────────────────────────────────────────────
    op.create_table(
        "assessment_types",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_sessional", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "name", name="uq_config_assessment_type_org_name"),
        schema="config",
    )
    op.create_index("ix_config_assessment_types_organization_id", "assessment_types", ["organization_id"], schema="config")

    # ── config.complex_problems ───────────────────────────────────────────────
    op.create_table(
        "complex_problems",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "code", name="uq_config_complex_problem_org_code"),
        schema="config",
    )
    op.create_index("ix_config_complex_problems_organization_id", "complex_problems", ["organization_id"], schema="config")

    # ── config.complex_activities ─────────────────────────────────────────────
    op.create_table(
        "complex_activities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "code", name="uq_config_complex_activity_org_code"),
        schema="config",
    )
    op.create_index("ix_config_complex_activities_organization_id", "complex_activities", ["organization_id"], schema="config")

    # ── config.knowledge_profiles ─────────────────────────────────────────────
    op.create_table(
        "knowledge_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "code", name="uq_config_knowledge_profile_org_code"),
        schema="config",
    )
    op.create_index("ix_config_knowledge_profiles_organization_id", "knowledge_profiles", ["organization_id"], schema="config")

    # ── config.mapping_weight_labels ──────────────────────────────────────────
    op.create_table(
        "mapping_weight_labels",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("weight_value", sa.SmallInteger(), nullable=False),
        sa.Column("label", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "weight_value", name="uq_config_mapping_weight_org_value"),
        sa.CheckConstraint("weight_value IN (1, 2, 3)", name="ck_config_mapping_weight_valid"),
        schema="config",
    )
    op.create_index("ix_config_mapping_weight_labels_organization_id", "mapping_weight_labels", ["organization_id"], schema="config")


def downgrade() -> None:
    op.drop_table("mapping_weight_labels", schema="config")
    op.drop_table("knowledge_profiles", schema="config")
    op.drop_table("complex_activities", schema="config")
    op.drop_table("complex_problems", schema="config")
    op.drop_table("assessment_types", schema="config")
    op.drop_table("course_types", schema="config")
    op.drop_table("delivery_methods", schema="config")
    op.drop_table("bloom_levels", schema="config")
    op.drop_table("bloom_domains", schema="config")
    op.drop_table("programs", schema="org")
    op.drop_table("department_head_history", schema="org")
    op.drop_table("departments", schema="org")
    op.drop_table("organizations", schema="org")
