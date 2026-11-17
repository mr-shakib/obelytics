"""
Workforce readiness — do the program's outcomes cover what employers ask for?

MarketPosting  — one job description a program collects (pasted from an employer or a
                 job board), with the skills the AI read from it.
MarketAnalysis — one comparison of the postings' skills with a curriculum's course
                 outcomes: which skills are covered, partly covered or missing, by
                 which COs (and, through CO-PO mapping, which POs).

Postings hold no student data. Analyses are advisory: they change no outcome or mapping;
a gap becomes a CO only when a teacher accepts a drafted one.
"""
import sqlalchemy as sa
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class MarketPosting(Base):
    __tablename__ = "market_postings"
    __table_args__ = ({"schema": "obe"},)

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    employer = Column(String(255), nullable=True)
    source = Column(String(500), nullable=True)
    posted_on = Column(Date, nullable=True)
    text = Column(Text, nullable=False)
    # [{"name": "SQL", "category": "technical", "required": true}, ...]; NULL until read.
    skills = Column(JSONB, nullable=True)
    skills_model = Column(String(100), nullable=True)
    skills_prompt_version = Column(String(50), nullable=True)
    # Plain UUID — no FK constraint (cross-schema IAM)
    created_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


class MarketAnalysis(Base):
    __tablename__ = "market_analyses"
    __table_args__ = ({"schema": "obe"},)

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.programs.id", ondelete="CASCADE"),
        nullable=False,
    )
    curriculum_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.curricula.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    posting_count = Column(Integer, nullable=False)
    result = Column(JSONB, nullable=False)
    provider = Column(String(10), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_version = Column(String(50), nullable=False)
    created_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
