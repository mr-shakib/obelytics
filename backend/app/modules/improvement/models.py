"""
ImprovementPlan — what the improvement agent found for one section and what it proposes.

The agent works through fixed, read-only tools (CO attainment, per-question statistics,
the lesson plan, the course's previous plan). Every tool call, the evidence it cites and
the model and prompt version are kept, so a plan can be traced back to the numbers.
Plans are advisory: they change no marks, attainment or outcomes. Teachers accept or
reject each proposed intervention; the next plan for the course checks what happened.
"""
import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class ImprovementPlan(Base):
    __tablename__ = "improvement_plans"
    __table_args__ = ({"schema": "cqi"},)

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_offering_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.section_offerings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # For finding the course's earlier plans in other sections and terms.
    course_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("curriculum.courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary = Column(Text, nullable=False)
    follow_up = Column(Text, nullable=True)
    # [{"id": "d1", "co": "CO2", "problem": …, "evidence": [{…, "verified": bool}], "interventions": […]}]
    diagnoses = Column(JSONB, nullable=False)
    # Every step of the agent: its reasoning, the tool it called and what the tool returned.
    steps = Column(JSONB, nullable=False)
    # {"d1-i1": {"decision": "ACCEPTED", "note": …, "by": …, "at": …}}
    decisions = Column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    provider = Column(String(10), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_version = Column(String(50), nullable=False)
    # Plain UUID — no FK constraint (cross-schema IAM)
    created_by_user_id = Column(PGUUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
