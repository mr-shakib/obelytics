import json
from uuid import UUID
from sqlalchemy import Column, DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from app.core.database import Base


class OutboxEvent(Base):
    __tablename__ = "domain_events"
    __table_args__ = {"schema": "events"}

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    event_type = Column(String(255), nullable=False, index=True)
    aggregate_type = Column(String(100), nullable=False)
    aggregate_id = Column(PGUUID(as_uuid=True), nullable=True)
    payload = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, server_default="PENDING", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    processed_at = Column(DateTime(timezone=True), nullable=True)


def write_outbox(
    session,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID | None,
    payload: dict,
) -> OutboxEvent:
    entry = OutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=json.dumps(payload, default=str),
    )
    session.add(entry)
    return entry
