"""Accreditation evidence writer: reference documents with full-text search, and drafts

Revision ID: 0063_evidence_writer
Revises: 0062_improvement_agent
Create Date: 2026-11-17 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0063_evidence_writer"
down_revision: Union[str, None] = "0062_improvement_agent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UUID = sa.dialects.postgresql.UUID(as_uuid=True)
_JSONB = sa.dialects.postgresql.JSONB()
_TS = sa.dialects.postgresql.TSVECTOR()


def upgrade() -> None:
    op.create_table(
        "reference_documents",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", _UUID, sa.ForeignKey("org.organizations.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("passage_count", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", _UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="accreditation",
    )
    op.create_index("ix_accreditation_reference_documents_organization_id", "reference_documents",
                    ["organization_id"], schema="accreditation")

    op.create_table(
        "reference_passages",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", _UUID, sa.ForeignKey("org.organizations.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("document_id", _UUID,
                  sa.ForeignKey("accreditation.reference_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(500), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("tsv", _TS, sa.Computed(
            "to_tsvector('english', coalesce(heading, '') || ' ' || text)", persisted=True,
        )),
        schema="accreditation",
    )
    for column in ("organization_id", "document_id"):
        op.create_index(f"ix_accreditation_reference_passages_{column}", "reference_passages", [column],
                        schema="accreditation")
    op.create_index("ix_accreditation_reference_passages_tsv", "reference_passages", ["tsv"],
                    schema="accreditation", postgresql_using="gin")

    op.create_table(
        "evidence_drafts",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", _UUID, sa.ForeignKey("org.organizations.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("program_id", _UUID, sa.ForeignKey("org.programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("curriculum_id", _UUID, sa.ForeignKey("curriculum.curricula.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("criterion_title", sa.String(255), nullable=False),
        sa.Column("criterion_guidance", sa.Text(), nullable=True),
        sa.Column("sentences", _JSONB, nullable=False),
        sa.Column("missing", _JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("sources", _JSONB, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'DRAFT'")),
        sa.Column("edited_text", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(10), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("created_by_user_id", _UUID, nullable=True),
        sa.Column("decided_by_user_id", _UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('DRAFT','ACCEPTED','REJECTED')", name="chk_evidence_drafts_status"),
        schema="accreditation",
    )
    for column in ("organization_id", "program_id"):
        op.create_index(f"ix_accreditation_evidence_drafts_{column}", "evidence_drafts", [column],
                        schema="accreditation")


def downgrade() -> None:
    for column in ("organization_id", "program_id"):
        op.drop_index(f"ix_accreditation_evidence_drafts_{column}", table_name="evidence_drafts",
                      schema="accreditation")
    op.drop_table("evidence_drafts", schema="accreditation")
    op.drop_index("ix_accreditation_reference_passages_tsv", table_name="reference_passages", schema="accreditation")
    for column in ("organization_id", "document_id"):
        op.drop_index(f"ix_accreditation_reference_passages_{column}", table_name="reference_passages",
                      schema="accreditation")
    op.drop_table("reference_passages", schema="accreditation")
    op.drop_index("ix_accreditation_reference_documents_organization_id", table_name="reference_documents",
                  schema="accreditation")
    op.drop_table("reference_documents", schema="accreditation")
