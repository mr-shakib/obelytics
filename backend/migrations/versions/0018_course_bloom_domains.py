"""Seed Affective/Psychomotor Bloom domains and add curriculum.course_bloom_domains

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Seed Affective and Psychomotor Bloom domains for every existing org ───
    op.execute(
        """
        INSERT INTO config.bloom_domains (id, organization_id, name, description, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), o.id, d.name, d.description, true, now(), now()
        FROM org.organizations o
        CROSS JOIN (VALUES
            ('Affective', 'Bloom''s Taxonomy Affective Domain'),
            ('Psychomotor', 'Bloom''s Taxonomy Psychomotor Domain')
        ) AS d(name, description)
        WHERE NOT EXISTS (
            SELECT 1 FROM config.bloom_domains bd
            WHERE bd.organization_id = o.id AND bd.name = d.name
        )
        """
    )

    # ── Seed their levels ──────────────────────────────────────────────────────
    op.execute(
        """
        INSERT INTO config.bloom_levels (id, organization_id, bloom_domain_id, code, name, order_index, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), bd.organization_id, bd.id, l.code, l.name, l.order_index, true, now(), now()
        FROM config.bloom_domains bd
        CROSS JOIN (VALUES
            ('Affective', 'A1', 'Receiving', 1),
            ('Affective', 'A2', 'Responding', 2),
            ('Affective', 'A3', 'Valuing', 3),
            ('Affective', 'A4', 'Organizing', 4),
            ('Affective', 'A5', 'Characterizing', 5),
            ('Psychomotor', 'P1', 'Imitation', 1),
            ('Psychomotor', 'P2', 'Manipulation', 2),
            ('Psychomotor', 'P3', 'Precision', 3),
            ('Psychomotor', 'P4', 'Articulation', 4),
            ('Psychomotor', 'P5', 'Naturalization', 5)
        ) AS l(domain_name, code, name, order_index)
        WHERE bd.name = l.domain_name
          AND NOT EXISTS (
            SELECT 1 FROM config.bloom_levels lvl
            WHERE lvl.organization_id = bd.organization_id
              AND lvl.bloom_domain_id = bd.id
              AND lvl.code = l.code
          )
        """
    )

    # ── curriculum.course_bloom_domains ────────────────────────────────────────
    op.create_table(
        "course_bloom_domains",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("curriculum.courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bloom_domain_id", UUID(as_uuid=True), sa.ForeignKey("config.bloom_domains.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("course_id", "bloom_domain_id", name="uq_curriculum_course_bloom_domain"),
        schema="curriculum",
    )
    op.create_index(
        "ix_curriculum_course_bloom_domains_course_id",
        "course_bloom_domains",
        ["course_id"],
        schema="curriculum",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_curriculum_course_bloom_domains_course_id",
        table_name="course_bloom_domains",
        schema="curriculum",
    )
    op.drop_table("course_bloom_domains", schema="curriculum")

    # Note: seeded Affective/Psychomotor Bloom domains/levels are intentionally
    # left in place — they may already be referenced by course outcomes.
