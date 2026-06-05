import sqlalchemy as sa
from sqlalchemy import Boolean, Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notification_recipient", "recipient_user_id", "is_read"),
        {"schema": "notification"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    recipient_user_id = Column(PGUUID(as_uuid=True), nullable=False)  # plain, no FK
    notification_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(PGUUID(as_uuid=True), nullable=True)
    is_read = Column(Boolean, nullable=False, server_default=sa.text("FALSE"))
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    read_at = Column(DateTime(timezone=True), nullable=True)
