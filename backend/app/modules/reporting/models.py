import sqlalchemy as sa
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID

from app.core.database import Base


class ReportRun(Base):
    __tablename__ = "report_runs"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING','RUNNING','DONE','FAILED')", name="chk_report_run_status"),
        Index("ix_reporting_report_runs_org_user", "organization_id", "requested_by_user_id"),
        {"schema": "reporting"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    definition_id = Column(String(50), nullable=False)
    definition_name = Column(String(255), nullable=False)
    # user_id stored without ORM FK — avoids cross-schema model coupling with IAM
    requested_by_user_id = Column(PGUUID(as_uuid=True), nullable=False)
    status = Column(String(20), nullable=False, server_default="PENDING")
    params = Column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    summary = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    output_file_key = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    completed_at = Column(DateTime(timezone=True), nullable=True)
