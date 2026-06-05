import sqlalchemy as sa
from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
        Index("ix_audit_log_actor", "actor_user_id"),
        {"schema": "audit"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    actor_user_id = Column(PGUUID(as_uuid=True), nullable=True)  # plain, no FK
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(PGUUID(as_uuid=True), nullable=False)
    action = Column(String(50), nullable=False)
    before_status = Column(String(30), nullable=True)
    after_status = Column(String(30), nullable=True)
    extra = Column(Text, nullable=True)  # JSON string for extra context
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
