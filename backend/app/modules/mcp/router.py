"""
Model Context Protocol endpoint (Streamable HTTP transport, JSON responses).

An MCP client posts JSON-RPC 2.0 messages to POST /api/v1/mcp with the user's bearer
token. Supported: initialize, notifications/initialized, ping, tools/list, tools/call.
Every call runs as the signed-in user, under their permissions and organization.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_permission_manifest
from app.modules.audit.writer import write_audit_log
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.mcp.tools import TOOLS, TOOLS_BY_NAME, Context, ToolError

router = APIRouter(prefix="/mcp", tags=["MCP"])

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
SERVER_INFO = {"name": "obelytics", "title": "Obelytics OBE tools", "version": "1.0.0"}
INSTRUCTIONS = (
    "Read-only tools over a university's outcome-based education records: course-outcome "
    "attainment (official and audit-supported), exam-paper audits, job-market skill coverage, "
    "PO–CO mappings and accreditation manuals. Results are class-level; no tool returns one "
    "student's data. Cite the tool results you rely on."
)


def _result(msg_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


async def _handle(message: Any, ctx: Context) -> dict | None:
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or "method" not in message:
        return _error(message.get("id") if isinstance(message, dict) else None, -32600, "Invalid request")
    method, msg_id, params = message["method"], message.get("id"), message.get("params") or {}
    if msg_id is None:  # a notification: nothing to answer
        return None
    if method == "initialize":
        asked = params.get("protocolVersion")
        return _result(msg_id, {
            "protocolVersion": asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
            "instructions": INSTRUCTIONS,
        })
    if method == "ping":
        return _result(msg_id, {})
    if method == "tools/list":
        return _result(msg_id, {"tools": [
            {"name": t.name, "description": t.description, "inputSchema": t.input_schema,
             "annotations": {"readOnlyHint": True, "openWorldHint": False}}
            for t in TOOLS
        ]})
    if method == "tools/call":
        tool = TOOLS_BY_NAME.get(params.get("name"))
        if tool is None:
            return _error(msg_id, -32602, f"Unknown tool: {params.get('name')}")
        try:
            data = await tool.run(ctx, params.get("arguments") or {})
            is_error = False
        except ToolError as exc:
            data, is_error = {"error": str(exc)}, True
        except HTTPException as exc:  # access checks inside the services
            data, is_error = {"error": str(exc.detail)}, True
        write_audit_log(
            ctx.db, entity_type="mcp_tool", entity_id=ctx.user.id, action="MCP_TOOL_CALL",
            org_id=ctx.user.organization_id, actor_user_id=ctx.user.id,
            extra={"tool": tool.name, "error": is_error},
        )
        await ctx.db.commit()
        return _result(msg_id, {
            "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, default=str)}],
            "structuredContent": data,
            "isError": is_error,
        })
    return _error(msg_id, -32601, f"Method not found: {method}")


@router.post("")
async def mcp_endpoint(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    manifest: Annotated[PermissionManifestResponse, Depends(get_permission_manifest)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse(_error(None, -32700, "Parse error"), status_code=status.HTTP_400_BAD_REQUEST)
    ctx = Context(db=db, user=current_user, manifest=manifest)
    if isinstance(payload, list):
        answers = [a for a in [await _handle(m, ctx) for m in payload] if a is not None]
        return JSONResponse(answers) if answers else Response(status_code=status.HTTP_202_ACCEPTED)
    answer = await _handle(payload, ctx)
    if answer is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)
    return JSONResponse(answer)


@router.get("")
async def mcp_stream_not_offered():
    """This server answers with JSON only; it opens no server-sent event stream."""
    return Response(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
