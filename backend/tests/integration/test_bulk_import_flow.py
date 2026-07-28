"""Integration tests for the bulk-import endpoints (ref data attributes + POs)."""
import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.parametrize(
    "path,extra",
    [
        ("/api/v1/ref-data/complex-problems/bulk-import", {"name": "Depth"}),
        ("/api/v1/ref-data/complex-activities/bulk-import", {"name": "Range"}),
        ("/api/v1/ref-data/knowledge-profiles/bulk-import", {}),
    ],
)
async def test_ref_data_bulk_import(client: AsyncClient, auth_headers, path, extra):
    s = uuid.uuid4().hex[:6].upper()
    items = [
        {"code": f"X{s}1", "description": "First characteristic", **extra},
        {"code": f"X{s}2", "description": "Second characteristic", **extra},
        # error rows
        {"code": "", "description": "missing code"},
        {"code": f"X{s}1", "description": "duplicate in file"},
        {"code": f"X{s}3", "description": ""},
        {"code": "X" * 25, "description": "code too long"},
    ]
    resp = await client.post(path, headers=auth_headers, json={"items": items})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created"] == 2, body
    assert [e["row"] for e in body["errors"]] == [3, 4, 5, 6], body

    # re-importing the same codes must now conflict, not duplicate
    again = await client.post(
        path, headers=auth_headers, json={"items": [{"code": f"X{s}1", "description": "again", **extra}]}
    )
    assert again.status_code == 200, again.text
    assert again.json()["created"] == 0
    assert "already exists" in again.json()["errors"][0]["message"]

    listing = await client.get(path.replace("/bulk-import", ""), headers=auth_headers)
    codes = {r["code"] for r in listing.json()}
    assert {f"X{s}1", f"X{s}2"} <= codes


async def test_program_outcome_bulk_import(client: AsyncClient, auth_headers):
    s = uuid.uuid4().hex[:6].upper()
    ver = await client.post(
        "/api/v1/po-versions", headers=auth_headers, json={"name": f"Bulk Ver {s}"}
    )
    assert ver.status_code == 201, ver.text
    version_id = ver.json()["id"]

    items = [
        {"code": f"P{s}1", "po_type": "Generic", "statement": "First outcome"},
        {"code": f"P{s}2", "statement": "Second outcome"},
        {"code": "", "statement": "no code"},
        {"code": f"P{s}1", "statement": "dup in file"},
    ]
    resp = await client.post(
        "/api/v1/program-outcomes/bulk-import",
        headers=auth_headers,
        json={"po_version_id": version_id, "items": items},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created"] == 2, body
    assert [e["row"] for e in body["errors"]] == [3, 4], body

    listing = await client.get(
        f"/api/v1/program-outcomes?po_version_id={version_id}", headers=auth_headers
    )
    rows = listing.json()
    assert {r["code"] for r in rows} == {f"P{s}1", f"P{s}2"}
    assert sorted(r["order_index"] for r in rows) == [0, 1]
    assert next(r for r in rows if r["code"] == f"P{s}1")["po_type"] == "Generic"

    # order_index continues from the existing POs on a second import
    resp2 = await client.post(
        "/api/v1/program-outcomes/bulk-import",
        headers=auth_headers,
        json={"po_version_id": version_id, "items": [{"code": f"P{s}3", "statement": "Third"}]},
    )
    assert resp2.json()["created"] == 1, resp2.text
    listing2 = await client.get(
        f"/api/v1/program-outcomes?po_version_id={version_id}", headers=auth_headers
    )
    assert sorted(r["order_index"] for r in listing2.json()) == [0, 1, 2]
