"""Create curriculum schema tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── curriculum.curricula ──────────────────────────────────────────────────
    op.create_table(
        "curricula",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("program_id", UUID(as_uuid=True), sa.ForeignKey("org.programs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("effective_year", sa.SmallInteger(), nullable=False),
        sa.Column("version_number", sa.SmallInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column("parent_curriculum_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("program_id", "code", "version_number", name="uq_curriculum_program_code_version"),
        schema="curriculum",
    )
    op.create_index("ix_curriculum_curricula_program_id", "curricula", ["program_id"], schema="curriculum")
    # Self-referential FK added after table creation
    op.create_foreign_key(
        "fk_curriculum_curricula_parent",
        "curricula", "curricula",
        ["parent_curriculum_id"], ["id"],
        source_schema="curriculum", referent_schema="curriculum",
        ondelete="RESTRICT",
    )

    # ── curriculum.curriculum_term_definitions ────────────────────────────────
    op.create_table(
        "curriculum_term_definitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("curriculum_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.curricula.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("term_number", sa.SmallInteger(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("total_credit_hours", sa.SmallInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("curriculum_id", "term_number", name="uq_curriculum_term_def_curriculum_term"),
        schema="curriculum",
    )
    op.create_index("ix_curriculum_curriculum_term_definitions_curriculum_id", "curriculum_term_definitions", ["curriculum_id"], schema="curriculum")

    # ── curriculum.courses ────────────────────────────────────────────────────
    op.create_table(
        "courses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_type_id", UUID(as_uuid=True), sa.ForeignKey("config.course_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("credits", sa.SmallInteger(), nullable=False),
        sa.Column("theory_hours", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("lab_hours", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="curriculum",
    )
    op.create_index("ix_curriculum_courses_organization_id", "courses", ["organization_id"], schema="curriculum")
    op.create_index(
        "uq_curriculum_course_org_code_active",
        "courses",
        ["organization_id", "code"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        schema="curriculum",
    )

    # ── curriculum.curriculum_course_slots ────────────────────────────────────
    op.create_table(
        "curriculum_course_slots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("curriculum_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.curricula.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("curriculum_term_definition_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.curriculum_term_definitions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.courses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_elective", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("curriculum_id", "course_id", name="uq_curriculum_course_slot_curriculum_course"),
        schema="curriculum",
    )
    op.create_index("ix_curriculum_curriculum_course_slots_curriculum_id", "curriculum_course_slots", ["curriculum_id"], schema="curriculum")
    op.create_index("ix_curriculum_curriculum_course_slots_course_id", "curriculum_course_slots", ["course_id"], schema="curriculum")

    # ── curriculum.course_prerequisites ──────────────────────────────────────
    op.create_table(
        "course_prerequisites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.courses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("prerequisite_course_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.courses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("course_id", "prerequisite_course_id", name="uq_curriculum_course_prereq"),
        sa.CheckConstraint("course_id != prerequisite_course_id", name="ck_curriculum_prereq_no_self"),
        schema="curriculum",
    )
    op.create_index("ix_curriculum_course_prerequisites_course_id", "course_prerequisites", ["course_id"], schema="curriculum")

    # ── curriculum.batches ────────────────────────────────────────────────────
    op.create_table(
        "batches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("curriculum_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.curricula.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("intake_year", sa.SmallInteger(), nullable=False),
        sa.Column("graduation_year", sa.SmallInteger(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("curriculum_id", "name", name="uq_curriculum_batch_curriculum_name"),
        schema="curriculum",
    )
    op.create_index("ix_curriculum_batches_organization_id", "batches", ["organization_id"], schema="curriculum")
    op.create_index("ix_curriculum_batches_curriculum_id", "batches", ["curriculum_id"], schema="curriculum")

    # ── curriculum.academic_terms ─────────────────────────────────────────────
    op.create_table(
        "academic_terms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("season", sa.String(20), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="UPCOMING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "year", "season", name="uq_curriculum_academic_term_org_year_season"),
        schema="curriculum",
    )
    op.create_index("ix_curriculum_academic_terms_organization_id", "academic_terms", ["organization_id"], schema="curriculum")

    # ── curriculum.sections ───────────────────────────────────────────────────
    op.create_table(
        "sections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("capacity", sa.SmallInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "name", name="uq_curriculum_section_org_name"),
        schema="curriculum",
    )

    # ── curriculum.section_offerings ──────────────────────────────────────────
    op.create_table(
        "section_offerings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("curriculum_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.curricula.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("batch_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.batches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.courses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("academic_term_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.academic_terms.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("section_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.sections.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="UPCOMING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "batch_id", "course_id", "academic_term_id", "section_id",
            name="uq_curriculum_section_offering_batch_course_term_section",
        ),
        schema="curriculum",
    )
    op.create_index("ix_curriculum_section_offerings_organization_id", "section_offerings", ["organization_id"], schema="curriculum")
    op.create_index("ix_curriculum_section_offerings_batch_id", "section_offerings", ["batch_id"], schema="curriculum")
    op.create_index("ix_curriculum_section_offerings_course_id", "section_offerings", ["course_id"], schema="curriculum")
    op.create_index("ix_curriculum_section_offerings_academic_term_id", "section_offerings", ["academic_term_id"], schema="curriculum")

    # ── curriculum.faculty_assignments ────────────────────────────────────────
    op.create_table(
        "faculty_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("section_offering_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.section_offerings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role_in_course", sa.String(30), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        schema="curriculum",
    )
    op.create_index("ix_curriculum_faculty_assignments_section_offering_id", "faculty_assignments", ["section_offering_id"], schema="curriculum")
    op.create_index(
        "uq_curriculum_faculty_assignment_active",
        "faculty_assignments",
        ["section_offering_id", "user_id", "role_in_course"],
        unique=True,
        postgresql_where=sa.text("removed_at IS NULL"),
        schema="curriculum",
    )


def downgrade() -> None:
    op.drop_table("faculty_assignments", schema="curriculum")
    op.drop_table("section_offerings", schema="curriculum")
    op.drop_table("sections", schema="curriculum")
    op.drop_table("academic_terms", schema="curriculum")
    op.drop_table("batches", schema="curriculum")
    op.drop_table("course_prerequisites", schema="curriculum")
    op.drop_table("curriculum_course_slots", schema="curriculum")
    op.drop_table("courses", schema="curriculum")
    op.drop_table("curriculum_term_definitions", schema="curriculum")
    op.drop_constraint("fk_curriculum_curricula_parent", "curricula", schema="curriculum", type_="foreignkey")
    op.drop_table("curricula", schema="curriculum")
