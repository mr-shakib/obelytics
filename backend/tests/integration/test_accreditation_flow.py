"""Integration tests for Accreditation module (Phase 9)."""
import uuid

import pytest
from httpx import AsyncClient


# ── Setup helpers ─────────────────────────────────────────────────────────────

async def _setup_accreditation_scenario(client: AsyncClient, headers: dict) -> dict:
    """
    Create a program with a PO, ready for accreditation cycle creation.
    Returns: program_id, po_id
    """
    suffix = uuid.uuid4().hex[:8]

    dept_resp = await client.post(
        "/api/v1/departments",
        headers=headers,
        json={"name": f"Acc Dept {suffix}", "short_name": f"AC{suffix[:4]}"},
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept_id = dept_resp.json()["id"]

    prog_resp = await client.post(
        "/api/v1/programs",
        headers=headers,
        json={
            "department_id": dept_id,
            "title": f"Acc Program {suffix}",
            "acronym": f"AP{suffix[:4]}",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 136,
            "study_mode": "FULL_TIME",
        },
    )
    assert prog_resp.status_code == 201, prog_resp.text
    program_id = prog_resp.json()["id"]

    po_resp = await client.post(
        "/api/v1/program-outcomes",
        headers=headers,
        json={
            "program_id": program_id,
            "code": "PO1",
            "statement": "Accreditation PO statement",
            "order_index": 1,
        },
    )
    assert po_resp.status_code == 201, po_resp.text
    po_id = po_resp.json()["id"]

    return {"program_id": program_id, "po_id": po_id}


# ── Cycle CRUD Tests ──────────────────────────────────────────────────────────

async def test_create_accreditation_cycle(client: AsyncClient, auth_headers):
    """POST /accreditation/cycles → 201 with correct fields."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]

    resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "ABET 2024-2027",
            "accreditation_body": "ABET",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["program_id"] == program_id
    assert data["name"] == "ABET 2024-2027"
    assert data["accreditation_body"] == "ABET"
    assert data["cycle_start_year"] == 2024
    assert data["cycle_end_year"] == 2027
    assert data["status"] == "DRAFT"
    assert "id" in data


async def test_list_accreditation_cycles(client: AsyncClient, auth_headers):
    """GET /accreditation/cycles → includes created cycle."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]

    create_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "NBA 2025-2028",
            "accreditation_body": "NBA",
            "cycle_start_year": 2025,
            "cycle_end_year": 2028,
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    cycle_id = create_resp.json()["id"]

    list_resp = await client.get("/api/v1/accreditation/cycles", headers=auth_headers)
    assert list_resp.status_code == 200, list_resp.text
    ids = [c["id"] for c in list_resp.json()]
    assert cycle_id in ids


async def test_list_cycles_filter_by_program(client: AsyncClient, auth_headers):
    """GET /accreditation/cycles?program_id=... filters correctly."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]

    create_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "Filter Test Cycle",
            "accreditation_body": "NAAC",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    cycle_id = create_resp.json()["id"]

    resp = await client.get(
        "/api/v1/accreditation/cycles",
        params={"program_id": program_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    ids = [c["id"] for c in data]
    assert cycle_id in ids
    # All returned cycles should belong to this program
    for c in data:
        assert c["program_id"] == program_id


async def test_get_cycle_by_id(client: AsyncClient, auth_headers):
    """GET /accreditation/cycles/{cycle_id} → 200 with correct data."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]

    create_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "Get Test Cycle",
            "accreditation_body": "OTHER",
            "cycle_start_year": 2023,
            "cycle_end_year": 2026,
        },
    )
    cycle_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/accreditation/cycles/{cycle_id}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == cycle_id
    assert data["name"] == "Get Test Cycle"


async def test_get_cycle_not_found(client: AsyncClient, auth_headers):
    """GET /accreditation/cycles/{non_existent_id} → 404."""
    resp = await client.get(
        f"/api/v1/accreditation/cycles/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 404, resp.text


async def test_patch_cycle_in_draft(client: AsyncClient, auth_headers):
    """PATCH cycle while in DRAFT → 200 with updated name."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]

    create_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "Patch Test Old Name",
            "accreditation_body": "ABET",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    cycle_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/accreditation/cycles/{cycle_id}",
        headers=auth_headers,
        json={"name": "Patch Test New Name"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Patch Test New Name"


async def test_activate_cycle(client: AsyncClient, auth_headers):
    """POST /cycles/{id}/activate → status=ACTIVE."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]

    create_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "Activate Test",
            "accreditation_body": "ABET",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    cycle_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/accreditation/cycles/{cycle_id}/activate",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ACTIVE"


async def test_close_cycle(client: AsyncClient, auth_headers):
    """POST /cycles/{id}/close → status=CLOSED (must be ACTIVE first)."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]

    create_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "Close Test",
            "accreditation_body": "NBA",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    cycle_id = create_resp.json()["id"]

    # Must activate first
    await client.post(f"/api/v1/accreditation/cycles/{cycle_id}/activate", headers=auth_headers)

    resp = await client.post(
        f"/api/v1/accreditation/cycles/{cycle_id}/close",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "CLOSED"


async def test_patch_cycle_after_active_returns_400(client: AsyncClient, auth_headers):
    """PATCH cycle when not in DRAFT → 400."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]

    create_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "No Patch After Active",
            "accreditation_body": "ABET",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    cycle_id = create_resp.json()["id"]

    # Activate the cycle
    activate_resp = await client.post(
        f"/api/v1/accreditation/cycles/{cycle_id}/activate",
        headers=auth_headers,
    )
    assert activate_resp.status_code == 200, activate_resp.text

    # Patch should now fail
    resp = await client.patch(
        f"/api/v1/accreditation/cycles/{cycle_id}",
        headers=auth_headers,
        json={"name": "Illegal Update"},
    )
    assert resp.status_code == 400, resp.text


async def test_invalid_status_transition_activate_already_active(
    client: AsyncClient, auth_headers
):
    """POST activate on already-ACTIVE cycle → 400."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]

    create_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "Double Activate Test",
            "accreditation_body": "ABET",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    cycle_id = create_resp.json()["id"]

    await client.post(f"/api/v1/accreditation/cycles/{cycle_id}/activate", headers=auth_headers)

    resp = await client.post(
        f"/api/v1/accreditation/cycles/{cycle_id}/activate",
        headers=auth_headers,
    )
    assert resp.status_code == 400, resp.text


# ── Criteria Tests ────────────────────────────────────────────────────────────

async def test_add_criterion_to_cycle(client: AsyncClient, auth_headers):
    """POST /cycles/{id}/criteria → 201 with criterion data."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]

    cycle_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "Criterion Test Cycle",
            "accreditation_body": "ABET",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    cycle_id = cycle_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/accreditation/cycles/{cycle_id}/criteria",
        headers=auth_headers,
        json={
            "code": "C1",
            "title": "Program Educational Objectives",
            "description": "Criteria 1 description",
            "order_index": 1,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["cycle_id"] == cycle_id
    assert data["code"] == "C1"
    assert data["title"] == "Program Educational Objectives"
    assert data["order_index"] == 1


async def test_list_criteria(client: AsyncClient, auth_headers):
    """GET /cycles/{id}/criteria → includes added criterion."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]

    cycle_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "List Criteria Cycle",
            "accreditation_body": "NBA",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    cycle_id = cycle_resp.json()["id"]

    add_resp = await client.post(
        f"/api/v1/accreditation/cycles/{cycle_id}/criteria",
        headers=auth_headers,
        json={"code": "C2", "title": "Student Outcomes", "order_index": 2},
    )
    criterion_id = add_resp.json()["id"]

    list_resp = await client.get(
        f"/api/v1/accreditation/cycles/{cycle_id}/criteria",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    ids = [c["id"] for c in list_resp.json()]
    assert criterion_id in ids


async def test_patch_criterion(client: AsyncClient, auth_headers):
    """PATCH /criteria/{id} → 200 with updated title."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]

    cycle_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "Patch Criterion Cycle",
            "accreditation_body": "ABET",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    cycle_id = cycle_resp.json()["id"]

    add_resp = await client.post(
        f"/api/v1/accreditation/cycles/{cycle_id}/criteria",
        headers=auth_headers,
        json={"code": "C3", "title": "Old Title", "order_index": 3},
    )
    criterion_id = add_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/accreditation/criteria/{criterion_id}",
        headers=auth_headers,
        json={"title": "New Title"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["title"] == "New Title"


async def test_add_criterion_to_closed_cycle_fails(client: AsyncClient, auth_headers):
    """POST criteria to a CLOSED cycle → 400."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]

    cycle_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "Closed Cycle Test",
            "accreditation_body": "ABET",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    cycle_id = cycle_resp.json()["id"]

    await client.post(f"/api/v1/accreditation/cycles/{cycle_id}/activate", headers=auth_headers)
    await client.post(f"/api/v1/accreditation/cycles/{cycle_id}/close", headers=auth_headers)

    resp = await client.post(
        f"/api/v1/accreditation/cycles/{cycle_id}/criteria",
        headers=auth_headers,
        json={"code": "C_CLOSED", "title": "Should Fail", "order_index": 99},
    )
    assert resp.status_code == 400, resp.text


# ── PO Mapping Tests ──────────────────────────────────────────────────────────

async def test_map_po_to_criterion(client: AsyncClient, auth_headers):
    """POST /criteria/{id}/po-mappings → 201 with mapping data."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]
    po_id = scenario["po_id"]

    cycle_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "PO Map Cycle",
            "accreditation_body": "ABET",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    cycle_id = cycle_resp.json()["id"]

    crit_resp = await client.post(
        f"/api/v1/accreditation/cycles/{cycle_id}/criteria",
        headers=auth_headers,
        json={"code": "C_PO1", "title": "PO Mapping Criterion", "order_index": 1},
    )
    criterion_id = crit_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/accreditation/criteria/{criterion_id}/po-mappings",
        headers=auth_headers,
        json={"program_outcome_id": po_id, "notes": "Test mapping note"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["criterion_id"] == criterion_id
    assert data["program_outcome_id"] == po_id
    assert data["notes"] == "Test mapping note"


async def test_list_po_mappings(client: AsyncClient, auth_headers):
    """GET /criteria/{id}/po-mappings → includes the mapped PO."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]
    po_id = scenario["po_id"]

    cycle_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "List PO Map Cycle",
            "accreditation_body": "NBA",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    cycle_id = cycle_resp.json()["id"]

    crit_resp = await client.post(
        f"/api/v1/accreditation/cycles/{cycle_id}/criteria",
        headers=auth_headers,
        json={"code": "C_LIST1", "title": "List PO Criterion", "order_index": 1},
    )
    criterion_id = crit_resp.json()["id"]

    map_resp = await client.post(
        f"/api/v1/accreditation/criteria/{criterion_id}/po-mappings",
        headers=auth_headers,
        json={"program_outcome_id": po_id},
    )
    mapping_id = map_resp.json()["id"]

    list_resp = await client.get(
        f"/api/v1/accreditation/criteria/{criterion_id}/po-mappings",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    ids = [m["id"] for m in list_resp.json()]
    assert mapping_id in ids


async def test_duplicate_po_mapping_returns_400(client: AsyncClient, auth_headers):
    """POST duplicate PO mapping → 400."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]
    po_id = scenario["po_id"]

    cycle_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "Dup PO Map Cycle",
            "accreditation_body": "ABET",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    cycle_id = cycle_resp.json()["id"]

    crit_resp = await client.post(
        f"/api/v1/accreditation/cycles/{cycle_id}/criteria",
        headers=auth_headers,
        json={"code": "C_DUP", "title": "Dup PO Criterion", "order_index": 1},
    )
    criterion_id = crit_resp.json()["id"]

    # First mapping
    first_resp = await client.post(
        f"/api/v1/accreditation/criteria/{criterion_id}/po-mappings",
        headers=auth_headers,
        json={"program_outcome_id": po_id},
    )
    assert first_resp.status_code == 201, first_resp.text

    # Duplicate mapping
    dup_resp = await client.post(
        f"/api/v1/accreditation/criteria/{criterion_id}/po-mappings",
        headers=auth_headers,
        json={"program_outcome_id": po_id},
    )
    assert dup_resp.status_code == 400, dup_resp.text


async def test_delete_po_mapping(client: AsyncClient, auth_headers):
    """DELETE /criteria/{id}/po-mappings/{po_id} → 204."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]
    po_id = scenario["po_id"]

    cycle_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "Del PO Map Cycle",
            "accreditation_body": "ABET",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    cycle_id = cycle_resp.json()["id"]

    crit_resp = await client.post(
        f"/api/v1/accreditation/cycles/{cycle_id}/criteria",
        headers=auth_headers,
        json={"code": "C_DEL1", "title": "Del PO Criterion", "order_index": 1},
    )
    criterion_id = crit_resp.json()["id"]

    await client.post(
        f"/api/v1/accreditation/criteria/{criterion_id}/po-mappings",
        headers=auth_headers,
        json={"program_outcome_id": po_id},
    )

    del_resp = await client.delete(
        f"/api/v1/accreditation/criteria/{criterion_id}/po-mappings/{po_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 204, del_resp.text

    # Verify it's gone
    list_resp = await client.get(
        f"/api/v1/accreditation/criteria/{criterion_id}/po-mappings",
        headers=auth_headers,
    )
    assert list_resp.json() == []


async def test_delete_criterion(client: AsyncClient, auth_headers):
    """DELETE /criteria/{id} → 204."""
    scenario = await _setup_accreditation_scenario(client, auth_headers)
    program_id = scenario["program_id"]

    cycle_resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "Del Criterion Cycle",
            "accreditation_body": "NAAC",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    cycle_id = cycle_resp.json()["id"]

    crit_resp = await client.post(
        f"/api/v1/accreditation/cycles/{cycle_id}/criteria",
        headers=auth_headers,
        json={"code": "C_DEL2", "title": "To Delete Criterion", "order_index": 1},
    )
    criterion_id = crit_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/accreditation/criteria/{criterion_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 204, del_resp.text

    # Verify gone from list
    list_resp = await client.get(
        f"/api/v1/accreditation/cycles/{cycle_id}/criteria",
        headers=auth_headers,
    )
    ids = [c["id"] for c in list_resp.json()]
    assert criterion_id not in ids


# ── RBAC Tests ────────────────────────────────────────────────────────────────

async def test_accreditation_read_denied_without_auth(client: AsyncClient):
    """Unauthenticated request is rejected."""
    resp = await client.get("/api/v1/accreditation/cycles")
    assert resp.status_code == 403


async def test_accreditation_read_denied_for_teacher(client: AsyncClient, teacher_auth_headers):
    """Section Teacher does not have accreditation.read permission → 403."""
    resp = await client.get("/api/v1/accreditation/cycles", headers=teacher_auth_headers)
    assert resp.status_code == 403, resp.text


async def test_accreditation_read_allowed_for_ml(client: AsyncClient, ml_auth_headers):
    """Module Leader has accreditation.read permission → 200."""
    resp = await client.get("/api/v1/accreditation/cycles", headers=ml_auth_headers)
    assert resp.status_code == 200, resp.text


async def test_accreditation_manage_denied_for_ml(client: AsyncClient, ml_auth_headers):
    """Module Leader does not have accreditation.manage permission → 403 on create."""
    resp = await client.post(
        "/api/v1/accreditation/cycles",
        headers=ml_auth_headers,
        json={
            "program_id": str(uuid.uuid4()),
            "name": "ML Should Fail",
            "accreditation_body": "ABET",
            "cycle_start_year": 2024,
            "cycle_end_year": 2027,
        },
    )
    # ML does not have accreditation.cycle.create
    assert resp.status_code == 403, resp.text
