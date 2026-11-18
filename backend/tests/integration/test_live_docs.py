"""The public /docs page: schedule and access control, drafts and versions, team photos,
live figures and the Markdown export."""
import io
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from PIL import Image

from app.core.config import settings
from app.modules.live_docs import live

URL = "/api/v1/docs"


def _iso(dt: datetime) -> str:
    return dt.isoformat()


async def _set(client: AsyncClient, headers: dict, **body) -> dict:
    payload = {"is_enabled": True, "schedule_mode": "always", **body}
    resp = await client.put(f"{URL}/admin/settings", headers=headers, json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _section(client: AsyncClient, headers: dict, key: str) -> dict:
    docs = (await client.get(f"{URL}/admin", headers=headers)).json()
    return next(s for s in docs["sections"] if s["key"] == key)


@pytest.mark.asyncio
async def test_default_window_and_schedule_control_public_access(client: AsyncClient, auth_headers: dict):
    docs = (await client.get(f"{URL}/admin", headers=auth_headers)).json()
    assert len(docs["sections"]) >= 26
    keys = {s["key"] for s in docs["sections"]}
    assert {"problem", "team", "features", "architecture", "api", "changelog"} <= keys

    # Default window: June 10 00:00 → June 14 23:59 in the configured time zone.
    tz = ZoneInfo(settings.DOCS_TIMEZONE)
    start = datetime.fromisoformat(docs["settings"]["default_starts_at"]).astimezone(tz)
    end = datetime.fromisoformat(docs["settings"]["default_ends_at"]).astimezone(tz)
    assert (start.month, start.day, start.hour, start.minute) == (6, 10, 0, 0)
    assert (end.month, end.day, end.hour, end.minute) == (6, 14, 23, 59)

    now = datetime.now(timezone.utc)
    await _set(client, auth_headers, is_enabled=False)
    resp = await client.get(f"{URL}/public")
    assert resp.status_code == 403 and resp.json()["detail"]["state"] == "disabled"

    await _set(client, auth_headers, schedule_mode="window",
               starts_at=_iso(now + timedelta(days=2)), ends_at=_iso(now + timedelta(days=3)))
    resp = await client.get(f"{URL}/public")
    assert resp.status_code == 403 and resp.json()["detail"]["state"] == "not_started"
    assert (await client.get(f"{URL}/live")).status_code == 403
    assert (await client.get(f"{URL}/export.md")).status_code == 403

    await _set(client, auth_headers, schedule_mode="window",
               starts_at=_iso(now - timedelta(days=3)), ends_at=_iso(now - timedelta(days=2)))
    assert (await client.get(f"{URL}/public")).json()["detail"]["state"] == "ended"

    await _set(client, auth_headers, schedule_mode="duration",
               starts_at=_iso(now - timedelta(hours=1)), duration_minutes=120)
    resp = await client.get(f"{URL}/public")
    assert resp.status_code == 200 and resp.json()["visibility"]["state"] == "live"

    await _set(client, auth_headers, schedule_mode="duration",
               starts_at=_iso(now - timedelta(hours=3)), duration_minutes=60)
    assert (await client.get(f"{URL}/public")).json()["detail"]["state"] == "ended"

    # An end before the start is refused.
    bad = await client.put(f"{URL}/admin/settings", headers=auth_headers, json={
        "is_enabled": True, "schedule_mode": "window",
        "starts_at": _iso(now), "ends_at": _iso(now - timedelta(hours=1)),
    })
    assert bad.status_code == 422

    reset = (await client.post(f"{URL}/admin/settings/reset-window", headers=auth_headers)).json()
    assert reset["settings"]["schedule_mode"] == "window"
    assert datetime.fromisoformat(reset["settings"]["starts_at"]) == start

    await _set(client, auth_headers)
    public = (await client.get(f"{URL}/public")).json()
    assert public["visibility"]["state"] == "live"
    assert public["sections"][0]["group"] == "pitch"
    assert "draft_body" not in public["sections"][0]


@pytest.mark.asyncio
async def test_only_super_admins_edit(client: AsyncClient, auth_headers: dict,
                                      teacher_auth_headers: dict, monkeypatch):
    assert (await client.get(f"{URL}/admin", headers=teacher_auth_headers)).status_code == 403
    resp = await client.put(f"{URL}/admin/settings", headers=teacher_auth_headers,
                            json={"is_enabled": False, "schedule_mode": "always"})
    assert resp.status_code == 403
    assert (await client.get(f"{URL}/admin")).status_code in (401, 403)

    monkeypatch.setattr(settings, "DOCS_EDITOR_EMAILS", "someone.else@example.edu")
    assert (await client.get(f"{URL}/admin", headers=auth_headers)).status_code == 403


@pytest.mark.asyncio
async def test_drafts_publish_versions_and_restore(client: AsyncClient, auth_headers: dict):
    await _set(client, auth_headers)
    problem = await _section(client, auth_headers, "problem")
    original = problem["published_body"]

    resp = await client.put(f"{URL}/admin/sections/{problem['id']}", headers=auth_headers,
                            json={"title": "The problem", "body": "Draft text only."})
    assert resp.status_code == 200
    problem = await _section(client, auth_headers, "problem")
    assert problem["has_changes"] is True

    public = (await client.get(f"{URL}/public")).json()
    shown = next(s for s in public["sections"] if s["key"] == "problem")
    assert shown["body"] == original and shown["title"] == "Problem"

    await client.post(f"{URL}/admin/sections/{problem['id']}/publish", headers=auth_headers)
    public = (await client.get(f"{URL}/public")).json()
    shown = next(s for s in public["sections"] if s["key"] == "problem")
    assert (shown["title"], shown["body"]) == ("The problem", "Draft text only.")

    versions = (await client.get(f"{URL}/admin/sections/{problem['id']}/versions",
                                 headers=auth_headers)).json()
    assert [v["version"] for v in versions][:2] == [versions[0]["version"], versions[0]["version"] - 1]
    first = versions[-1]
    await client.post(f"{URL}/admin/sections/{problem['id']}/versions/{first['version']}/restore",
                      headers=auth_headers)
    problem = await _section(client, auth_headers, "problem")
    assert problem["draft_body"] == first["body"] and problem["has_changes"] is True

    resp = (await client.post(f"{URL}/admin/publish-all", headers=auth_headers)).json()
    assert not any(s["has_changes"] for s in resp["sections"])
    shown = next(s for s in (await client.get(f"{URL}/public")).json()["sections"]
                 if s["key"] == "problem")
    assert shown["body"] == original

    # Discard throws the draft away; hiding removes the section from the public page.
    await client.put(f"{URL}/admin/sections/{problem['id']}", headers=auth_headers,
                     json={"title": "Problem", "body": "Never published."})
    await client.post(f"{URL}/admin/sections/{problem['id']}/discard", headers=auth_headers)
    assert (await _section(client, auth_headers, "problem"))["draft_body"] == original

    await client.put(f"{URL}/admin/sections/{problem['id']}/visibility", headers=auth_headers,
                     json={"is_visible": False})
    keys = {s["key"] for s in (await client.get(f"{URL}/public")).json()["sections"]}
    assert "problem" not in keys
    await client.put(f"{URL}/admin/sections/{problem['id']}/visibility", headers=auth_headers,
                     json={"is_visible": True})


@pytest.mark.asyncio
async def test_custom_sections_order_and_data_checks(client: AsyncClient, auth_headers: dict):
    await _set(client, auth_headers)
    docs = (await client.post(f"{URL}/admin/sections", headers=auth_headers,
                              json={"title": "Pilot results", "group": "operations"})).json()
    custom = next(s for s in docs["sections"] if s["key"] == "pilot-results")
    assert custom["is_builtin"] is False and custom["published_version"] == 0
    public_keys = {s["key"] for s in (await client.get(f"{URL}/public")).json()["sections"]}
    assert "pilot-results" not in public_keys  # never published yet

    await client.put(f"{URL}/admin/sections/{custom['id']}", headers=auth_headers,
                     json={"title": "Pilot results", "body": "**Five courses** audited."})
    await client.post(f"{URL}/admin/sections/{custom['id']}/publish", headers=auth_headers)
    public_keys = [s["key"] for s in (await client.get(f"{URL}/public")).json()["sections"]]
    assert "pilot-results" in public_keys

    ops = [s for s in docs["sections"] if s["group"] == "operations"]
    order = [custom["id"]] + [s["id"] for s in ops if s["id"] != custom["id"]]
    resp = await client.put(f"{URL}/admin/sections-order", headers=auth_headers, json={"ids": order})
    ops_now = [s["id"] for s in resp.json()["sections"] if s["group"] == "operations"]
    assert ops_now[0] == custom["id"]

    features = await _section(client, auth_headers, "features")
    bad = await client.put(f"{URL}/admin/sections/{features['id']}", headers=auth_headers, json={
        "title": "Feature matrix", "body": "",
        "data": {"items": [{"name": "X", "status": "maybe"}]},
    })
    assert bad.status_code == 422
    bad = await client.put(f"{URL}/admin/sections/{features['id']}", headers=auth_headers, json={
        "title": "Feature matrix", "body": "",
        "data": {"items": [{"name": "X", "status": "live", "signal": "nope"}]},
    })
    assert bad.status_code == 422

    team = await _section(client, auth_headers, "team")
    assert (await client.delete(f"{URL}/admin/sections/{team['id']}",
                                headers=auth_headers)).status_code == 409
    resp = await client.delete(f"{URL}/admin/sections/{custom['id']}", headers=auth_headers)
    assert all(s["key"] != "pilot-results" for s in resp.json()["sections"])


def _png(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (30, 120, 200)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_team_members_get_uniform_photos(client: AsyncClient, auth_headers: dict):
    await _set(client, auth_headers, team_name="Team Obelytics")
    resp = await client.post(
        f"{URL}/admin/team", headers=auth_headers,
        data={"full_name": "Test Member", "role": "Backend engineer", "email": "member@example.edu"},
        files={"photo": ("photo.png", _png(1200, 700), "image/png")},
    )
    assert resp.status_code == 201, resp.text
    member = next(m for m in resp.json()["team"] if m["email"] == "member@example.edu")
    assert member["photo_url"]

    photo = await client.get(member["photo_url"])
    assert photo.status_code == 200 and photo.headers["content-type"] == "image/webp"
    assert Image.open(io.BytesIO(photo.content)).size == (480, 480)

    bad = await client.put(f"{URL}/admin/team/{member['id']}/photo", headers=auth_headers,
                           files={"photo": ("x.png", b"not an image", "image/png")})
    assert bad.status_code == 422
    bad = await client.put(f"{URL}/admin/team/{member['id']}", headers=auth_headers,
                           json={"full_name": "Test Member", "role": "Lead", "email": "nope"})
    assert bad.status_code == 422

    resp = await client.put(f"{URL}/admin/team/{member['id']}", headers=auth_headers,
                            json={"full_name": "Test Member", "role": "Lead",
                                  "email": "member@example.edu"})
    assert next(m for m in resp.json()["team"] if m["id"] == member["id"])["role"] == "Lead"

    public = (await client.get(f"{URL}/public")).json()
    assert public["team_name"] == "Team Obelytics"
    assert any(m["full_name"] == "Test Member" for m in public["team"])

    resp = await client.delete(f"{URL}/admin/team/{member['id']}/photo", headers=auth_headers)
    assert next(m for m in resp.json()["team"] if m["id"] == member["id"])["photo_url"] is None
    resp = await client.delete(f"{URL}/admin/team/{member['id']}", headers=auth_headers)
    assert all(m["id"] != member["id"] for m in resp.json()["team"])


@pytest.mark.asyncio
async def test_live_figures_api_reference_and_export(client: AsyncClient, auth_headers: dict):
    await _set(client, auth_headers)
    live.clear_cache()
    data = (await client.get(f"{URL}/live")).json()
    assert data["system"]["database"] is True
    assert data["api"]["endpoints"] > 300 and len(data["api"]["mcp_tools"]) == 7
    assert data["usage"]["organizations"]["real"] >= 1
    assert data["usage"]["courses"]["label"] == "Courses"
    assert {f["feature"] for f in data["ai"]["features"]} == {
        "integrity", "copilot", "authoring", "improvement",
    }
    assert len(data["ai"]["daily"]) == 14 and len(data["events"]["daily"]) == 14

    ref = (await client.get(f"{URL}/api-reference")).json()
    rows = {(e["method"], e["path"]): e for g in ref["groups"] for e in g["endpoints"]}
    assert rows[("GET", "/api/v1/docs/public")]["auth"] == "public"
    assert rows[("GET", "/api/v1/docs/admin")]["auth"] == "bearer"

    md = await client.get(f"{URL}/export.md")
    assert md.status_code == 200 and md.headers["content-type"].startswith("text/markdown")
    assert "### Problem" in md.text and "```mermaid" in md.text
    assert "| Live figure | Real institutions | Demo (synthetic) |" in md.text
