"""Integration tests for Attainment module (Phase 6)."""
import uuid

import pytest
from httpx import AsyncClient


# ── Setup helpers ─────────────────────────────────────────────────────────────

async def _setup_attainment_scenario(client: AsyncClient, headers: dict) -> dict:
    """
    Create a full scenario ready for attainment computation:
    - Department, Program, CourseCategory, Course, Curriculum
    - Batch, AcademicTerm, Section, SectionOffering
    - 2 students enrolled
    - 1 assessment (100% weightage) with 1 CO weight
    - Both students have marks entered
    - PO created and CO-PO mapping set up
    - Result publication walked through to PC_APPROVED (ready to publish)

    Returns a dict with all relevant IDs.
    """
    suffix = uuid.uuid4().hex
    full_int = int(suffix, 16)
    year = 4000 + (full_int % 500)
    seasons = ["FALL", "SPRING", "SUMMER", "WINTER"]
    season = seasons[(full_int >> 32) % 4]

    # Department
    dept_resp = await client.post(
        "/api/v1/departments",
        headers=headers,
        json={"name": f"Att Dept {suffix[:8]}", "short_name": f"AT{suffix[:4]}"},
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept_id = dept_resp.json()["id"]

    # Program
    prog_resp = await client.post(
        "/api/v1/programs",
        headers=headers,
        json={
            "department_id": dept_id,
            "title": f"Att Program {suffix[:8]}",
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
        json={"name": f"Att Theory {suffix[:8]}"},
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
            "code": f"ATT{suffix[:6]}",
            "title": f"Att Course {suffix[:8]}",
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
            "name": f"Att Curriculum {suffix[:8]}",
            "code": f"ATC{suffix[:6]}",
            "effective_year": 2024,
        },
    )
    assert curr_resp.status_code == 201, curr_resp.text
    curriculum_id = curr_resp.json()["id"]

    # Batch
    batch_resp = await client.post(
        "/api/v1/batches",
        headers=headers,
        json={
            "curriculum_id": curriculum_id,
            "name": f"Batch {suffix[:8]}",
            "start_date": "2024-09-01",
            "term_system": "SEMESTER",
            "num_semesters": 8,
        },
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
        json={"name": f"Sec {suffix[:8]}", "capacity": 40},
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
        "/api/v1/ref-data/assessment-types",
        headers=headers,
        json={"name": f"AttQuiz {suffix[:8]}"},
    )
    assert at_resp.status_code == 201, at_resp.text
    assessment_type_id = at_resp.json()["id"]

    # Create PO
    po_resp = await client.post(
        "/api/v1/program-outcomes",
        headers=headers,
        json={
            "program_id": program_id,
            "code": f"PO1-{suffix[:8]}",
            "statement": "Apply attainment fundamentals",
            "order_index": 1,
        },
    )
    assert po_resp.status_code == 201, po_resp.text
    po_id = po_resp.json()["id"]

    # Create CO (goes through DRAFT -> SUBMITTED -> APPROVED -> PUBLISHED)
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=headers,
        json={
            "curriculum_id": curriculum_id,
            "course_id": course_id,
            "code": "CO1",
            "statement": "Attainment CO statement",
        },
    )
    assert co_resp.status_code == 201, co_resp.text
    co_id = co_resp.json()["id"]

    submit_co = await client.post(f"/api/v1/course-outcomes/{co_id}/submit", headers=headers)
    assert submit_co.status_code == 200, submit_co.text
    approve_co = await client.post(f"/api/v1/course-outcomes/{co_id}/approve", headers=headers)
    assert approve_co.status_code == 200, approve_co.text
    publish_co = await client.post(f"/api/v1/course-outcomes/{co_id}/publish", headers=headers)
    assert publish_co.status_code == 200, publish_co.text

    # CO-PO mapping
    ms_resp = await client.post(
        "/api/v1/mappings/co-po",
        headers=headers,
        json={"curriculum_id": curriculum_id, "course_id": course_id},
    )
    assert ms_resp.status_code == 201, ms_resp.text
    mapping_set_id = ms_resp.json()["id"]

    entries_resp = await client.put(
        f"/api/v1/mappings/co-po/{mapping_set_id}/entries",
        headers=headers,
        json=[{"course_outcome_id": co_id, "program_outcome_id": po_id, "weight": 2}],
    )
    assert entries_resp.status_code == 200, entries_resp.text

    # Create assessment with 100% weightage
    assess_resp = await client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "section_offering_id": offering_id,
            "assessment_type_id": assessment_type_id,
            "name": "Final Exam",
            "total_marks": "100.00",
            "weightage_percent": "100.00",
        },
    )
    assert assess_resp.status_code == 201, assess_resp.text
    assessment_id = assess_resp.json()["id"]

    # Add CO weight to assessment
    co_weight_resp = await client.post(
        f"/api/v1/assessments/{assessment_id}/co-weights",
        headers=headers,
        json={"course_outcome_id": co_id, "contribution_percent": "100.00"},
    )
    assert co_weight_resp.status_code == 201, co_weight_resp.text

    # Open marks
    open_resp = await client.post(
        f"/api/v1/assessments/{assessment_id}/open-marks",
        headers=headers,
    )
    assert open_resp.status_code == 200, open_resp.text

    # Create student 1 and enroll
    stu1_resp = await client.post(
        "/api/v1/students",
        headers=headers,
        json={
            "student_id_number": f"ATT1-{suffix[:8]}",
            "full_name": f"Attainment Student 1 {suffix[:4]}",
            "email": f"att1_{suffix[:8]}@test.com",
            "program_id": program_id,
            "batch_id": batch_id,
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

    # Create student 2 and enroll
    stu2_resp = await client.post(
        "/api/v1/students",
        headers=headers,
        json={
            "student_id_number": f"ATT2-{suffix[:8]}",
            "full_name": f"Attainment Student 2 {suffix[:4]}",
            "email": f"att2_{suffix[:8]}@test.com",
            "program_id": program_id,
            "batch_id": batch_id,
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

    # Enter marks: student1 = 75/100 (above 50% threshold), student2 = 40/100 (below)
    mark1_resp = await client.post(
        "/api/v1/marks",
        headers=headers,
        json={
            "assessment_id": assessment_id,
            "student_enrollment_id": enrollment1_id,
            "marks_obtained": "75.00",
            "is_absent": False,
        },
    )
    assert mark1_resp.status_code == 201, mark1_resp.text

    mark2_resp = await client.post(
        "/api/v1/marks",
        headers=headers,
        json={
            "assessment_id": assessment_id,
            "student_enrollment_id": enrollment2_id,
            "marks_obtained": "40.00",
            "is_absent": False,
        },
    )
    assert mark2_resp.status_code == 201, mark2_resp.text

    # Walk through result publication workflow to PC_APPROVED
    submit_resp = await client.post(f"/api/v1/results/{offering_id}/submit", headers=headers)
    assert submit_resp.status_code == 200, submit_resp.text

    ml_resp = await client.post(f"/api/v1/results/{offering_id}/approve-ml", headers=headers)
    assert ml_resp.status_code == 200, ml_resp.text

    pc_resp = await client.post(f"/api/v1/results/{offering_id}/approve-pc", headers=headers)
    assert pc_resp.status_code == 200, pc_resp.text

    return {
        "offering_id": offering_id,
        "curriculum_id": curriculum_id,
        "course_id": course_id,
        "program_id": program_id,
        "po_id": po_id,
        "co_id": co_id,
        "assessment_id": assessment_id,
        "enrollment1_id": enrollment1_id,
        "enrollment2_id": enrollment2_id,
        "mapping_set_id": mapping_set_id,
    }


# ── Config Tests ──────────────────────────────────────────────────────────────

async def test_get_config_auto_creates_default(client: AsyncClient, auth_headers):
    """GET /attainment/config auto-creates org-wide default with 50/50 thresholds."""
    resp = await client.get("/api/v1/attainment/config", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["program_id"] is None
    assert float(data["threshold_co_score_pct"]) == 50.0


async def test_update_org_level_config(client: AsyncClient, auth_headers):
    """PATCH /attainment/config updates org-wide thresholds."""
    resp = await client.patch(
        "/api/v1/attainment/config",
        headers=auth_headers,
        json={"threshold_co_score_pct": "55.00"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert float(data["threshold_co_score_pct"]) == 55.0

    # Reset back to 50 for other tests
    await client.patch(
        "/api/v1/attainment/config",
        headers=auth_headers,
        json={"threshold_co_score_pct": "50.00"},
    )


async def test_get_program_config_auto_falls_back_to_org(client: AsyncClient, auth_headers):
    """GET /attainment/config/programs/{id} falls back to org default if no program-specific config."""
    # Create a fresh program
    suffix = uuid.uuid4().hex[:8]
    dept_resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": f"Cfg Dept {suffix}", "short_name": f"CD{suffix[:4]}"},
    )
    dept_id = dept_resp.json()["id"]
    prog_resp = await client.post(
        "/api/v1/programs",
        headers=auth_headers,
        json={
            "department_id": dept_id,
            "title": f"Cfg Program {suffix}",
            "acronym": f"CP{suffix[:4]}",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 136,
            "study_mode": "FULL_TIME",
        },
    )
    assert prog_resp.status_code == 201, prog_resp.text
    program_id = prog_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/attainment/config/programs/{program_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    # Falls back to org-wide default
    assert resp.json()["program_id"] is None


async def test_update_program_specific_config(client: AsyncClient, auth_headers):
    """PATCH /attainment/config/programs/{id} creates program-specific config."""
    suffix = uuid.uuid4().hex[:8]
    dept_resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": f"PrgCfg Dept {suffix}", "short_name": f"PD{suffix[:4]}"},
    )
    dept_id = dept_resp.json()["id"]
    prog_resp = await client.post(
        "/api/v1/programs",
        headers=auth_headers,
        json={
            "department_id": dept_id,
            "title": f"PrgCfg Program {suffix}",
            "acronym": f"PP{suffix[:4]}",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 136,
            "study_mode": "FULL_TIME",
        },
    )
    program_id = prog_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/attainment/config/programs/{program_id}",
        headers=auth_headers,
        json={"threshold_co_score_pct": "70.00"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["program_id"] == program_id
    assert float(data["threshold_co_score_pct"]) == 70.0


# ── Attainment Computation Tests ──────────────────────────────────────────────

async def test_attainment_auto_computed_on_publish(client: AsyncClient, auth_headers):
    """Publishing a result publication triggers attainment computation."""
    scenario = await _setup_attainment_scenario(client, auth_headers)
    offering_id = scenario["offering_id"]

    # Publish the result
    pub_resp = await client.post(f"/api/v1/results/{offering_id}/publish", headers=auth_headers)
    assert pub_resp.status_code == 200, pub_resp.text
    assert pub_resp.json()["status"] == "PUBLISHED"

    # Attainment should now be computed
    summary_resp = await client.get(
        f"/api/v1/attainment/section-offerings/{offering_id}/summary",
        headers=auth_headers,
    )
    assert summary_resp.status_code == 200, summary_resp.text
    data = summary_resp.json()
    assert data["section_offering_id"] == offering_id
    assert len(data["co_results"]) == 1
    co_result = data["co_results"][0]
    assert co_result["course_outcome_id"] == scenario["co_id"]
    assert co_result["total_students"] == 2
    # student1 scored 75% (above 50%), student2 scored 40% (below 50%)
    # average = (75 + 40) / 2 = 57.5
    assert float(co_result["average_attainment_pct"]) == pytest.approx(57.5, abs=0.1)
    assert co_result["students_above_threshold"] == 1
    # 1/2 = 50% >= 50% threshold -> attained
    assert co_result["is_attained"] is True


async def test_po_attainment_results_exist_after_publish(client: AsyncClient, auth_headers):
    """PO attainment results are computed based on student-level PO score aggregation."""
    scenario = await _setup_attainment_scenario(client, auth_headers)
    offering_id = scenario["offering_id"]

    pub_resp = await client.post(f"/api/v1/results/{offering_id}/publish", headers=auth_headers)
    assert pub_resp.status_code == 200, pub_resp.text

    summary_resp = await client.get(
        f"/api/v1/attainment/section-offerings/{offering_id}/summary",
        headers=auth_headers,
    )
    assert summary_resp.status_code == 200, summary_resp.text
    data = summary_resp.json()

    # PO results should exist
    assert len(data["po_results"]) == 1
    po_result = data["po_results"][0]
    assert po_result["program_outcome_id"] == scenario["po_id"]
    assert po_result["contributing_co_count"] == 1
    # student1 scored 75% (above 50%), student2 scored 40% (below 50%)
    # 1 out of 2 students attained -> attainment_pct = 50.0%
    assert po_result["students_above_threshold"] == 1
    assert po_result["total_students"] == 2
    assert float(po_result["attainment_pct"]) == pytest.approx(50.0, abs=0.1)
    # 50% is NOT > 50% -> not attained
    assert po_result["is_attained"] is False


async def test_attainment_summary_not_found_before_publish(client: AsyncClient, auth_headers):
    """GET summary returns 404 if attainment has not been computed yet."""
    suffix = uuid.uuid4().hex[:8]
    dept_resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": f"NF Dept {suffix}", "short_name": f"NF{suffix[:4]}"},
    )
    dept_id = dept_resp.json()["id"]
    prog_resp = await client.post(
        "/api/v1/programs",
        headers=auth_headers,
        json={
            "department_id": dept_id,
            "title": f"NF Program {suffix}",
            "acronym": f"NP{suffix[:4]}",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 136,
            "study_mode": "FULL_TIME",
        },
    )
    prog_id = prog_resp.json()["id"]
    ct_resp = await client.post(
        "/api/v1/ref-data/course-categories",
        headers=auth_headers,
        json={"name": f"NF CT {suffix}"},
    )
    ct_id = ct_resp.json()["id"]
    course_resp = await client.post(
        "/api/v1/courses",
        headers=auth_headers,
        json={
            "course_category_id": ct_id,
            "course_type": "THEORY",
            "code": f"NF{suffix[:6]}",
            "title": f"NF Course {suffix}",
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
            "program_id": prog_id,
            "name": f"NF Curriculum {suffix}",
            "code": f"NFC{suffix[:6]}",
            "effective_year": 2024,
        },
    )
    curriculum_id = curr_resp.json()["id"]
    batch_resp = await client.post(
        "/api/v1/batches",
        headers=auth_headers,
        json={
            "curriculum_id": curriculum_id,
            "name": f"NF Batch {suffix}",
            "start_date": "2024-09-01",
            "term_system": "SEMESTER",
            "num_semesters": 8,
        },
    )
    batch_id = batch_resp.json()["id"]
    full_int = int(uuid.uuid4().hex, 16)
    year = 4500 + (full_int % 500)
    seasons = ["FALL", "SPRING", "SUMMER", "WINTER"]
    season = seasons[(full_int >> 32) % 4]
    term_resp = await client.post(
        "/api/v1/academic-terms",
        headers=auth_headers,
        json={
            "name": f"NF Term {suffix}",
            "year": year,
            "season": season,
            "start_date": "2024-09-01",
            "end_date": "2025-01-15",
        },
    )
    term_id = term_resp.json()["id"]
    sec_resp = await client.post(
        "/api/v1/sections",
        headers=auth_headers,
        json={"name": f"NF Sec {suffix}", "capacity": 30},
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
        f"/api/v1/attainment/section-offerings/{so_id}/summary",
        headers=auth_headers,
    )
    assert resp.status_code == 404, resp.text


async def test_recompute_attainment(client: AsyncClient, auth_headers):
    """POST /recompute re-triggers attainment computation and returns fresh results."""
    scenario = await _setup_attainment_scenario(client, auth_headers)
    offering_id = scenario["offering_id"]

    # Publish first to compute attainment
    pub_resp = await client.post(f"/api/v1/results/{offering_id}/publish", headers=auth_headers)
    assert pub_resp.status_code == 200, pub_resp.text

    # Re-trigger computation
    recompute_resp = await client.post(
        f"/api/v1/attainment/section-offerings/{offering_id}/recompute",
        headers=auth_headers,
    )
    assert recompute_resp.status_code == 200, recompute_resp.text
    data = recompute_resp.json()
    assert data["section_offering_id"] == offering_id
    assert len(data["co_results"]) >= 1


# ── Permission Tests ──────────────────────────────────────────────────────────

async def test_attainment_view_denied_without_auth(client: AsyncClient):
    """Unauthenticated request is rejected."""
    resp = await client.get(
        "/api/v1/attainment/section-offerings/00000000-0000-0000-0000-000000000000/summary",
    )
    assert resp.status_code in (401, 403)


async def test_attainment_config_read_allowed_for_ml(client: AsyncClient, ml_auth_headers):
    """Module Leader has attainment.read permission — can read config."""
    resp = await client.get("/api/v1/attainment/config", headers=ml_auth_headers)
    assert resp.status_code == 200, resp.text


async def test_attainment_config_update_denied_for_teacher(client: AsyncClient, teacher_auth_headers):
    """Section Teacher does not have attainment.configure permission."""
    resp = await client.patch(
        "/api/v1/attainment/config",
        headers=teacher_auth_headers,
        json={"threshold_student_pct": "60.00"},
    )
    assert resp.status_code == 403, resp.text


async def test_attainment_recompute_denied_for_teacher(client: AsyncClient, teacher_auth_headers):
    """Section Teacher cannot trigger recompute (needs attainment.configure)."""
    resp = await client.post(
        "/api/v1/attainment/section-offerings/00000000-0000-0000-0000-000000000001/recompute",
        headers=teacher_auth_headers,
    )
    assert resp.status_code == 403, resp.text


async def test_attainment_summary_allowed_for_teacher(client: AsyncClient, auth_headers, teacher_auth_headers):
    """Section Teacher has attainment.read — can view summary."""
    scenario = await _setup_attainment_scenario(client, auth_headers)
    offering_id = scenario["offering_id"]

    pub_resp = await client.post(f"/api/v1/results/{offering_id}/publish", headers=auth_headers)
    assert pub_resp.status_code == 200, pub_resp.text

    resp = await client.get(
        f"/api/v1/attainment/section-offerings/{offering_id}/summary",
        headers=teacher_auth_headers,
    )
    assert resp.status_code == 200, resp.text
