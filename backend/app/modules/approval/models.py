import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class ReviewComment(Base):
    __tablename__ = "review_comments"
    __table_args__ = (
        Index("ix_approval_review_comment_entity", "entity_type", "entity_id"),
        {"schema": "approval"},
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    organization_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("org.organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(PGUUID(as_uuid=True), nullable=False)
    # Plain UUID — no FK constraint (cross-schema IAM)
    author_user_id = Column(PGUUID(as_uuid=True), nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
