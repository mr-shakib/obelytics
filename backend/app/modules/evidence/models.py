"""
Accreditation evidence writer — the documents it retrieves from and the drafts it writes.

ReferenceDocument / ReferencePassage: documents an institution uploads (its accreditor's
manual, self-assessment templates), split into passages and indexed for full-text search.
EvidenceDraft: one AI-drafted report section. Every sentence cites the program records
and manual passages it rests on; the sources given to the model are kept with the draft,
so each sentence can be traced and re-checked. Advisory: nothing is submitted anywhere.
"""
import sqlalchemy as sa
from sqlalchemy import Column, Computed, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class ReferenceDocument(Base):
    __tablename__ = "reference_documents"
    __table_args__ = ({"schema": "accreditation"},)

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True), ForeignKey("org.organizations.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    sha256 = Column(String(64), nullable=False)
    passage_count = Column(Integer, nullable=False)
    # Plain UUID — no FK constraint (cross-schema IAM)
    created_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class ReferencePassage(Base):
    __tablename__ = "reference_passages"
    __table_args__ = (
        sa.Index("ix_accreditation_reference_passages_tsv", "tsv", postgresql_using="gin"),
        {"schema": "accreditation"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True), ForeignKey("org.organizations.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    document_id = Column(
        PGUUID(as_uuid=True), ForeignKey("accreditation.reference_documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    ordinal = Column(Integer, nullable=False)
    heading = Column(String(500), nullable=True)
    text = Column(Text, nullable=False)
    tsv = Column(
        TSVECTOR,
        Computed("to_tsvector('english', coalesce(heading, '') || ' ' || text)", persisted=True),
    )


class EvidenceDraft(Base):
    __tablename__ = "evidence_drafts"
    __table_args__ = ({"schema": "accreditation"},)

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True), ForeignKey("org.organizations.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    program_id = Column(
        PGUUID(as_uuid=True), ForeignKey("org.programs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    curriculum_id = Column(
        PGUUID(as_uuid=True), ForeignKey("curriculum.curricula.id", ondelete="CASCADE"), nullable=False,
    )
    criterion_title = Column(String(255), nullable=False)
    criterion_guidance = Column(Text, nullable=True)
    # [{"text", "cites": ["E3", "M1"], "gap": bool, "status": "supported"|"check", "issues": [...]}]
    sentences = Column(JSONB, nullable=False)
    # Evidence the program should still collect, as the model listed it.
    missing = Column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))
    # {"E1": {"kind", "label", "text"}, "M1": {"kind": "manual", "label", "text", "document_id"}}
    sources = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False, server_default=sa.text("'DRAFT'"))
    edited_text = Column(Text, nullable=True)
    provider = Column(String(10), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_version = Column(String(50), nullable=False)
    created_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    decided_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    decided_at = Column(DateTime(timezone=True), nullable=True)
