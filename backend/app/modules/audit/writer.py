import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog


def write_audit_log(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: UUID,
    action: str,
    org_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    before_status: str | None = None,
    after_status: str | None = None,
    extra: dict | None = None,
) -> AuditLog:
    """Write an audit log entry. Caller must flush/commit the session."""
    entry = AuditLog(
        organization_id=org_id,
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before_status=before_status,
        after_status=after_status,
        extra=json.dumps(extra, default=str) if extra else None,
    )
    session.add(entry)
    return entry
