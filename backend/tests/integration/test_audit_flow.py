"""Integration tests for Audit module endpoints."""
import uuid

import pytest
from httpx import AsyncClient


# ── Setup helpers ─────────────────────────────────────────────────────────────

async def _setup_co_chain(client: AsyncClient, headers: dict) -> dict:
    """
    Create a minimal chain: dept, program, course-type, course, curriculum, batch,
    academic-term, section, section-offering, and a CO for that course.
    Returns dict with co_id, curriculum_id, course_id.
    """
    suffix = uuid.uuid4().hex
    full_int = int(suffix, 16)
    year = 7000 + (full_int % 2000)
    seasons = ["FALL", "SPRING", "SUMMER", "WINTER"]
    season = seasons[(full_int >> 32) % 4]

    # Department
    dept_resp = await client.post(
        "/api/v1/departments",
        headers=headers,
        json={"name": f"Audit Dept {suffix[:8]}", "short_name": f"AU{suffix[:4]}"},
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept_id = dept_resp.json()["id"]

    # Program
    prog_resp = await client.post(
        "/api/v1/programs",
        headers=headers,
        json={
            "department_id": dept_id,
            "title": f"Audit Program {suffix[:8]}",
            "acronym": f"AP{suffix[:4]}",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 136,
            "study_mode": "FULL_TIME",
        },
    )
    assert prog_resp.status_code == 201, prog_resp.text
    program_id = prog_resp.json()["id"]

    # Course type
    ct_resp = await client.post(
        "/api/v1/config/course-types",
        headers=headers,
        json={"name": f"Audit Theory {suffix[:8]}"},
    )
    assert ct_resp.status_code == 201, ct_resp.text
    ct_id = ct_resp.json()["id"]

    # Course
    course_resp = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "course_type_id": ct_id,
            "code": f"AUD{suffix[:6]}",
            "title": f"Audit Course {suffix[:8]}",
            "credits": 3,
            "theory_hours": 3,
            "lab_hours": 0,
        },
    )
    assert course_resp.status_code == 201, course_resp.text
    course_id = course_resp.json()["id"]

    # Curriculum
    curr_resp = await client.post(
        "/api/v1/curricula",
        headers=headers,
        json={
            "program_id": program_id,
            "name": f"Audit Curriculum {suffix[:8]}",
            "code": f"AUC{suffix[:6]}",
            "effective_year": 2024,
        },
    )
    assert curr_resp.status_code == 201, curr_resp.text
    curriculum_id = curr_resp.json()["id"]

    # Batch
    batch_resp = await client.post(
        "/api/v1/batches",
        headers=headers,
        json={"curriculum_id": curriculum_id, "name": f"Batch {suffix[:8]}", "intake_year": 2024},
    )
    assert batch_resp.status_code == 201, batch_resp.text
    batch_id = batch_resp.json()["id"]

    # Academic term
    term_resp = await client.post(
        "/api/v1/academic-terms",
        headers=headers,
        json={
            "name": f"Term {suffix[:8]}",
            "year": year,
            "season": season,
            "start_date": "2024-09-01",
            "end_date": "2025-01-15",
        },
    )
    assert term_resp.status_code == 201, term_resp.text
    term_id = term_resp.json()["id"]

    # Section
    sec_resp = await client.post(
        "/api/v1/sections",
        headers=headers,
        json={"name": f"Section {suffix[:8]}", "capacity": 40},
    )
    assert sec_resp.status_code == 201, sec_resp.text
    section_id = sec_resp.json()["id"]

    # Section offering
    offering_resp = await client.post(
        "/api/v1/section-offerings",
        headers=headers,
        json={
            "curriculum_id": curriculum_id,
            "batch_id": batch_id,
            "course_id": course_id,
            "academic_term_id": term_id,
            "section_id": section_id,
        },
    )
    assert offering_resp.status_code == 201, offering_resp.text

    # Course Outcome
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=headers,
        json={
            "curriculum_id": curriculum_id,
            "course_id": course_id,
            "code": f"CO{suffix[:6]}",
            "statement": f"Audit test CO statement {suffix[:8]}",
        },
    )
    assert co_resp.status_code == 201, co_resp.text
    co_id = co_resp.json()["id"]

    return {
        "co_id": co_id,
        "curriculum_id": curriculum_id,
        "course_id": course_id,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log_after_co_submit(client: AsyncClient, auth_headers: dict):
    """After CO submit, audit log shows CO_SUBMITTED."""
    chain = await _setup_co_chain(client, auth_headers)
    co_id = chain["co_id"]

    # Submit the CO
    submit_resp = await client.post(
        f"/api/v1/course-outcomes/{co_id}/submit",
        headers=auth_headers,
    )
    assert submit_resp.status_code == 200, submit_resp.text

    # Check audit log
    audit_resp = await client.get(
        "/api/v1/audit/logs",
        headers=auth_headers,
        params={"entity_type": "course_outcome", "entity_id": co_id},
    )
    assert audit_resp.status_code == 200, audit_resp.text
    logs = audit_resp.json()
    assert len(logs) >= 1
    actions = [l["action"] for l in logs]
    assert "CO_SUBMITTED" in actions

    # Verify the log entry details
    submitted_log = next(l for l in logs if l["action"] == "CO_SUBMITTED")
    assert submitted_log["entity_type"] == "course_outcome"
    assert submitted_log["entity_id"] == co_id
    assert submitted_log["before_status"] == "DRAFT"
    assert submitted_log["after_status"] == "SUBMITTED"


@pytest.mark.asyncio
async def test_audit_log_after_co_approve(client: AsyncClient, auth_headers: dict):
    """After CO approve, audit log shows CO_APPROVED."""
    chain = await _setup_co_chain(client, auth_headers)
    co_id = chain["co_id"]

    # Submit then approve
    await client.post(f"/api/v1/course-outcomes/{co_id}/submit", headers=auth_headers)
    approve_resp = await client.post(
        f"/api/v1/course-outcomes/{co_id}/approve",
        headers=auth_headers,
    )
    assert approve_resp.status_code == 200, approve_resp.text

    # Check audit log
    audit_resp = await client.get(
        "/api/v1/audit/logs",
        headers=auth_headers,
        params={"entity_type": "course_outcome", "entity_id": co_id},
    )
    assert audit_resp.status_code == 200, audit_resp.text
    logs = audit_resp.json()
    actions = [l["action"] for l in logs]
    assert "CO_APPROVED" in actions

    approved_log = next(l for l in logs if l["action"] == "CO_APPROVED")
    assert approved_log["after_status"] == "APPROVED"


@pytest.mark.asyncio
async def test_audit_log_org_wide(client: AsyncClient, auth_headers: dict):
    """GET /audit/logs without entity_id returns org-wide logs."""
    chain = await _setup_co_chain(client, auth_headers)
    co_id = chain["co_id"]

    # Create at least one log entry
    await client.post(f"/api/v1/course-outcomes/{co_id}/submit", headers=auth_headers)

    # Fetch org-wide logs
    resp = await client.get("/api/v1/audit/logs", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    logs = resp.json()
    assert isinstance(logs, list)
    assert len(logs) >= 1


@pytest.mark.asyncio
async def test_audit_log_requires_permission(
    client: AsyncClient, teacher_auth_headers: dict
):
    """Section Teacher (no system.audit.read) gets 403."""
    resp = await client.get("/api/v1/audit/logs", headers=teacher_auth_headers)
    assert resp.status_code == 403, resp.text
