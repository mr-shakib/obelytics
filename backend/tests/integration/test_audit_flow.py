"""Integration tests for Audit module endpoints."""
import uuid
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.writer import write_audit_log


# ── Setup helpers ─────────────────────────────────────────────────────────────

async def _write_test_audit_log(
    client: AsyncClient, headers: dict, db_session: AsyncSession
) -> str:
    """Write an audit log entry directly for the authenticated user's org.

    Returns the entity_id used, so tests can filter for it.
    """
    me_resp = await client.get("/api/v1/users/me", headers=headers)
    assert me_resp.status_code == 200, me_resp.text
    me = me_resp.json()

    entity_id = uuid.uuid4()
    write_audit_log(
        db_session,
        entity_type="test_entity",
        entity_id=entity_id,
        action="TEST_ACTION",
        org_id=UUID(me["organization_id"]),
        actor_user_id=UUID(me["id"]),
        before_status="BEFORE",
        after_status="AFTER",
    )
    await db_session.commit()
    return str(entity_id)


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log_entity_filter(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """GET /audit/logs filtered by entity returns the matching entries."""
    entity_id = await _write_test_audit_log(client, auth_headers, db_session)

    audit_resp = await client.get(
        f"/api/v1/audit/logs/test_entity/{entity_id}",
        headers=auth_headers,
    )
    assert audit_resp.status_code == 200, audit_resp.text
    logs = audit_resp.json()
    assert len(logs) >= 1
    entry = next(l for l in logs if l["action"] == "TEST_ACTION")
    assert entry["entity_type"] == "test_entity"
    assert entry["entity_id"] == entity_id


@pytest.mark.asyncio
async def test_audit_log_org_wide(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """GET /audit/logs without entity_id returns org-wide logs."""
    await _write_test_audit_log(client, auth_headers, db_session)

    resp = await client.get("/api/v1/audit/logs", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data["items"], list)
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_audit_log_requires_permission(
    client: AsyncClient, teacher_auth_headers: dict
):
    """Section Teacher (no system.audit.read) gets 403."""
    resp = await client.get("/api/v1/audit/logs", headers=teacher_auth_headers)
    assert resp.status_code == 403, resp.text
