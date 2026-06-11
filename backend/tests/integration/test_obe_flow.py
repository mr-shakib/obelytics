"""Integration tests for OBE module endpoints."""
import uuid

import pytest
from httpx import AsyncClient


# ── Setup helpers ─────────────────────────────────────────────────────────────

async def _setup_curriculum(client: AsyncClient, headers: dict) -> dict:
    """Create department, program, course type, course, curriculum and return IDs."""
    suffix = uuid.uuid4().hex[:6]

    dept_resp = await client.post(
        "/api/v1/departments",
        headers=headers,
        json={"name": f"OBE Dept {suffix}", "short_name": f"OD{suffix[:4]}"},
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept_id = dept_resp.json()["id"]

    prog_resp = await client.post(
        "/api/v1/programs",
        headers=headers,
        json={
            "department_id": dept_id,
            "title": f"OBE Program {suffix}",
            "acronym": f"OP{suffix[:4]}",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 136,
            "study_mode": "FULL_TIME",
        },
    )
    assert prog_resp.status_code == 201, prog_resp.text
    program_id = prog_resp.json()["id"]

    ct_resp = await client.post(
        "/api/v1/ref-data/course-categories",
        headers=headers,
        json={"name": f"OBE Theory {suffix}"},
    )
    assert ct_resp.status_code == 201, ct_resp.text
    ct_id = ct_resp.json()["id"]

    course_resp = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "course_category_id": ct_id,
            "course_type": "THEORY",
            "code": f"OBE{suffix}",
            "title": f"OBE Course {suffix}",
            "credits": 3,
            "theory_hours": 3,
            "lab_hours": 0,
        },
    )
    assert course_resp.status_code == 201, course_resp.text
    course_id = course_resp.json()["id"]

    curr_resp = await client.post(
        "/api/v1/curricula",
        headers=headers,
        json={
            "program_id": program_id,
            "name": f"OBE Curriculum {suffix}",
            "code": f"OBC{suffix}",
            "effective_year": 2024,
        },
    )
    assert curr_resp.status_code == 201, curr_resp.text
    curriculum_id = curr_resp.json()["id"]

    return {
        "program_id": program_id,
        "curriculum_id": curriculum_id,
        "course_id": course_id,
    }


# ── Program Outcomes ──────────────────────────────────────────────────────────

async def test_create_po(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    resp = await client.post(
        "/api/v1/program-outcomes",
        headers=auth_headers,
        json={
            "program_id": ids["program_id"],
            "code": "PO1",
            "statement": "Apply engineering fundamentals",
            "order_index": 1,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["code"] == "PO1"
    assert data["status"] == "ACTIVE"
    assert data["program_id"] == ids["program_id"]


async def test_list_pos(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    await client.post(
        "/api/v1/program-outcomes",
        headers=auth_headers,
        json={
            "program_id": ids["program_id"],
            "code": "PO1",
            "statement": "First outcome",
            "order_index": 1,
        },
    )
    resp = await client.get(
        "/api/v1/program-outcomes",
        headers=auth_headers,
        params={"program_id": ids["program_id"]},
    )
    assert resp.status_code == 200
    pos = resp.json()
    assert isinstance(pos, list)
    assert len(pos) >= 1


async def test_get_po(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    create_resp = await client.post(
        "/api/v1/program-outcomes",
        headers=auth_headers,
        json={
            "program_id": ids["program_id"],
            "code": "PO1",
            "statement": "Get test outcome",
            "order_index": 1,
        },
    )
    po_id = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/program-outcomes/{po_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == po_id


async def test_archive_po(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    create_resp = await client.post(
        "/api/v1/program-outcomes",
        headers=auth_headers,
        json={
            "program_id": ids["program_id"],
            "code": "PO1",
            "statement": "Archive test",
            "order_index": 1,
        },
    )
    po_id = create_resp.json()["id"]
    resp = await client.post(f"/api/v1/program-outcomes/{po_id}/archive", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ARCHIVED"
    assert resp.json()["archived_at"] is not None


async def test_archive_po_blocked_when_mapping_entries_exist(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)

    po_resp = await client.post(
        "/api/v1/program-outcomes",
        headers=auth_headers,
        json={
            "program_id": ids["program_id"],
            "code": "PO1",
            "statement": "PO to block",
            "order_index": 1,
        },
    )
    po_id = po_resp.json()["id"]

    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO statement",
        },
    )
    co_id = co_resp.json()["id"]

    # Create mapping set
    ms_resp = await client.post(
        "/api/v1/mappings/co-po",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
        },
    )
    assert ms_resp.status_code == 201, ms_resp.text
    set_id = ms_resp.json()["id"]

    # Add an entry referencing this PO
    await client.put(
        f"/api/v1/mappings/co-po/{set_id}/entries",
        headers=auth_headers,
        json=[{"course_outcome_id": co_id, "program_outcome_id": po_id, "weight": 2}],
    )

    # Now try to archive the PO
    resp = await client.post(f"/api/v1/program-outcomes/{po_id}/archive", headers=auth_headers)
    assert resp.status_code == 409
    assert "mapping" in resp.json()["detail"].lower()


async def test_po_code_conflict(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    payload = {
        "program_id": ids["program_id"],
        "code": "PO1",
        "statement": "First",
        "order_index": 1,
    }
    await client.post("/api/v1/program-outcomes", headers=auth_headers, json=payload)
    resp = await client.post("/api/v1/program-outcomes", headers=auth_headers, json=payload)
    assert resp.status_code == 409


async def test_teacher_cannot_create_po(client: AsyncClient, auth_headers, teacher_auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    resp = await client.post(
        "/api/v1/program-outcomes",
        headers=teacher_auth_headers,
        json={
            "program_id": ids["program_id"],
            "code": "PO1",
            "statement": "Teacher tries to create PO",
            "order_index": 1,
        },
    )
    assert resp.status_code == 403


# ── PO Knowledge Profiles ─────────────────────────────────────────────────────

async def _create_knowledge_profile(client: AsyncClient, headers: dict) -> str:
    suffix = uuid.uuid4().hex[:6]
    resp = await client.post(
        "/api/v1/config/knowledge-profiles",
        headers=headers,
        json={"code": f"KP{suffix[:4]}", "description": f"Test KP {suffix}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_add_remove_knowledge_profiles_to_po(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    po_resp = await client.post(
        "/api/v1/program-outcomes",
        headers=auth_headers,
        json={
            "program_id": ids["program_id"],
            "code": "PO1",
            "statement": "KP test PO",
            "order_index": 1,
        },
    )
    po_id = po_resp.json()["id"]
    kp_id = await _create_knowledge_profile(client, auth_headers)

    # Add KP
    add_resp = await client.post(
        f"/api/v1/program-outcomes/{po_id}/knowledge-profiles",
        headers=auth_headers,
        json={"knowledge_profile_id": kp_id},
    )
    assert add_resp.status_code == 201, add_resp.text
    assert add_resp.json()["knowledge_profile_id"] == kp_id

    # List KPs
    list_resp = await client.get(
        f"/api/v1/program-outcomes/{po_id}/knowledge-profiles",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    kps = list_resp.json()
    assert any(k["knowledge_profile_id"] == kp_id for k in kps)

    # Remove KP
    del_resp = await client.delete(
        f"/api/v1/program-outcomes/{po_id}/knowledge-profiles/{kp_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 204

    # List again — should be empty
    list_resp2 = await client.get(
        f"/api/v1/program-outcomes/{po_id}/knowledge-profiles",
        headers=auth_headers,
    )
    assert all(k["knowledge_profile_id"] != kp_id for k in list_resp2.json())


# ── Course Outcomes ───────────────────────────────────────────────────────────

async def test_create_co_draft(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO1 statement",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["code"] == "CO1"
    assert data["status"] == "DRAFT"


async def test_co_state_machine_submit_approve_publish(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO for state machine test",
        },
    )
    co_id = co_resp.json()["id"]
    assert co_resp.json()["status"] == "DRAFT"

    # Submit
    sub_resp = await client.post(f"/api/v1/course-outcomes/{co_id}/submit", headers=auth_headers)
    assert sub_resp.status_code == 200, sub_resp.text
    assert sub_resp.json()["status"] == "SUBMITTED"

    # Approve
    app_resp = await client.post(f"/api/v1/course-outcomes/{co_id}/approve", headers=auth_headers)
    assert app_resp.status_code == 200, app_resp.text
    assert app_resp.json()["status"] == "APPROVED"

    # Publish
    pub_resp = await client.post(f"/api/v1/course-outcomes/{co_id}/publish", headers=auth_headers)
    assert pub_resp.status_code == 200, pub_resp.text
    assert pub_resp.json()["status"] == "PUBLISHED"


async def test_co_state_machine_submit_reject_back_to_draft(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO for reject test",
        },
    )
    co_id = co_resp.json()["id"]

    # Submit
    await client.post(f"/api/v1/course-outcomes/{co_id}/submit", headers=auth_headers)

    # Reject → back to DRAFT
    rej_resp = await client.post(f"/api/v1/course-outcomes/{co_id}/reject", headers=auth_headers)
    assert rej_resp.status_code == 200, rej_resp.text
    assert rej_resp.json()["status"] == "DRAFT"


async def test_co_update_blocked_when_not_draft(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO for edit block test",
        },
    )
    co_id = co_resp.json()["id"]

    # Submit so it's no longer DRAFT
    await client.post(f"/api/v1/course-outcomes/{co_id}/submit", headers=auth_headers)

    # Try to update — should be blocked
    resp = await client.patch(
        f"/api/v1/course-outcomes/{co_id}",
        headers=auth_headers,
        json={"statement": "Blocked update"},
    )
    assert resp.status_code == 409


async def test_co_invalid_state_transition(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO for invalid transition",
        },
    )
    co_id = co_resp.json()["id"]

    # Try to approve from DRAFT (not allowed; must submit first)
    resp = await client.post(f"/api/v1/course-outcomes/{co_id}/approve", headers=auth_headers)
    assert resp.status_code == 409


async def test_ml_cannot_publish_co(client: AsyncClient, auth_headers, ml_auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO for ML publish test",
        },
    )
    co_id = co_resp.json()["id"]
    await client.post(f"/api/v1/course-outcomes/{co_id}/submit", headers=auth_headers)
    await client.post(f"/api/v1/course-outcomes/{co_id}/approve", headers=auth_headers)

    # ML tries to publish — should be forbidden
    resp = await client.post(
        f"/api/v1/course-outcomes/{co_id}/publish",
        headers=ml_auth_headers,
    )
    assert resp.status_code == 403


# ── Delivery Methods ──────────────────────────────────────────────────────────

async def _create_delivery_method(client: AsyncClient, headers: dict) -> str:
    suffix = uuid.uuid4().hex[:6]
    resp = await client.post(
        "/api/v1/config/delivery-methods",
        headers=headers,
        json={"name": f"Lecture {suffix}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_add_delivery_methods_to_co(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO for DM test",
        },
    )
    co_id = co_resp.json()["id"]
    dm_id = await _create_delivery_method(client, auth_headers)

    add_resp = await client.post(
        f"/api/v1/course-outcomes/{co_id}/delivery-methods",
        headers=auth_headers,
        json={"delivery_method_id": dm_id},
    )
    assert add_resp.status_code == 201, add_resp.text
    assert add_resp.json()["delivery_method_id"] == dm_id

    list_resp = await client.get(
        f"/api/v1/course-outcomes/{co_id}/delivery-methods",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    assert any(d["delivery_method_id"] == dm_id for d in list_resp.json())


async def test_add_delivery_method_blocked_when_co_published(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO for DM block test",
        },
    )
    co_id = co_resp.json()["id"]
    # Progress to PUBLISHED
    await client.post(f"/api/v1/course-outcomes/{co_id}/submit", headers=auth_headers)
    await client.post(f"/api/v1/course-outcomes/{co_id}/approve", headers=auth_headers)
    await client.post(f"/api/v1/course-outcomes/{co_id}/publish", headers=auth_headers)

    dm_id = await _create_delivery_method(client, auth_headers)
    resp = await client.post(
        f"/api/v1/course-outcomes/{co_id}/delivery-methods",
        headers=auth_headers,
        json={"delivery_method_id": dm_id},
    )
    assert resp.status_code == 409


# ── CO-PO Mapping Sets ────────────────────────────────────────────────────────

async def test_create_co_po_mapping_set(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    resp = await client.post(
        "/api/v1/mappings/co-po",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "DRAFT"
    assert data["curriculum_id"] == ids["curriculum_id"]


async def test_upsert_co_po_entries(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)

    po_resp = await client.post(
        "/api/v1/program-outcomes",
        headers=auth_headers,
        json={
            "program_id": ids["program_id"],
            "code": "PO1",
            "statement": "PO for mapping test",
            "order_index": 1,
        },
    )
    po_id = po_resp.json()["id"]

    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO for mapping",
        },
    )
    co_id = co_resp.json()["id"]

    ms_resp = await client.post(
        "/api/v1/mappings/co-po",
        headers=auth_headers,
        json={"curriculum_id": ids["curriculum_id"], "course_id": ids["course_id"]},
    )
    set_id = ms_resp.json()["id"]

    entries_resp = await client.put(
        f"/api/v1/mappings/co-po/{set_id}/entries",
        headers=auth_headers,
        json=[{"course_outcome_id": co_id, "program_outcome_id": po_id, "weight": 2}],
    )
    assert entries_resp.status_code == 200, entries_resp.text
    entries = entries_resp.json()
    assert len(entries) == 1
    assert entries[0]["weight"] == 2


async def test_publish_co_po_mapping_set(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)

    po_resp = await client.post(
        "/api/v1/program-outcomes",
        headers=auth_headers,
        json={
            "program_id": ids["program_id"],
            "code": "PO1",
            "statement": "PO for publish test",
            "order_index": 1,
        },
    )
    po_id = po_resp.json()["id"]

    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO for publish",
        },
    )
    co_id = co_resp.json()["id"]

    ms_resp = await client.post(
        "/api/v1/mappings/co-po",
        headers=auth_headers,
        json={"curriculum_id": ids["curriculum_id"], "course_id": ids["course_id"]},
    )
    set_id = ms_resp.json()["id"]

    await client.put(
        f"/api/v1/mappings/co-po/{set_id}/entries",
        headers=auth_headers,
        json=[{"course_outcome_id": co_id, "program_outcome_id": po_id, "weight": 3}],
    )

    pub_resp = await client.post(
        f"/api/v1/mappings/co-po/{set_id}/publish",
        headers=auth_headers,
    )
    assert pub_resp.status_code == 200, pub_resp.text
    assert pub_resp.json()["status"] == "PUBLISHED"
    assert pub_resp.json()["published_at"] is not None


async def test_cannot_upsert_entries_after_publish(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)

    po_resp = await client.post(
        "/api/v1/program-outcomes",
        headers=auth_headers,
        json={
            "program_id": ids["program_id"],
            "code": "PO1",
            "statement": "PO",
            "order_index": 1,
        },
    )
    po_id = po_resp.json()["id"]

    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO",
        },
    )
    co_id = co_resp.json()["id"]

    ms_resp = await client.post(
        "/api/v1/mappings/co-po",
        headers=auth_headers,
        json={"curriculum_id": ids["curriculum_id"], "course_id": ids["course_id"]},
    )
    set_id = ms_resp.json()["id"]

    await client.post(f"/api/v1/mappings/co-po/{set_id}/publish", headers=auth_headers)

    # Try to upsert entries after publish
    resp = await client.put(
        f"/api/v1/mappings/co-po/{set_id}/entries",
        headers=auth_headers,
        json=[{"course_outcome_id": co_id, "program_outcome_id": po_id, "weight": 1}],
    )
    assert resp.status_code == 409


# ── CO-CP Mappings ────────────────────────────────────────────────────────────

async def _create_complex_problem(client: AsyncClient, headers: dict) -> str:
    suffix = uuid.uuid4().hex[:6]
    resp = await client.post(
        "/api/v1/config/complex-problems",
        headers=headers,
        json={"code": f"CP{suffix[:4]}", "description": f"Complex problem {suffix}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_create_and_approve_co_cp_mapping(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO for CP mapping",
        },
    )
    co_id = co_resp.json()["id"]
    cp_id = await _create_complex_problem(client, auth_headers)

    # Create CP mapping
    create_resp = await client.post(
        "/api/v1/mappings/co-cp",
        headers=auth_headers,
        json={"course_outcome_id": co_id, "complex_problem_id": cp_id},
    )
    assert create_resp.status_code == 201, create_resp.text
    mapping_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "DRAFT"

    # Approve mapping
    approve_resp = await client.post(
        f"/api/v1/mappings/co-cp/{mapping_id}/approve",
        headers=auth_headers,
    )
    assert approve_resp.status_code == 200, approve_resp.text
    assert approve_resp.json()["status"] == "APPROVED"
    assert approve_resp.json()["approved_by_user_id"] is not None


async def test_cannot_create_co_cp_mapping_for_published_co(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO to publish",
        },
    )
    co_id = co_resp.json()["id"]

    # Publish the CO
    await client.post(f"/api/v1/course-outcomes/{co_id}/submit", headers=auth_headers)
    await client.post(f"/api/v1/course-outcomes/{co_id}/approve", headers=auth_headers)
    await client.post(f"/api/v1/course-outcomes/{co_id}/publish", headers=auth_headers)

    cp_id = await _create_complex_problem(client, auth_headers)
    resp = await client.post(
        "/api/v1/mappings/co-cp",
        headers=auth_headers,
        json={"course_outcome_id": co_id, "complex_problem_id": cp_id},
    )
    assert resp.status_code == 409


async def test_delete_co_cp_mapping(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO for CP delete test",
        },
    )
    co_id = co_resp.json()["id"]
    cp_id = await _create_complex_problem(client, auth_headers)

    create_resp = await client.post(
        "/api/v1/mappings/co-cp",
        headers=auth_headers,
        json={"course_outcome_id": co_id, "complex_problem_id": cp_id},
    )
    mapping_id = create_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/mappings/co-cp/{mapping_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 204


# ── CO-CA Mappings ────────────────────────────────────────────────────────────

async def _create_complex_activity(client: AsyncClient, headers: dict) -> str:
    suffix = uuid.uuid4().hex[:6]
    resp = await client.post(
        "/api/v1/config/complex-activities",
        headers=headers,
        json={"code": f"CA{suffix[:4]}", "description": f"Complex activity {suffix}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_create_and_approve_co_ca_mapping(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO for CA mapping",
        },
    )
    co_id = co_resp.json()["id"]
    ca_id = await _create_complex_activity(client, auth_headers)

    create_resp = await client.post(
        "/api/v1/mappings/co-ca",
        headers=auth_headers,
        json={"course_outcome_id": co_id, "complex_activity_id": ca_id},
    )
    assert create_resp.status_code == 201, create_resp.text
    mapping_id = create_resp.json()["id"]

    approve_resp = await client.post(
        f"/api/v1/mappings/co-ca/{mapping_id}/approve",
        headers=auth_headers,
    )
    assert approve_resp.status_code == 200, approve_resp.text
    assert approve_resp.json()["status"] == "APPROVED"


# ── CO-KP Mappings ────────────────────────────────────────────────────────────

async def test_create_and_approve_co_kp_mapping(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "CO for KP mapping",
        },
    )
    co_id = co_resp.json()["id"]
    kp_id = await _create_knowledge_profile(client, auth_headers)

    create_resp = await client.post(
        "/api/v1/mappings/co-kp",
        headers=auth_headers,
        json={"course_outcome_id": co_id, "knowledge_profile_id": kp_id},
    )
    assert create_resp.status_code == 201, create_resp.text
    mapping_id = create_resp.json()["id"]

    approve_resp = await client.post(
        f"/api/v1/mappings/co-kp/{mapping_id}/approve",
        headers=auth_headers,
    )
    assert approve_resp.status_code == 200, approve_resp.text
    assert approve_resp.json()["status"] == "APPROVED"


# ── CO list endpoint ──────────────────────────────────────────────────────────

async def test_list_co_by_curriculum_course(client: AsyncClient, auth_headers):
    ids = await _setup_curriculum(client, auth_headers)
    await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO1",
            "statement": "First CO",
        },
    )
    await client.post(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        json={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
            "code": "CO2",
            "statement": "Second CO",
        },
    )
    resp = await client.get(
        "/api/v1/course-outcomes",
        headers=auth_headers,
        params={
            "curriculum_id": ids["curriculum_id"],
            "course_id": ids["course_id"],
        },
    )
    assert resp.status_code == 200
    cos = resp.json()
    assert len(cos) >= 2
