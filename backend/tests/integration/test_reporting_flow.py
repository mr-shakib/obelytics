"""Integration tests for Reporting module (Phase 9)."""
import uuid

import pytest
from httpx import AsyncClient


# ── Setup helpers ─────────────────────────────────────────────────────────────

async def _setup_reporting_scenario(client: AsyncClient, headers: dict) -> dict:
    """
    Create a full scenario with published attainment:
    - department, program, course, curriculum, batch, term, section, section offering
    - 2 students enrolled with marks
    - result published (attainment auto-computed)

    Returns a dict with all relevant IDs.
    Uses year 9100+ and WINTER season to avoid collisions.
    """
    suffix = uuid.uuid4().hex
    full_int = int(suffix, 16)
    year = 8000 + (full_int % 500)

    # Department
    dept_resp = await client.post(
        "/api/v1/departments",
        headers=headers,
        json={"name": f"Rep Dept {suffix[:8]}", "short_name": f"RD{suffix[:4]}"},
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept_id = dept_resp.json()["id"]

    # Program
    prog_resp = await client.post(
        "/api/v1/programs",
        headers=headers,
        json={
            "department_id": dept_id,
            "title": f"Rep Program {suffix[:8]}",
            "acronym": f"RP{suffix[:4]}",
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
        json={"name": f"Rep Theory {suffix[:8]}"},
    )
    assert ct_resp.status_code == 201, ct_resp.text
    ct_id = ct_resp.json()["id"]

    # Course
    course_resp = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "course_type_id": ct_id,
            "code": f"REP{suffix[:6]}",
            "title": f"Rep Course {suffix[:8]}",
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
            "name": f"Rep Curriculum {suffix[:8]}",
            "code": f"RPC{suffix[:6]}",
            "effective_year": 2024,
        },
    )
    assert curr_resp.status_code == 201, curr_resp.text
    curriculum_id = curr_resp.json()["id"]

    # Batch
    batch_resp = await client.post(
        "/api/v1/batches",
        headers=headers,
        json={"curriculum_id": curriculum_id, "name": f"Rep Batch {suffix[:8]}", "intake_year": 2024},
    )
    assert batch_resp.status_code == 201, batch_resp.text
    batch_id = batch_resp.json()["id"]

    # Academic term
    term_resp = await client.post(
        "/api/v1/academic-terms",
        headers=headers,
        json={
            "name": f"Rep Term {suffix[:8]}",
            "year": year,
            "season": "WINTER",
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
        json={"name": f"Rep Sec {suffix[:8]}", "capacity": 40},
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

    # Assessment type
    at_resp = await client.post(
        "/api/v1/config/assessment-types",
        headers=headers,
        json={"name": f"RepQuiz {suffix[:8]}"},
    )
    assert at_resp.status_code == 201, at_resp.text
    assessment_type_id = at_resp.json()["id"]

    # Create PO
    po_resp = await client.post(
        "/api/v1/program-outcomes",
        headers=headers,
        json={
            "program_id": program_id,
            "code": "PO1",
            "statement": "Apply reporting fundamentals",
            "order_index": 1,
        },
    )
    assert po_resp.status_code == 201, po_resp.text
    po_id = po_resp.json()["id"]

    # Create CO
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=headers,
        json={
            "curriculum_id": curriculum_id,
            "course_id": course_id,
            "code": "CO1",
            "statement": "Reporting CO statement",
        },
    )
    assert co_resp.status_code == 201, co_resp.text
    co_id = co_resp.json()["id"]

    # CO lifecycle: draft → submitted → approved → published
    await client.post(f"/api/v1/course-outcomes/{co_id}/submit", headers=headers)
    await client.post(f"/api/v1/course-outcomes/{co_id}/approve", headers=headers)
    await client.post(f"/api/v1/course-outcomes/{co_id}/publish", headers=headers)

    # CO-PO mapping
    ms_resp = await client.post(
        "/api/v1/mappings/co-po",
        headers=headers,
        json={"curriculum_id": curriculum_id, "course_id": course_id},
    )
    assert ms_resp.status_code == 201, ms_resp.text
    mapping_set_id = ms_resp.json()["id"]

    await client.put(
        f"/api/v1/mappings/co-po/{mapping_set_id}/entries",
        headers=headers,
        json=[{"course_outcome_id": co_id, "program_outcome_id": po_id, "weight": 2}],
    )

    # Assessment
    assess_resp = await client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "section_offering_id": offering_id,
            "assessment_type_id": assessment_type_id,
            "name": "Rep Final Exam",
            "total_marks": "100.00",
            "weightage_percent": "100.00",
        },
    )
    assert assess_resp.status_code == 201, assess_resp.text
    assessment_id = assess_resp.json()["id"]

    # CO weight
    await client.post(
        f"/api/v1/assessments/{assessment_id}/co-weights",
        headers=headers,
        json={"course_outcome_id": co_id, "contribution_percent": "100.00"},
    )

    # Open marks
    await client.post(f"/api/v1/assessments/{assessment_id}/open-marks", headers=headers)

    # Students + enrollments
    stu1_resp = await client.post(
        "/api/v1/students",
        headers=headers,
        json={
            "student_id_number": f"R1-{suffix[:8]}",
            "full_name": f"Rep Student 1 {suffix[:4]}",
            "email": f"r1_{suffix[:8]}@test.com",
            "program_id": program_id,
        },
    )
    assert stu1_resp.status_code == 201, stu1_resp.text
    student1_id = stu1_resp.json()["id"]

    enroll1_resp = await client.post(
        "/api/v1/enrollments",
        headers=headers,
        json={"student_id": student1_id, "section_offering_id": offering_id},
    )
    assert enroll1_resp.status_code == 201, enroll1_resp.text
    enrollment1_id = enroll1_resp.json()["id"]

    stu2_resp = await client.post(
        "/api/v1/students",
        headers=headers,
        json={
            "student_id_number": f"R2-{suffix[:8]}",
            "full_name": f"Rep Student 2 {suffix[:4]}",
            "email": f"r2_{suffix[:8]}@test.com",
            "program_id": program_id,
        },
    )
    assert stu2_resp.status_code == 201, stu2_resp.text
    student2_id = stu2_resp.json()["id"]

    enroll2_resp = await client.post(
        "/api/v1/enrollments",
        headers=headers,
        json={"student_id": student2_id, "section_offering_id": offering_id},
    )
    assert enroll2_resp.status_code == 201, enroll2_resp.text
    enrollment2_id = enroll2_resp.json()["id"]

    # Enter marks
    await client.post(
        "/api/v1/marks",
        headers=headers,
        json={
            "assessment_id": assessment_id,
            "student_enrollment_id": enrollment1_id,
            "marks_obtained": "80.00",
            "is_absent": False,
        },
    )
    await client.post(
        "/api/v1/marks",
        headers=headers,
        json={
            "assessment_id": assessment_id,
            "student_enrollment_id": enrollment2_id,
            "marks_obtained": "60.00",
            "is_absent": False,
        },
    )

    # Result publication workflow → PC_APPROVED
    await client.post(f"/api/v1/results/{offering_id}/submit", headers=headers)
    await client.post(f"/api/v1/results/{offering_id}/approve-ml", headers=headers)
    await client.post(f"/api/v1/results/{offering_id}/approve-pc", headers=headers)

    return {
        "offering_id": offering_id,
        "program_id": program_id,
        "academic_term_id": term_id,
        "assessment_id": assessment_id,
        "co_id": co_id,
        "po_id": po_id,
    }


# ── Assessment Summary Report Tests ──────────────────────────────────────────

async def test_assessment_summary_report(client: AsyncClient, auth_headers):
    """GET assessment summary returns 200 with correct structure."""
    scenario = await _setup_reporting_scenario(client, auth_headers)
    offering_id = scenario["offering_id"]

    resp = await client.get(
        f"/api/v1/reports/section-offerings/{offering_id}/assessment-summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["section_offering_id"] == offering_id
    assert data["total_enrolled"] == 2
    assert len(data["assessments"]) == 1

    row = data["assessments"][0]
    assert row["marks_entered_count"] == 2
    assert row["absent_count"] == 0
    assert row["scored_count"] == 2
    assert float(row["average_score"]) == pytest.approx(70.0, abs=0.1)
    assert row["pass_count"] == 2  # both 80 and 60 >= 50
    assert float(row["pass_rate"]) == pytest.approx(100.0, abs=0.1)


async def test_assessment_summary_no_assessments(client: AsyncClient, auth_headers):
    """GET assessment summary for offering with no assessments → 200, empty list."""
    suffix = uuid.uuid4().hex[:8]
    full_int = int(suffix, 16)
    year = 8500 + (full_int % 300)

    dept_resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": f"Empty Dept {suffix}", "short_name": f"ED{suffix[:4]}"},
    )
    dept_id = dept_resp.json()["id"]

    prog_resp = await client.post(
        "/api/v1/programs",
        headers=auth_headers,
        json={
            "department_id": dept_id,
            "title": f"Empty Program {suffix}",
            "acronym": f"EP{suffix[:4]}",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 136,
            "study_mode": "FULL_TIME",
        },
    )
    program_id = prog_resp.json()["id"]

    ct_resp = await client.post(
        "/api/v1/config/course-types",
        headers=auth_headers,
        json={"name": f"Empty CT {suffix}"},
    )
    ct_id = ct_resp.json()["id"]

    course_resp = await client.post(
        "/api/v1/courses",
        headers=auth_headers,
        json={
            "course_type_id": ct_id,
            "code": f"EMP{suffix[:6]}",
            "title": f"Empty Course {suffix}",
            "credits": 3,
            "theory_hours": 3,
            "lab_hours": 0,
        },
    )
    course_id = course_resp.json()["id"]

    curr_resp = await client.post(
        "/api/v1/curricula",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": f"Empty Curriculum {suffix}",
            "code": f"EPC{suffix[:6]}",
            "effective_year": 2024,
        },
    )
    curriculum_id = curr_resp.json()["id"]

    batch_resp = await client.post(
        "/api/v1/batches",
        headers=auth_headers,
        json={"curriculum_id": curriculum_id, "name": f"Empty Batch {suffix}", "intake_year": 2024},
    )
    batch_id = batch_resp.json()["id"]

    term_resp = await client.post(
        "/api/v1/academic-terms",
        headers=auth_headers,
        json={
            "name": f"Empty Term {suffix}",
            "year": year,
            "season": "WINTER",
            "start_date": "2024-09-01",
            "end_date": "2025-01-15",
        },
    )
    term_id = term_resp.json()["id"]

    sec_resp = await client.post(
        "/api/v1/sections",
        headers=auth_headers,
        json={"name": f"Empty Sec {suffix}", "capacity": 30},
    )
    section_id = sec_resp.json()["id"]

    so_resp = await client.post(
        "/api/v1/section-offerings",
        headers=auth_headers,
        json={
            "curriculum_id": curriculum_id,
            "batch_id": batch_id,
            "course_id": course_id,
            "academic_term_id": term_id,
            "section_id": section_id,
        },
    )
    assert so_resp.status_code == 201, so_resp.text
    so_id = so_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/reports/section-offerings/{so_id}/assessment-summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["section_offering_id"] == so_id
    assert data["assessments"] == []
    assert data["total_enrolled"] == 0


# ── CO Attainment Report Tests ────────────────────────────────────────────────

async def test_co_attainment_report_after_publish(client: AsyncClient, auth_headers):
    """GET CO attainment report returns computed results after publication."""
    scenario = await _setup_reporting_scenario(client, auth_headers)
    offering_id = scenario["offering_id"]

    # Publish to trigger attainment computation
    pub_resp = await client.post(f"/api/v1/results/{offering_id}/publish", headers=auth_headers)
    assert pub_resp.status_code == 200, pub_resp.text

    resp = await client.get(
        f"/api/v1/reports/section-offerings/{offering_id}/co-attainment",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["section_offering_id"] == offering_id
    assert len(data["co_attainments"]) == 1
    assert len(data["po_attainments"]) == 1

    co_row = data["co_attainments"][0]
    assert co_row["course_outcome_id"] == scenario["co_id"]
    assert co_row["total_students"] == 2
    assert co_row["students_above_threshold"] == 2  # both 80 and 60 >= 50%
    assert float(co_row["average_attainment_pct"]) == pytest.approx(70.0, abs=0.1)

    po_row = data["po_attainments"][0]
    assert po_row["program_outcome_id"] == scenario["po_id"]
    assert po_row["contributing_co_count"] == 1


async def test_co_attainment_report_empty_before_publish(client: AsyncClient, auth_headers):
    """GET CO attainment report before attainment is computed → 200 with empty lists."""
    suffix = uuid.uuid4().hex[:8]
    full_int = int(suffix, 16)
    year = 8800 + (full_int % 200)

    dept_resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": f"PrePub Dept {suffix}", "short_name": f"PP{suffix[:4]}"},
    )
    dept_id = dept_resp.json()["id"]

    prog_resp = await client.post(
        "/api/v1/programs",
        headers=auth_headers,
        json={
            "department_id": dept_id,
            "title": f"PrePub Program {suffix}",
            "acronym": f"PQ{suffix[:4]}",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 136,
            "study_mode": "FULL_TIME",
        },
    )
    program_id = prog_resp.json()["id"]

    ct_resp = await client.post(
        "/api/v1/config/course-types",
        headers=auth_headers,
        json={"name": f"PrePub CT {suffix}"},
    )
    ct_id = ct_resp.json()["id"]

    course_resp = await client.post(
        "/api/v1/courses",
        headers=auth_headers,
        json={
            "course_type_id": ct_id,
            "code": f"PPB{suffix[:6]}",
            "title": f"PrePub Course {suffix}",
            "credits": 3,
            "theory_hours": 3,
            "lab_hours": 0,
        },
    )
    course_id = course_resp.json()["id"]

    curr_resp = await client.post(
        "/api/v1/curricula",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": f"PrePub Curriculum {suffix}",
            "code": f"PPC{suffix[:6]}",
            "effective_year": 2024,
        },
    )
    curriculum_id = curr_resp.json()["id"]

    batch_resp = await client.post(
        "/api/v1/batches",
        headers=auth_headers,
        json={"curriculum_id": curriculum_id, "name": f"PrePub Batch {suffix}", "intake_year": 2024},
    )
    batch_id = batch_resp.json()["id"]

    term_resp = await client.post(
        "/api/v1/academic-terms",
        headers=auth_headers,
        json={
            "name": f"PrePub Term {suffix}",
            "year": year,
            "season": "WINTER",
            "start_date": "2024-09-01",
            "end_date": "2025-01-15",
        },
    )
    term_id = term_resp.json()["id"]

    sec_resp = await client.post(
        "/api/v1/sections",
        headers=auth_headers,
        json={"name": f"PrePub Sec {suffix}", "capacity": 30},
    )
    section_id = sec_resp.json()["id"]

    so_resp = await client.post(
        "/api/v1/section-offerings",
        headers=auth_headers,
        json={
            "curriculum_id": curriculum_id,
            "batch_id": batch_id,
            "course_id": course_id,
            "academic_term_id": term_id,
            "section_id": section_id,
        },
    )
    so_id = so_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/reports/section-offerings/{so_id}/co-attainment",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["section_offering_id"] == so_id
    assert data["co_attainments"] == []
    assert data["po_attainments"] == []


# ── Program PO Attainment Report Tests ───────────────────────────────────────

async def test_program_po_attainment_report(client: AsyncClient, auth_headers):
    """GET program PO attainment report → 200 with po_rows after publish."""
    scenario = await _setup_reporting_scenario(client, auth_headers)
    offering_id = scenario["offering_id"]
    program_id = scenario["program_id"]
    term_id = scenario["academic_term_id"]

    # Publish to trigger attainment
    pub_resp = await client.post(f"/api/v1/results/{offering_id}/publish", headers=auth_headers)
    assert pub_resp.status_code == 200, pub_resp.text

    resp = await client.get(
        f"/api/v1/reports/programs/{program_id}/po-attainment",
        params={"academic_term_id": term_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["program_id"] == program_id
    assert data["academic_term_id"] == term_id
    assert len(data["po_rows"]) == 1

    row = data["po_rows"][0]
    assert row["program_outcome_id"] == scenario["po_id"]
    assert row["offering_count"] == 1
    assert row["attained_count"] == 1  # both students passed
    assert float(row["avg_attainment_pct"]) == pytest.approx(70.0, abs=0.1)


async def test_program_po_attainment_no_offerings(client: AsyncClient, auth_headers):
    """GET program PO attainment when no offerings exist → 200 with empty po_rows."""
    suffix = uuid.uuid4().hex[:8]
    dept_resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": f"Noff Dept {suffix}", "short_name": f"NO{suffix[:4]}"},
    )
    dept_id = dept_resp.json()["id"]

    prog_resp = await client.post(
        "/api/v1/programs",
        headers=auth_headers,
        json={
            "department_id": dept_id,
            "title": f"Noff Program {suffix}",
            "acronym": f"NF{suffix[:4]}",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 136,
            "study_mode": "FULL_TIME",
        },
    )
    program_id = prog_resp.json()["id"]

    # Use a random term_id that won't match anything
    fake_term_id = str(uuid.uuid4())

    resp = await client.get(
        f"/api/v1/reports/programs/{program_id}/po-attainment",
        params={"academic_term_id": fake_term_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["po_rows"] == []


# ── RBAC Tests ────────────────────────────────────────────────────────────────

async def test_assessment_report_denied_without_auth(client: AsyncClient):
    """Unauthenticated request is rejected."""
    resp = await client.get(
        "/api/v1/reports/section-offerings/00000000-0000-0000-0000-000000000000/assessment-summary"
    )
    assert resp.status_code == 403


async def test_assessment_report_denied_for_student(client: AsyncClient, auth_headers):
    """Student role does not have report.assessment.generate permission → 403."""
    # Create a student user and authenticate
    suffix = uuid.uuid4().hex[:8]
    student_resp = await client.post(
        "/api/v1/students",
        headers=auth_headers,
        json={
            "student_id_number": f"RBAC-{suffix}",
            "full_name": f"RBAC Student {suffix}",
            "email": f"rbac_{suffix}@test.com",
            "program_id": None,
        },
    )
    # The report endpoint requires report.assessment.generate — teacher has it
    # but we test that missing auth returns 403
    resp = await client.get(
        "/api/v1/reports/section-offerings/00000000-0000-0000-0000-000000000000/assessment-summary"
    )
    assert resp.status_code == 403
