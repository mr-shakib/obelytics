"""Integration tests for Assessment module endpoints."""
import uuid

import pytest
from httpx import AsyncClient


# ── Setup Helpers ─────────────────────────────────────────────────────────────

async def _setup_assessment_chain(client: AsyncClient, headers: dict) -> dict:
    """
    Create a full chain: program, curriculum, course, academic-term, section,
    section-offering, student, enrollment.
    Returns a dict with offering_id, student_enrollment_id, curriculum_id, course_id,
    student_id, program_id, section_id, term_id, batch_id.
    """
    suffix = uuid.uuid4().hex
    # Use full 128-bit UUID integer to avoid (org_id, year, season) unique constraint collisions.
    # Year range 3000–3999 * 4 seasons = 4000 combos (non-overlapping with other test files).
    full_int = int(suffix, 16)
    year = 3000 + (full_int % 1000)
    seasons = ["FALL", "SPRING", "SUMMER", "WINTER"]
    season = seasons[(full_int >> 32) % 4]

    # Department
    dept_resp = await client.post(
        "/api/v1/departments",
        headers=headers,
        json={"name": f"Assessment Dept {suffix}", "short_name": f"AD{suffix[:4]}"},
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept_id = dept_resp.json()["id"]

    # Program
    prog_resp = await client.post(
        "/api/v1/programs",
        headers=headers,
        json={
            "department_id": dept_id,
            "title": f"Assessment Program {suffix}",
            "acronym": f"AP{suffix[:4]}",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 136,
            "study_mode": "FULL_TIME",
        },
    )
    assert prog_resp.status_code == 201, prog_resp.text
    program_id = prog_resp.json()["id"]

    # Course category
    ct_resp = await client.post(
        "/api/v1/ref-data/course-categories",
        headers=headers,
        json={"name": f"Assessment Theory {suffix}"},
    )
    assert ct_resp.status_code == 201, ct_resp.text
    ct_id = ct_resp.json()["id"]

    # Course
    course_resp = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "course_category_id": ct_id,
            "course_type": "THEORY",
            "code": f"ASS{suffix[:6]}",
            "title": f"Assessment Course {suffix}",
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
            "name": f"Assessment Curriculum {suffix}",
            "code": f"ASC{suffix[:6]}",
            "effective_year": 2024,
        },
    )
    assert curr_resp.status_code == 201, curr_resp.text
    curriculum_id = curr_resp.json()["id"]

    # Batch
    batch_resp = await client.post(
        "/api/v1/batches",
        headers=headers,
        json={"curriculum_id": curriculum_id, "name": f"Batch {suffix}", "intake_year": 2024},
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
        json={"name": f"Section {suffix}", "capacity": 40},
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
            "student_id_number": f"STU-{suffix[:8]}",
            "full_name": f"Test Student {suffix}",
            "email": f"student_{suffix}@test.com",
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
        json={"name": f"Quiz {suffix}"},
    )
    assert at_resp.status_code == 201, at_resp.text
    assessment_type_id = at_resp.json()["id"]

    return {
        "offering_id": offering_id,
        "student_enrollment_id": enrollment_id,
        "curriculum_id": curriculum_id,
        "course_id": course_id,
        "student_id": student_id,
        "program_id": program_id,
        "section_id": section_id,
        "term_id": term_id,
        "batch_id": batch_id,
        "assessment_type_id": assessment_type_id,
    }


async def _setup_published_co(client: AsyncClient, headers: dict, curriculum_id: str, course_id: str) -> str:
    """Create a PUBLISHED course outcome and return its id."""
    suffix = uuid.uuid4().hex[:6]

    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=headers,
        json={
            "curriculum_id": curriculum_id,
            "course_id": course_id,
            "code": f"CO{suffix}",
            "statement": f"Test CO statement {suffix}",
        },
    )
    assert co_resp.status_code == 201, co_resp.text
    co_id = co_resp.json()["id"]

    submit_resp = await client.post(f"/api/v1/course-outcomes/{co_id}/submit", headers=headers)
    assert submit_resp.status_code == 200, submit_resp.text

    approve_resp = await client.post(f"/api/v1/course-outcomes/{co_id}/approve", headers=headers)
    assert approve_resp.status_code == 200, approve_resp.text

    publish_resp = await client.post(f"/api/v1/course-outcomes/{co_id}/publish", headers=headers)
    assert publish_resp.status_code == 200, publish_resp.text

    return co_id


# ── Student Tests ─────────────────────────────────────────────────────────────

async def test_create_student(client: AsyncClient, auth_headers):
    suffix = uuid.uuid4().hex[:8]
    resp = await client.post(
        "/api/v1/students",
        headers=auth_headers,
        json={
            "student_id_number": f"ST-{suffix}",
            "full_name": f"Jane Doe {suffix}",
            "email": f"jane_{suffix}@test.com",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["student_id_number"] == f"ST-{suffix}"
    assert data["status"] == "ACTIVE"


async def test_create_student_duplicate_id_number(client: AsyncClient, auth_headers):
    suffix = uuid.uuid4().hex[:8]
    payload = {"student_id_number": f"DUP-{suffix}", "full_name": "First Student"}
    await client.post("/api/v1/students", headers=auth_headers, json=payload)
    resp = await client.post("/api/v1/students", headers=auth_headers, json=payload)
    assert resp.status_code == 409, resp.text


async def test_get_student(client: AsyncClient, auth_headers):
    suffix = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/api/v1/students",
        headers=auth_headers,
        json={"student_id_number": f"GET-{suffix}", "full_name": "Get Me"},
    )
    student_id = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/students/{student_id}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == student_id


async def test_update_student(client: AsyncClient, auth_headers):
    suffix = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/api/v1/students",
        headers=auth_headers,
        json={"student_id_number": f"UPD-{suffix}", "full_name": "Original Name"},
    )
    student_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/v1/students/{student_id}",
        headers=auth_headers,
        json={"full_name": "Updated Name"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["full_name"] == "Updated Name"


# ── Enrollment Tests ──────────────────────────────────────────────────────────

async def test_enroll_student(client: AsyncClient, auth_headers):
    chain = await _setup_assessment_chain(client, auth_headers)
    # enrollment already created in setup — verify it exists
    resp = await client.get(
        "/api/v1/enrollments",
        headers=auth_headers,
        params={"section_offering_id": chain["offering_id"]},
    )
    assert resp.status_code == 200, resp.text
    enrollments = resp.json()
    assert any(e["student_id"] == chain["student_id"] for e in enrollments)


async def test_enroll_student_duplicate(client: AsyncClient, auth_headers):
    chain = await _setup_assessment_chain(client, auth_headers)
    # Try enrolling same student again
    resp = await client.post(
        "/api/v1/enrollments",
        headers=auth_headers,
        json={
            "student_id": chain["student_id"],
            "section_offering_id": chain["offering_id"],
        },
    )
    assert resp.status_code == 409, resp.text


# ── Assessment Tests ──────────────────────────────────────────────────────────

async def test_create_assessment_auto_creates_result_publication(client: AsyncClient, auth_headers):
    chain = await _setup_assessment_chain(client, auth_headers)

    resp = await client.post(
        "/api/v1/assessments",
        headers=auth_headers,
        json={
            "section_offering_id": chain["offering_id"],
            "assessment_type_id": chain["assessment_type_id"],
            "name": "Quiz 1",
            "total_marks": "20.00",
            "weightage_percent": "40.00",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "CONFIGURED"
    assert data["name"] == "Quiz 1"

    # Verify result publication was auto-created
    pub_resp = await client.get(
        f"/api/v1/results/{chain['offering_id']}",
        headers=auth_headers,
    )
    assert pub_resp.status_code == 200, pub_resp.text
    assert pub_resp.json()["status"] == "DRAFT"


async def test_list_assessments(client: AsyncClient, auth_headers):
    chain = await _setup_assessment_chain(client, auth_headers)
    await client.post(
        "/api/v1/assessments",
        headers=auth_headers,
        json={
            "section_offering_id": chain["offering_id"],
            "assessment_type_id": chain["assessment_type_id"],
            "name": "Assignment 1",
            "total_marks": "30.00",
            "weightage_percent": "30.00",
        },
    )
    resp = await client.get(
        "/api/v1/assessments",
        headers=auth_headers,
        params={"section_offering_id": chain["offering_id"]},
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) >= 1


async def test_update_assessment_configured(client: AsyncClient, auth_headers):
    chain = await _setup_assessment_chain(client, auth_headers)
    create_resp = await client.post(
        "/api/v1/assessments",
        headers=auth_headers,
        json={
            "section_offering_id": chain["offering_id"],
            "assessment_type_id": chain["assessment_type_id"],
            "name": "Original Quiz",
            "total_marks": "25.00",
            "weightage_percent": "100.00",
        },
    )
    assessment_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/assessments/{assessment_id}",
        headers=auth_headers,
        json={"name": "Updated Quiz"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Updated Quiz"


# ── CO Weight Tests ───────────────────────────────────────────────────────────

async def test_add_co_weight_to_assessment(client: AsyncClient, auth_headers):
    chain = await _setup_assessment_chain(client, auth_headers)
    co_id = await _setup_published_co(client, auth_headers, chain["curriculum_id"], chain["course_id"])

    create_resp = await client.post(
        "/api/v1/assessments",
        headers=auth_headers,
        json={
            "section_offering_id": chain["offering_id"],
            "assessment_type_id": chain["assessment_type_id"],
            "name": "CO Quiz",
            "total_marks": "20.00",
            "weightage_percent": "100.00",
        },
    )
    assessment_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/assessments/{assessment_id}/co-weights",
        headers=auth_headers,
        json={"course_outcome_id": co_id, "contribution_percent": "50.00"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["course_outcome_id"] == co_id
    assert data["assessment_id"] == assessment_id


async def test_add_co_weight_duplicate_rejected(client: AsyncClient, auth_headers):
    chain = await _setup_assessment_chain(client, auth_headers)
    co_id = await _setup_published_co(client, auth_headers, chain["curriculum_id"], chain["course_id"])

    create_resp = await client.post(
        "/api/v1/assessments",
        headers=auth_headers,
        json={
            "section_offering_id": chain["offering_id"],
            "assessment_type_id": chain["assessment_type_id"],
            "name": "DupCO Quiz",
            "total_marks": "20.00",
            "weightage_percent": "100.00",
        },
    )
    assessment_id = create_resp.json()["id"]
    payload = {"course_outcome_id": co_id, "contribution_percent": "50.00"}
    await client.post(f"/api/v1/assessments/{assessment_id}/co-weights", headers=auth_headers, json=payload)
    resp = await client.post(f"/api/v1/assessments/{assessment_id}/co-weights", headers=auth_headers, json=payload)
    assert resp.status_code == 409, resp.text


async def test_remove_co_weight(client: AsyncClient, auth_headers):
    chain = await _setup_assessment_chain(client, auth_headers)
    co_id = await _setup_published_co(client, auth_headers, chain["curriculum_id"], chain["course_id"])

    create_resp = await client.post(
        "/api/v1/assessments",
        headers=auth_headers,
        json={
            "section_offering_id": chain["offering_id"],
            "assessment_type_id": chain["assessment_type_id"],
            "name": "Remove CO Quiz",
            "total_marks": "20.00",
            "weightage_percent": "100.00",
        },
    )
    assessment_id = create_resp.json()["id"]

    add_resp = await client.post(
        f"/api/v1/assessments/{assessment_id}/co-weights",
        headers=auth_headers,
        json={"course_outcome_id": co_id, "contribution_percent": "50.00"},
    )
    weight_id = add_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/assessments/{assessment_id}/co-weights/{weight_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 204, del_resp.text


# ── Open Marks Tests ──────────────────────────────────────────────────────────

async def test_open_marks_succeeds_when_weightage_100(client: AsyncClient, auth_headers):
    chain = await _setup_assessment_chain(client, auth_headers)

    # Create assessment with total weightage = 100
    create_resp = await client.post(
        "/api/v1/assessments",
        headers=auth_headers,
        json={
            "section_offering_id": chain["offering_id"],
            "assessment_type_id": chain["assessment_type_id"],
            "name": "Final Exam",
            "total_marks": "100.00",
            "weightage_percent": "100.00",
        },
    )
    assessment_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/assessments/{assessment_id}/open-marks",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "MARKS_OPEN"


async def test_open_marks_fails_when_weightage_not_100(client: AsyncClient, auth_headers):
    chain = await _setup_assessment_chain(client, auth_headers)

    # Create two assessments with total weightage != 100
    resp1 = await client.post(
        "/api/v1/assessments",
        headers=auth_headers,
        json={
            "section_offering_id": chain["offering_id"],
            "assessment_type_id": chain["assessment_type_id"],
            "name": "Quiz A",
            "total_marks": "30.00",
            "weightage_percent": "30.00",
        },
    )
    assessment_id = resp1.json()["id"]

    await client.post(
        "/api/v1/assessments",
        headers=auth_headers,
        json={
            "section_offering_id": chain["offering_id"],
            "assessment_type_id": chain["assessment_type_id"],
            "name": "Quiz B",
            "total_marks": "30.00",
            "weightage_percent": "40.00",  # 30 + 40 = 70, not 100
        },
    )

    resp = await client.post(
        f"/api/v1/assessments/{assessment_id}/open-marks",
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text
    assert "100" in resp.json()["detail"]


# ── Marks Tests ───────────────────────────────────────────────────────────────

async def _setup_open_assessment(client: AsyncClient, headers: dict) -> dict:
    """Setup a chain + single assessment with 100% weightage in MARKS_OPEN state."""
    chain = await _setup_assessment_chain(client, headers)
    create_resp = await client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "section_offering_id": chain["offering_id"],
            "assessment_type_id": chain["assessment_type_id"],
            "name": "Open Marks Test",
            "total_marks": "50.00",
            "weightage_percent": "100.00",
        },
    )
    assessment_id = create_resp.json()["id"]
    open_resp = await client.post(
        f"/api/v1/assessments/{assessment_id}/open-marks",
        headers=headers,
    )
    assert open_resp.status_code == 200, open_resp.text
    chain["assessment_id"] = assessment_id
    return chain


async def test_enter_mark(client: AsyncClient, auth_headers):
    chain = await _setup_open_assessment(client, auth_headers)

    resp = await client.post(
        "/api/v1/marks",
        headers=auth_headers,
        json={
            "assessment_id": chain["assessment_id"],
            "student_enrollment_id": chain["student_enrollment_id"],
            "marks_obtained": "42.50",
            "is_absent": False,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert str(data["marks_obtained"]) == "42.50"
    assert data["is_absent"] is False


async def test_enter_mark_exceeds_total_marks(client: AsyncClient, auth_headers):
    chain = await _setup_open_assessment(client, auth_headers)

    resp = await client.post(
        "/api/v1/marks",
        headers=auth_headers,
        json={
            "assessment_id": chain["assessment_id"],
            "student_enrollment_id": chain["student_enrollment_id"],
            "marks_obtained": "999.00",  # exceeds total_marks=50
            "is_absent": False,
        },
    )
    assert resp.status_code == 422, resp.text


async def test_enter_mark_absent_with_marks_rejected(client: AsyncClient, auth_headers):
    chain = await _setup_open_assessment(client, auth_headers)

    resp = await client.post(
        "/api/v1/marks",
        headers=auth_headers,
        json={
            "assessment_id": chain["assessment_id"],
            "student_enrollment_id": chain["student_enrollment_id"],
            "marks_obtained": "20.00",
            "is_absent": True,  # conflict: absent=True but marks provided
        },
    )
    assert resp.status_code == 422, resp.text


async def test_enter_mark_absent_no_marks(client: AsyncClient, auth_headers):
    chain = await _setup_open_assessment(client, auth_headers)

    resp = await client.post(
        "/api/v1/marks",
        headers=auth_headers,
        json={
            "assessment_id": chain["assessment_id"],
            "student_enrollment_id": chain["student_enrollment_id"],
            "is_absent": True,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["is_absent"] is True
    assert resp.json()["marks_obtained"] is None


async def test_enter_mark_duplicate_rejected(client: AsyncClient, auth_headers):
    chain = await _setup_open_assessment(client, auth_headers)
    payload = {
        "assessment_id": chain["assessment_id"],
        "student_enrollment_id": chain["student_enrollment_id"],
        "marks_obtained": "30.00",
        "is_absent": False,
    }
    await client.post("/api/v1/marks", headers=auth_headers, json=payload)
    resp = await client.post("/api/v1/marks", headers=auth_headers, json=payload)
    assert resp.status_code == 409, resp.text


async def test_update_mark(client: AsyncClient, auth_headers):
    chain = await _setup_open_assessment(client, auth_headers)
    enter_resp = await client.post(
        "/api/v1/marks",
        headers=auth_headers,
        json={
            "assessment_id": chain["assessment_id"],
            "student_enrollment_id": chain["student_enrollment_id"],
            "marks_obtained": "20.00",
            "is_absent": False,
        },
    )
    mark_id = enter_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/marks/{mark_id}",
        headers=auth_headers,
        json={"marks_obtained": "35.00"},
    )
    assert resp.status_code == 200, resp.text
    assert str(resp.json()["marks_obtained"]) == "35.00"


async def test_marks_immutable_after_publish(client: AsyncClient, auth_headers):
    chain = await _setup_open_assessment(client, auth_headers)

    # Enter a mark
    enter_resp = await client.post(
        "/api/v1/marks",
        headers=auth_headers,
        json={
            "assessment_id": chain["assessment_id"],
            "student_enrollment_id": chain["student_enrollment_id"],
            "marks_obtained": "40.00",
            "is_absent": False,
        },
    )
    assert enter_resp.status_code == 201, enter_resp.text

    # Run result publication workflow
    offering_id = chain["offering_id"]

    submit_resp = await client.post(f"/api/v1/results/{offering_id}/submit", headers=auth_headers)
    assert submit_resp.status_code == 200, submit_resp.text

    ml_resp = await client.post(f"/api/v1/results/{offering_id}/approve-ml", headers=auth_headers)
    assert ml_resp.status_code == 200, ml_resp.text

    pc_resp = await client.post(f"/api/v1/results/{offering_id}/approve-pc", headers=auth_headers)
    assert pc_resp.status_code == 200, pc_resp.text

    pub_resp = await client.post(f"/api/v1/results/{offering_id}/publish", headers=auth_headers)
    assert pub_resp.status_code == 200, pub_resp.text
    assert pub_resp.json()["status"] == "PUBLISHED"

    # Try to enter another mark — should be rejected
    new_suffix = uuid.uuid4().hex[:8]

    # Create a second student and enroll
    stu_resp = await client.post(
        "/api/v1/students",
        headers=auth_headers,
        json={"student_id_number": f"IMMUT-{new_suffix}", "full_name": "Immutable Test"},
    )
    stu2_id = stu_resp.json()["id"]
    enroll_resp = await client.post(
        "/api/v1/enrollments",
        headers=auth_headers,
        json={"student_id": stu2_id, "section_offering_id": offering_id},
    )
    enroll2_id = enroll_resp.json()["id"]

    resp = await client.post(
        "/api/v1/marks",
        headers=auth_headers,
        json={
            "assessment_id": chain["assessment_id"],
            "student_enrollment_id": enroll2_id,
            "marks_obtained": "45.00",
            "is_absent": False,
        },
    )
    assert resp.status_code == 409, resp.text


# ── Result Publication Workflow ───────────────────────────────────────────────

async def test_full_result_workflow_submit_approve_publish(client: AsyncClient, auth_headers):
    chain = await _setup_open_assessment(client, auth_headers)

    await client.post(
        "/api/v1/marks",
        headers=auth_headers,
        json={
            "assessment_id": chain["assessment_id"],
            "student_enrollment_id": chain["student_enrollment_id"],
            "marks_obtained": "38.00",
            "is_absent": False,
        },
    )

    offering_id = chain["offering_id"]

    # Check initial state
    pub = await client.get(f"/api/v1/results/{offering_id}", headers=auth_headers)
    assert pub.json()["status"] == "DRAFT"

    # Submit
    sub = await client.post(f"/api/v1/results/{offering_id}/submit", headers=auth_headers)
    assert sub.status_code == 200, sub.text
    assert sub.json()["status"] == "SUBMITTED"

    # ML approve
    ml = await client.post(f"/api/v1/results/{offering_id}/approve-ml", headers=auth_headers)
    assert ml.status_code == 200, ml.text
    assert ml.json()["status"] == "ML_APPROVED"

    # PC approve
    pc = await client.post(f"/api/v1/results/{offering_id}/approve-pc", headers=auth_headers)
    assert pc.status_code == 200, pc.text
    assert pc.json()["status"] == "PC_APPROVED"

    # Publish
    pub_r = await client.post(f"/api/v1/results/{offering_id}/publish", headers=auth_headers)
    assert pub_r.status_code == 200, pub_r.text
    assert pub_r.json()["status"] == "PUBLISHED"
    assert pub_r.json()["published_at"] is not None


async def test_result_workflow_ml_reject_back_to_draft(client: AsyncClient, auth_headers):
    chain = await _setup_open_assessment(client, auth_headers)

    await client.post(
        "/api/v1/marks",
        headers=auth_headers,
        json={
            "assessment_id": chain["assessment_id"],
            "student_enrollment_id": chain["student_enrollment_id"],
            "marks_obtained": "25.00",
            "is_absent": False,
        },
    )

    offering_id = chain["offering_id"]

    end_report_body = {
        "grade_distribution": {"A": 1},
        "co_attainment": {"CO1": 55.0},
        "unattained_co_explanations": [],
        "teacher_feedback": "Initial feedback",
        "course_drive_link": "https://drive.google.com/drive/folders/test",
    }

    # Submitting the end report also submits the result publication and locks the section.
    end_report = await client.post(
        f"/api/v1/end-reports/{offering_id}/submit",
        headers=auth_headers,
        json=end_report_body,
    )
    assert end_report.status_code == 200, end_report.text
    assert end_report.json()["status"] == "SUBMITTED"

    # ML reject
    reject = await client.post(
        f"/api/v1/results/{offering_id}/reject-ml",
        headers=auth_headers,
        json={"comment": "Marks seem incorrect, please re-verify"},
    )
    assert reject.status_code == 200, reject.text
    data = reject.json()
    assert data["status"] == "DRAFT"
    assert data["ml_rejection_comment"] == "Marks seem incorrect, please re-verify"

    reopened_report = await client.get(f"/api/v1/end-reports/{offering_id}", headers=auth_headers)
    assert reopened_report.status_code == 200, reopened_report.text
    assert reopened_report.json()["status"] == "DRAFT"
    assert reopened_report.json()["submitted_at"] is None

    save_again = await client.post(
        f"/api/v1/end-reports/{offering_id}/save-draft",
        headers=auth_headers,
        json={**end_report_body, "teacher_feedback": "Revised feedback"},
    )
    assert save_again.status_code == 200, save_again.text
    assert save_again.json()["teacher_feedback"] == "Revised feedback"


async def test_cannot_submit_with_no_marks(client: AsyncClient, auth_headers):
    chain = await _setup_open_assessment(client, auth_headers)
    offering_id = chain["offering_id"]

    resp = await client.post(f"/api/v1/results/{offering_id}/submit", headers=auth_headers)
    assert resp.status_code == 422, resp.text
    assert "no marks" in resp.json()["detail"].lower()


async def test_cannot_skip_result_state_machine(client: AsyncClient, auth_headers):
    chain = await _setup_open_assessment(client, auth_headers)

    await client.post(
        "/api/v1/marks",
        headers=auth_headers,
        json={
            "assessment_id": chain["assessment_id"],
            "student_enrollment_id": chain["student_enrollment_id"],
            "marks_obtained": "15.00",
            "is_absent": False,
        },
    )

    offering_id = chain["offering_id"]

    # Try to approve ML without submitting first
    resp = await client.post(f"/api/v1/results/{offering_id}/approve-ml", headers=auth_headers)
    assert resp.status_code == 409, resp.text


async def test_cannot_enter_mark_before_open_marks(client: AsyncClient, auth_headers):
    chain = await _setup_assessment_chain(client, auth_headers)
    # Create assessment but DON'T call open-marks
    create_resp = await client.post(
        "/api/v1/assessments",
        headers=auth_headers,
        json={
            "section_offering_id": chain["offering_id"],
            "assessment_type_id": chain["assessment_type_id"],
            "name": "Closed Assessment",
            "total_marks": "30.00",
            "weightage_percent": "100.00",
        },
    )
    assessment_id = create_resp.json()["id"]

    resp = await client.post(
        "/api/v1/marks",
        headers=auth_headers,
        json={
            "assessment_id": assessment_id,
            "student_enrollment_id": chain["student_enrollment_id"],
            "marks_obtained": "20.00",
            "is_absent": False,
        },
    )
    assert resp.status_code == 409, resp.text


# ── Permission Checks ─────────────────────────────────────────────────────────

async def test_create_student_denied_for_teacher(client: AsyncClient, teacher_auth_headers):
    """Section Teacher does not have assessment.configure permission."""
    resp = await client.post(
        "/api/v1/students",
        headers=teacher_auth_headers,
        json={"student_id_number": "PERM-001", "full_name": "Perm Test"},
    )
    assert resp.status_code == 403


async def test_read_students_allowed_for_teacher(client: AsyncClient, auth_headers, teacher_auth_headers):
    resp = await client.get("/api/v1/students", headers=teacher_auth_headers)
    assert resp.status_code == 200


async def test_open_marks_denied_for_teacher(client: AsyncClient, auth_headers, teacher_auth_headers):
    """Section Teacher lacks assessment.publish_config permission."""
    chain = await _setup_assessment_chain(client, auth_headers)
    create_resp = await client.post(
        "/api/v1/assessments",
        headers=auth_headers,
        json={
            "section_offering_id": chain["offering_id"],
            "assessment_type_id": chain["assessment_type_id"],
            "name": "Perm Quiz",
            "total_marks": "40.00",
            "weightage_percent": "100.00",
        },
    )
    assessment_id = create_resp.json()["id"]
    resp = await client.post(
        f"/api/v1/assessments/{assessment_id}/open-marks",
        headers=teacher_auth_headers,
    )
    assert resp.status_code == 403


async def test_enter_marks_allowed_for_teacher(client: AsyncClient, auth_headers, teacher_auth_headers):
    """Section Teacher has marks.enter permission."""
    chain = await _setup_open_assessment(client, auth_headers)
    resp = await client.post(
        "/api/v1/marks",
        headers=teacher_auth_headers,
        json={
            "assessment_id": chain["assessment_id"],
            "student_enrollment_id": chain["student_enrollment_id"],
            "marks_obtained": "28.00",
            "is_absent": False,
        },
    )
    assert resp.status_code == 201, resp.text


async def test_approve_ml_denied_for_teacher(client: AsyncClient, auth_headers, teacher_auth_headers):
    """Section Teacher does not have result.approve.ml permission."""
    chain = await _setup_open_assessment(client, auth_headers)
    await client.post(
        "/api/v1/marks",
        headers=auth_headers,
        json={
            "assessment_id": chain["assessment_id"],
            "student_enrollment_id": chain["student_enrollment_id"],
            "marks_obtained": "30.00",
            "is_absent": False,
        },
    )
    offering_id = chain["offering_id"]
    await client.post(f"/api/v1/results/{offering_id}/submit", headers=auth_headers)
    resp = await client.post(f"/api/v1/results/{offering_id}/approve-ml", headers=teacher_auth_headers)
    assert resp.status_code == 403


async def test_approve_ml_allowed_for_ml_user(client: AsyncClient, auth_headers, ml_auth_headers):
    """Module Leader has result.approve.ml permission."""
    chain = await _setup_open_assessment(client, auth_headers)
    await client.post(
        "/api/v1/marks",
        headers=auth_headers,
        json={
            "assessment_id": chain["assessment_id"],
            "student_enrollment_id": chain["student_enrollment_id"],
            "marks_obtained": "22.00",
            "is_absent": False,
        },
    )
    offering_id = chain["offering_id"]
    await client.post(f"/api/v1/results/{offering_id}/submit", headers=auth_headers)
    resp = await client.post(f"/api/v1/results/{offering_id}/approve-ml", headers=ml_auth_headers)
    assert resp.status_code == 200, resp.text
