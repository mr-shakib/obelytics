"""MCP endpoint: JSON-RPC handshake, tool list, permission-checked read-only tool calls."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from tests.integration.test_outcome_authoring import _scenario

URL = "/api/v1/mcp"


def _rpc(method: str, params: dict | None = None, msg_id: int | None = 1) -> dict:
    message = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    if msg_id is not None:
        message["id"] = msg_id
    return message


@pytest.mark.asyncio
async def test_handshake_lists_read_only_tools(client: AsyncClient, auth_headers: dict):
    resp = await client.post(URL, headers=auth_headers, json=_rpc("initialize", {
        "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"},
    }))
    body = resp.json()["result"]
    assert body["protocolVersion"] == "2025-06-18" and body["serverInfo"]["name"] == "obelytics"
    assert body["capabilities"] == {"tools": {"listChanged": False}}

    resp = await client.post(URL, headers=auth_headers, json=_rpc("notifications/initialized", msg_id=None))
    assert resp.status_code == 202

    tools = (await client.post(URL, headers=auth_headers, json=_rpc("tools/list"))).json()["result"]["tools"]
    names = {t["name"] for t in tools}
    assert {"section_attainment", "paper_audit", "skill_coverage", "search_accreditation_documents"} <= names
    assert all(t["annotations"]["readOnlyHint"] for t in tools)


@pytest.mark.asyncio
async def test_tool_calls_run_as_the_caller(
    client: AsyncClient, auth_headers: dict, teacher_auth_headers: dict, db_session: AsyncSession
):
    s = await _scenario(db_session)
    resp = await client.post(URL, headers=auth_headers, json=_rpc("tools/call", {
        "name": "program_outcome_map", "arguments": {"curriculum_id": s["curriculum_id"]},
    }))
    result = resp.json()["result"]
    assert result["isError"] is False
    assert any(po["po"] == "PO1" for po in result["structuredContent"]["program_outcomes"])

    resp = await client.post(URL, headers=auth_headers, json=_rpc("tools/call", {
        "name": "skill_coverage", "arguments": {"curriculum_id": "not-an-id"},
    }))
    assert resp.json()["result"]["isError"] is True

    resp = await client.post(URL, headers=auth_headers, json=_rpc("tools/call", {"name": "drop_tables"}))
    assert resp.json()["error"]["code"] == -32602

    # A section teacher lacks the accreditation permission: a tool error, not a crash.
    resp = await client.post(URL, headers=teacher_auth_headers, json=_rpc("tools/call", {
        "name": "search_accreditation_documents", "arguments": {"query": "program outcomes"},
    }))
    result = resp.json()["result"]
    assert result["isError"] is True and "accreditation.read" in result["structuredContent"]["error"]

    calls = (await db_session.execute(select(AuditLog).where(AuditLog.action == "MCP_TOOL_CALL"))).scalars().all()
    assert len(calls) >= 3


@pytest.mark.asyncio
async def test_unknown_method_and_missing_token(client: AsyncClient, auth_headers: dict):
    resp = await client.post(URL, headers=auth_headers, json=_rpc("resources/list"))
    assert resp.json()["error"]["code"] == -32601
    resp = await client.post(URL, json=_rpc("tools/list"))
    assert resp.status_code in (401, 403)
