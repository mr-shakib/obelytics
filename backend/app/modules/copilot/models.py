import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class CopilotConversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_copilot_conversations_owner", "organization_id", "user_id", "updated_at"),
        {"schema": "copilot"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("iam.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(255), nullable=False, server_default="New conversation")
    status = Column(String(20), nullable=False, server_default="ACTIVE")
    context = Column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )
    last_message_at = Column(DateTime(timezone=True), nullable=True)

    messages = relationship(
        "CopilotMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="raise",
    )


class CopilotMessage(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_copilot_messages_conversation_created", "conversation_id", "created_at"),
        {"schema": "copilot"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    conversation_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("copilot.conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False, server_default="")
    status = Column(String(20), nullable=False, server_default="COMPLETE")
    model = Column(String(100), nullable=True)
    token_usage = Column(JSONB, nullable=True)
    tool_calls = Column(JSONB, nullable=True)
    citations = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    conversation = relationship("CopilotConversation", back_populates="messages", lazy="raise")
