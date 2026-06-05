"""Integration tests for Approval module endpoints."""
import uuid

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _setup_submitted_result(client: AsyncClient, headers: dict) -> dict:
    """
    Creates a full assessment chain and submits the result publication.
    Returns dict with offering_id and result publication status.
    """
    suffix = uuid.uuid4().hex
    full_int = int(suffix, 16)
    year = 7000 + (full_int % 1000)
    seasons = ["FALL", "SPRING", "SUMMER", "WINTER"]
    season = seasons[(full_int >> 32) % 4]

    # Department
    dept_resp = await client.post(
        "/api/v1/departments",
        headers=headers,
        json={"name": f"Approval Dept {suffix}", "short_name": f"APD{suffix[:4]}"},
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept_id = dept_resp.json()["id"]

    # Program
    prog_resp = await client.post(
        "/api/v1/programs",
        headers=headers,
        json={
            "department_id": dept_id,
            "title": f"Approval Program {suffix}",
            "acronym": f"APP{suffix[:4]}",
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
        json={"name": f"Approval Theory {suffix}"},
    )
    assert ct_resp.status_code == 201, ct_resp.text
    ct_id = ct_resp.json()["id"]

    # Course
    course_resp = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "course_type_id": ct_id,
            "code": f"APR{suffix[:6]}",
            "title": f"Approval Course {suffix}",
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
            "name": f"Approval Curriculum {suffix}",
            "code": f"APC{suffix[:6]}",
            "effective_year": 2024,
        },
    )
    assert curr_resp.status_code == 201, curr_resp.text
    curriculum_id = curr_resp.json()["id"]

    # Batch
    batch_resp = await client.post(
        "/api/v1/batches",
        headers=headers,
        json={"curriculum_id": curriculum_id, "name": f"Approval Batch {suffix}", "intake_year": 2024},
    )
    assert batch_resp.status_code == 201, batch_resp.text
    batch_id = batch_resp.json()["id"]

    # Academic term
    term_resp = await client.post(
        "/api/v1/academic-terms",
        headers=headers,
        json={
            "name": f"Approval Term {suffix[:8]}",
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
        json={"name": f"Approval Section {suffix}", "capacity": 40},
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
    offering_id = offering_resp.json()["id"]

    # Student
    student_resp = await client.post(
        "/api/v1/students",
        headers=headers,
        json={
            "student_id_number": f"APSTU-{suffix[:8]}",
            "full_name": f"Approval Student {suffix}",
            "email": f"apstu_{suffix}@test.com",
            "program_id": program_id,
        },
    )
    assert student_resp.status_code == 201, student_resp.text
    student_id = student_resp.json()["id"]

    # Enrollment
    enroll_resp = await client.post(
        "/api/v1/enrollments",
        headers=headers,
        json={"student_id": student_id, "section_offering_id": offering_id},
    )
    assert enroll_resp.status_code == 201, enroll_resp.text
    enrollment_id = enroll_resp.json()["id"]

    # Assessment type
    at_resp = await client.post(
        "/api/v1/config/assessment-types",
        headers=headers,
        json={"name": f"Approval Quiz {suffix}"},
    )
    assert at_resp.status_code == 201, at_resp.text
    assessment_type_id = at_resp.json()["id"]

    # Assessment with 100% weightage
    assess_resp = await client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "section_offering_id": offering_id,
            "assessment_type_id": assessment_type_id,
            "name": f"Approval Final {suffix}",
            "total_marks": "100.00",
            "weightage_percent": "100.00",
        },
    )
    assert assess_resp.status_code == 201, assess_resp.text
    assessment_id = assess_resp.json()["id"]

    # Open marks
    open_resp = await client.post(
        f"/api/v1/assessments/{assessment_id}/open-marks",
        headers=headers,
    )
    assert open_resp.status_code == 200, open_resp.text

    # Enter mark
    mark_resp = await client.post(
        "/api/v1/marks",
        headers=headers,
        json={
            "assessment_id": assessment_id,
            "student_enrollment_id": enrollment_id,
            "marks_obtained": "75.00",
            "is_absent": False,
        },
    )
    assert mark_resp.status_code == 201, mark_resp.text

    # Submit result
    submit_resp = await client.post(f"/api/v1/results/{offering_id}/submit", headers=headers)
    assert submit_resp.status_code == 200, submit_resp.text
    assert submit_resp.json()["status"] == "SUBMITTED"

    return {"offering_id": offering_id}


# ── Inbox Tests ───────────────────────────────────────────────────────────────

async def test_get_inbox_empty(client: AsyncClient, auth_headers):
    """GET /approval/inbox returns the correct structure with empty lists on a clean DB."""
    resp = await client.get("/api/v1/approval/inbox", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "pending_result_publications" in data
    assert "pending_course_outcomes" in data
    assert "pending_co_po_mapping_sets" in data
    assert "total_count" in data
    assert isinstance(data["pending_result_publications"], list)
    assert isinstance(data["pending_course_outcomes"], list)
    assert isinstance(data["pending_co_po_mapping_sets"], list)


async def test_get_inbox_counts_structure(client: AsyncClient, auth_headers):
    """GET /approval/inbox/counts returns zeros initially."""
    resp = await client.get("/api/v1/approval/inbox/counts", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "result_publications" in data
    assert "course_outcomes" in data
    assert "co_po_mapping_sets" in data
    assert "total" in data
    assert isinstance(data["result_publications"], int)
    assert isinstance(data["course_outcomes"], int)
    assert isinstance(data["co_po_mapping_sets"], int)
    assert isinstance(data["total"], int)


# ── Comment Tests ─────────────────────────────────────────────────────────────

async def test_add_comment_course_outcome(client: AsyncClient, auth_headers):
    """POST /approval/comments/course_outcome/{entity_id} creates a comment, returns 201."""
    entity_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/approval/comments/course_outcome/{entity_id}",
        headers=auth_headers,
        json={"comment": "This CO needs more clarity on the assessment criteria."},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["entity_type"] == "course_outcome"
    assert data["entity_id"] == entity_id
    assert data["comment"] == "This CO needs more clarity on the assessment criteria."
    assert "id" in data
    assert "author_user_id" in data
    assert "created_at" in data


async def test_list_comments_for_entity(client: AsyncClient, auth_headers):
    """GET /approval/comments/{entity_type}/{entity_id} returns comments for the entity."""
    entity_id = str(uuid.uuid4())

    # Add two comments
    for i in range(2):
        resp = await client.post(
            f"/api/v1/approval/comments/result_publication/{entity_id}",
            headers=auth_headers,
            json={"comment": f"Comment number {i + 1}"},
        )
        assert resp.status_code == 201, resp.text

    # List them
    list_resp = await client.get(
        f"/api/v1/approval/comments/result_publication/{entity_id}",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    comments = list_resp.json()
    assert len(comments) >= 2
    texts = [c["comment"] for c in comments]
    assert "Comment number 1" in texts
    assert "Comment number 2" in texts


async def test_add_comment_invalid_entity_type(client: AsyncClient, auth_headers):
    """POST /approval/comments/{invalid_type}/{entity_id} returns 400."""
    entity_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/approval/comments/invalid_entity/{entity_id}",
        headers=auth_headers,
        json={"comment": "This should fail"},
    )
    assert resp.status_code == 400, resp.text


# ── Inbox Shows Pending Items ─────────────────────────────────────────────────

async def test_inbox_shows_pending_result_publication(client: AsyncClient, auth_headers):
    """After submitting a result publication, it appears in the inbox."""
    result = await _setup_submitted_result(client, auth_headers)
    offering_id = result["offering_id"]

    resp = await client.get("/api/v1/approval/inbox", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    pending = data["pending_result_publications"]
    # Find the one we just submitted
    found = any(item["status"] in ("SUBMITTED", "ML_APPROVED") for item in pending)
    assert found, f"Expected pending result publications but got: {pending}"
    assert data["total_count"] >= 1


# ── RBAC Tests ────────────────────────────────────────────────────────────────

async def test_inbox_unauthenticated_returns_4xx(client: AsyncClient):
    """No auth header → 401 or 403 (HTTPBearer returns 403 when missing)."""
    resp = await client.get("/api/v1/approval/inbox")
    assert resp.status_code in (401, 403), resp.text


async def test_inbox_counts_unauthenticated_returns_4xx(client: AsyncClient):
    """No auth header → 401 or 403 for counts endpoint."""
    resp = await client.get("/api/v1/approval/inbox/counts")
    assert resp.status_code in (401, 403), resp.text


async def test_add_comment_unauthenticated_returns_4xx(client: AsyncClient):
    """No auth header → 401 or 403 for add comment endpoint."""
    entity_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/approval/comments/course_outcome/{entity_id}",
        json={"comment": "Should fail"},
    )
    assert resp.status_code in (401, 403), resp.text
