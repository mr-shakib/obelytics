"""Integration tests for Curriculum module endpoints."""
import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _create_program(client: AsyncClient, headers: dict) -> str:
    """Create a department and program, return program_id."""
    import uuid
    suffix = uuid.uuid4().hex[:6]
    dept_resp = await client.post(
        "/api/v1/departments",
        headers=headers,
        json={"name": f"Curriculum Dept {suffix}", "short_name": f"CD{suffix[:4]}"},
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept_id = dept_resp.json()["id"]

    prog_resp = await client.post(
        "/api/v1/programs",
        headers=headers,
        json={
            "department_id": dept_id,
            "title": f"Bachelor of Curriculum Test {suffix}",
            "acronym": f"BCT{suffix[:3]}",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 136,
            "study_mode": "FULL_TIME",
        },
    )
    assert prog_resp.status_code == 201, prog_resp.text
    return prog_resp.json()["id"]


async def _create_course_type(client: AsyncClient, headers: dict) -> str:
    """Create a course category and return its id."""
    import uuid
    suffix = uuid.uuid4().hex[:6]
    resp = await client.post(
        "/api/v1/ref-data/course-categories",
        headers=headers,
        json={"name": f"Theory {suffix}", "description": "Theory course category"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ── Curriculum CRUD ───────────────────────────────────────────────────────────

async def test_create_curriculum_as_admin(client: AsyncClient, auth_headers):
    program_id = await _create_program(client, auth_headers)
    resp = await client.post(
        "/api/v1/curricula",
        headers=auth_headers,
        json={
            "program_id": program_id,
            "name": "CS Curriculum 2024",
            "code": "CS-2024",
            "effective_year": 2024,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["code"] == "CS-2024"
    assert data["status"] == "DRAFT"
    assert data["version_number"] == 1
    assert data["parent_curriculum_id"] is None


async def test_create_curriculum_denied_for_teacher(client: AsyncClient, auth_headers, teacher_auth_headers):
    program_id = await _create_program(client, auth_headers)
    resp = await client.post(
        "/api/v1/curricula",
        headers=teacher_auth_headers,
        json={
            "program_id": program_id,
            "name": "CS Curriculum Denied",
            "code": "CS-DENIED",
            "effective_year": 2024,
        },
    )
    assert resp.status_code == 403


async def test_list_curricula(client: AsyncClient, auth_headers):
    program_id = await _create_program(client, auth_headers)
    await client.post(
        "/api/v1/curricula",
        headers=auth_headers,
        json={"program_id": program_id, "name": "Listed Curr", "code": "LIST-2024", "effective_year": 2024},
    )
    resp = await client.get("/api/v1/curricula", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_get_curriculum(client: AsyncClient, auth_headers):
    program_id = await _create_program(client, auth_headers)
    create_resp = await client.post(
        "/api/v1/curricula",
        headers=auth_headers,
        json={"program_id": program_id, "name": "Get Test Curr", "code": "GET-2024", "effective_year": 2024},
    )
    curr_id = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/curricula/{curr_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == curr_id


async def test_update_curriculum(client: AsyncClient, auth_headers):
    program_id = await _create_program(client, auth_headers)
    create_resp = await client.post(
        "/api/v1/curricula",
        headers=auth_headers,
        json={"program_id": program_id, "name": "Update Test", "code": "UPD-2024", "effective_year": 2024},
    )
    curr_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/v1/curricula/{curr_id}",
        headers=auth_headers,
        json={"name": "Updated Curriculum Name"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Curriculum Name"


# ── Curriculum Terms ──────────────────────────────────────────────────────────

async def test_add_curriculum_terms(client: AsyncClient, auth_headers):
    program_id = await _create_program(client, auth_headers)
    curr_resp = await client.post(
        "/api/v1/curricula",
        headers=auth_headers,
        json={"program_id": program_id, "name": "Term Test Curr", "code": "TERM-2024", "effective_year": 2024},
    )
    curr_id = curr_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/curricula/{curr_id}/terms",
        headers=auth_headers,
        json=[
            {"curriculum_id": curr_id, "term_number": 1, "name": "Semester 1", "total_credit_hours": 18},
            {"curriculum_id": curr_id, "term_number": 2, "name": "Semester 2", "total_credit_hours": 18},
        ],
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert len(data) == 2
    assert data[0]["term_number"] == 1


async def test_list_curriculum_terms(client: AsyncClient, auth_headers):
    program_id = await _create_program(client, auth_headers)
    curr_resp = await client.post(
        "/api/v1/curricula",
        headers=auth_headers,
        json={"program_id": program_id, "name": "List Terms Curr", "code": "LTERM-2024", "effective_year": 2024},
    )
    curr_id = curr_resp.json()["id"]
    await client.post(
        f"/api/v1/curricula/{curr_id}/terms",
        headers=auth_headers,
        json=[{"curriculum_id": curr_id, "term_number": 1, "name": "Sem 1"}],
    )
    resp = await client.get(f"/api/v1/curricula/{curr_id}/terms", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ── Courses ───────────────────────────────────────────────────────────────────

async def test_create_course(client: AsyncClient, auth_headers):
    ct_id = await _create_course_type(client, auth_headers)
    resp = await client.post(
        "/api/v1/courses",
        headers=auth_headers,
        json={
            "course_category_id": ct_id,
            "course_type": "THEORY",
            "code": "CSE101",
            "title": "Introduction to Programming",
            "credits": 3,
            "theory_hours": 3,
            "lab_hours": 0,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["code"] == "CSE101"
    assert data["status"] == "ACTIVE"


async def test_create_course_denied_for_teacher(client: AsyncClient, auth_headers, teacher_auth_headers):
    ct_id = await _create_course_type(client, auth_headers)
    resp = await client.post(
        "/api/v1/courses",
        headers=teacher_auth_headers,
        json={
            "course_category_id": ct_id,
            "course_type": "THEORY",
            "code": "CSE999",
            "title": "Denied Course",
            "credits": 3,
        },
    )
    assert resp.status_code == 403


async def test_create_course_duplicate_code(client: AsyncClient, auth_headers):
    ct_id = await _create_course_type(client, auth_headers)
    payload = {
        "course_category_id": ct_id,
        "course_type": "THEORY",
        "code": "DUPL-CODE",
        "title": "First Course",
        "credits": 3,
    }
    await client.post("/api/v1/courses", headers=auth_headers, json=payload)
    resp = await client.post("/api/v1/courses", headers=auth_headers, json=payload)
    assert resp.status_code == 409


async def test_update_course(client: AsyncClient, auth_headers):
    ct_id = await _create_course_type(client, auth_headers)
    create_resp = await client.post(
        "/api/v1/courses",
        headers=auth_headers,
        json={"course_category_id": ct_id, "course_type": "THEORY", "code": "UPD-COURSE", "title": "Original Title", "credits": 3},
    )
    course_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/v1/courses/{course_id}",
        headers=auth_headers,
        json={"title": "Updated Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


async def test_archive_course(client: AsyncClient, auth_headers):
    ct_id = await _create_course_type(client, auth_headers)
    create_resp = await client.post(
        "/api/v1/courses",
        headers=auth_headers,
        json={"course_category_id": ct_id, "course_type": "THEORY", "code": "ARCH-COURSE", "title": "Course To Archive", "credits": 3},
    )
    course_id = create_resp.json()["id"]
    resp = await client.post(f"/api/v1/courses/{course_id}/archive", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ARCHIVED"
    assert resp.json()["archived_at"] is not None


# ── Course Slots ──────────────────────────────────────────────────────────────

async def test_add_course_to_curriculum_slot(client: AsyncClient, auth_headers):
    ct_id = await _create_course_type(client, auth_headers)
    program_id = await _create_program(client, auth_headers)

    curr_resp = await client.post(
        "/api/v1/curricula",
        headers=auth_headers,
        json={"program_id": program_id, "name": "Slot Curr", "code": "SLOT-2024", "effective_year": 2024},
    )
    curr_id = curr_resp.json()["id"]

    term_resp = await client.post(
        f"/api/v1/curricula/{curr_id}/terms",
        headers=auth_headers,
        json=[{"curriculum_id": curr_id, "term_number": 1, "name": "Sem 1"}],
    )
    term_id = term_resp.json()[0]["id"]

    course_resp = await client.post(
        "/api/v1/courses",
        headers=auth_headers,
        json={"course_category_id": ct_id, "course_type": "THEORY", "code": "SLOT-CSE101", "title": "Prog 101", "credits": 3},
    )
    course_id = course_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/curricula/{curr_id}/course-slots",
        headers=auth_headers,
        json={
            "curriculum_id": curr_id,
            "curriculum_term_definition_id": term_id,
            "course_id": course_id,
            "is_elective": False,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["course_id"] == course_id
    assert data["curriculum_id"] == curr_id


# ── Prerequisites ──────────────────────────────────────────────────────────────

async def test_add_prerequisites_and_cycle_detection(client: AsyncClient, auth_headers):
    ct_id = await _create_course_type(client, auth_headers)

    # Create 3 courses: A, B, C
    courses = {}
    for code in ["PREREQ-A", "PREREQ-B", "PREREQ-C"]:
        resp = await client.post(
            "/api/v1/courses",
            headers=auth_headers,
            json={"course_category_id": ct_id, "course_type": "THEORY", "code": code, "title": f"Course {code}", "credits": 3},
        )
        assert resp.status_code == 201, resp.text
        courses[code] = resp.json()["id"]

    # A requires B
    resp = await client.post(
        f"/api/v1/courses/{courses['PREREQ-A']}/prerequisites",
        headers=auth_headers,
        json={"course_id": courses["PREREQ-A"], "prerequisite_course_id": courses["PREREQ-B"]},
    )
    assert resp.status_code == 201, resp.text

    # B requires C
    resp = await client.post(
        f"/api/v1/courses/{courses['PREREQ-B']}/prerequisites",
        headers=auth_headers,
        json={"course_id": courses["PREREQ-B"], "prerequisite_course_id": courses["PREREQ-C"]},
    )
    assert resp.status_code == 201, resp.text

    # C requires A — this would create a cycle: A→B→C→A
    resp = await client.post(
        f"/api/v1/courses/{courses['PREREQ-C']}/prerequisites",
        headers=auth_headers,
        json={"course_id": courses["PREREQ-C"], "prerequisite_course_id": courses["PREREQ-A"]},
    )
    assert resp.status_code == 409, resp.text
    assert "circular" in resp.json()["detail"].lower()


async def test_list_prerequisites(client: AsyncClient, auth_headers):
    ct_id = await _create_course_type(client, auth_headers)
    main_resp = await client.post(
        "/api/v1/courses",
        headers=auth_headers,
        json={"course_category_id": ct_id, "course_type": "THEORY", "code": "LIST-PREREQ-MAIN", "title": "Main Course", "credits": 3},
    )
    pre_resp = await client.post(
        "/api/v1/courses",
        headers=auth_headers,
        json={"course_category_id": ct_id, "course_type": "THEORY", "code": "LIST-PREREQ-PRE", "title": "Pre Course", "credits": 3},
    )
    main_id = main_resp.json()["id"]
    pre_id = pre_resp.json()["id"]

    await client.post(
        f"/api/v1/courses/{main_id}/prerequisites",
        headers=auth_headers,
        json={"course_id": main_id, "prerequisite_course_id": pre_id},
    )

    resp = await client.get(f"/api/v1/courses/{main_id}/prerequisites", headers=auth_headers)
    assert resp.status_code == 200
    prereqs = resp.json()
    assert any(p["prerequisite_course_id"] == pre_id for p in prereqs)


# ── Batch ──────────────────────────────────────────────────────────────────────

async def test_create_batch(client: AsyncClient, auth_headers):
    program_id = await _create_program(client, auth_headers)
    curr_resp = await client.post(
        "/api/v1/curricula",
        headers=auth_headers,
        json={"program_id": program_id, "name": "Batch Curr", "code": "BATCH-2024", "effective_year": 2024},
    )
    curr_id = curr_resp.json()["id"]

    resp = await client.post(
        "/api/v1/batches",
        headers=auth_headers,
        json={"curriculum_id": curr_id, "name": "Batch 2024", "intake_year": 2024},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == "Batch 2024"
    assert data["status"] == "ACTIVE"


async def test_create_batch_duplicate_name(client: AsyncClient, auth_headers):
    program_id = await _create_program(client, auth_headers)
    curr_resp = await client.post(
        "/api/v1/curricula",
        headers=auth_headers,
        json={"program_id": program_id, "name": "Dup Batch Curr", "code": "DUPB-2024", "effective_year": 2024},
    )
    curr_id = curr_resp.json()["id"]
    payload = {"curriculum_id": curr_id, "name": "DupBatch", "intake_year": 2024}
    await client.post("/api/v1/batches", headers=auth_headers, json=payload)
    resp = await client.post("/api/v1/batches", headers=auth_headers, json=payload)
    assert resp.status_code == 409


# ── Academic Term ──────────────────────────────────────────────────────────────

async def test_create_academic_term(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/academic-terms",
        headers=auth_headers,
        json={
            "name": "Spring 2024",
            "year": 2024,
            "season": "SPRING",
            "start_date": "2024-01-15",
            "end_date": "2024-05-15",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["season"] == "SPRING"
    assert data["status"] == "UPCOMING"


async def test_create_academic_term_duplicate(client: AsyncClient, auth_headers):
    payload = {
        "name": "Fall 2024",
        "year": 2024,
        "season": "FALL",
        "start_date": "2024-08-15",
        "end_date": "2024-12-15",
    }
    await client.post("/api/v1/academic-terms", headers=auth_headers, json=payload)
    resp = await client.post("/api/v1/academic-terms", headers=auth_headers, json=payload)
    assert resp.status_code == 409


# ── Section ────────────────────────────────────────────────────────────────────

async def test_create_section(client: AsyncClient, auth_headers):
    import uuid
    section_name = f"Section-{uuid.uuid4().hex[:6]}"
    resp = await client.post(
        "/api/v1/sections",
        headers=auth_headers,
        json={"name": section_name, "capacity": 40},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == section_name
    assert data["capacity"] == 40


async def test_create_section_duplicate(client: AsyncClient, auth_headers):
    import uuid
    section_name = f"DupSec-{uuid.uuid4().hex[:6]}"
    payload = {"name": section_name, "capacity": 30}
    await client.post("/api/v1/sections", headers=auth_headers, json=payload)
    resp = await client.post("/api/v1/sections", headers=auth_headers, json=payload)
    assert resp.status_code == 409


# ── Section Offering ──────────────────────────────────────────────────────────

async def _setup_offering_data(client: AsyncClient, headers: dict) -> dict:
    """Creates all prerequisites for a section offering and returns their IDs."""
    import uuid
    suffix = uuid.uuid4().hex[:6]
    # Use a pseudo-random year in far future to avoid collisions across tests
    year = 2100 + (int(suffix, 16) % 900)

    ct_id = await _create_course_type(client, headers)
    program_id = await _create_program(client, headers)

    curr_resp = await client.post(
        "/api/v1/curricula",
        headers=headers,
        json={"program_id": program_id, "name": f"Off Curr {suffix}", "code": f"OFF{suffix}", "effective_year": 2024},
    )
    curr_id = curr_resp.json()["id"]

    batch_resp = await client.post(
        "/api/v1/batches",
        headers=headers,
        json={"curriculum_id": curr_id, "name": f"Batch {suffix}", "intake_year": 2024},
    )
    batch_id = batch_resp.json()["id"]

    course_resp = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={"course_category_id": ct_id, "course_type": "THEORY", "code": f"OFF-CSE{suffix}", "title": "Off Course", "credits": 3},
    )
    course_id = course_resp.json()["id"]

    term_resp = await client.post(
        "/api/v1/academic-terms",
        headers=headers,
        json={
            "name": f"Spring {suffix}",
            "year": year,
            "season": "SPRING",
            "start_date": "2024-01-01",
            "end_date": "2024-05-31",
        },
    )
    assert term_resp.status_code == 201, f"Failed to create academic term: {term_resp.text}"
    term_id = term_resp.json()["id"]

    section_name = f"Sec-{suffix}"
    sec_resp = await client.post(
        "/api/v1/sections",
        headers=headers,
        json={"name": section_name, "capacity": 35},
    )
    section_id = sec_resp.json()["id"]

    return {
        "curriculum_id": curr_id,
        "batch_id": batch_id,
        "course_id": course_id,
        "academic_term_id": term_id,
        "section_id": section_id,
    }


async def test_create_section_offering(client: AsyncClient, auth_headers):
    data = await _setup_offering_data(client, auth_headers)
    resp = await client.post(
        "/api/v1/section-offerings",
        headers=auth_headers,
        json=data,
    )
    assert resp.status_code == 201, resp.text
    result = resp.json()
    assert result["status"] == "UPCOMING"
    assert result["batch_id"] == data["batch_id"]


async def test_create_section_offering_duplicate(client: AsyncClient, auth_headers):
    data = await _setup_offering_data(client, auth_headers)
    await client.post("/api/v1/section-offerings", headers=auth_headers, json=data)
    resp = await client.post("/api/v1/section-offerings", headers=auth_headers, json=data)
    assert resp.status_code == 409


# ── Faculty Assignment ────────────────────────────────────────────────────────

async def test_assign_faculty(client: AsyncClient, auth_headers):
    import uuid
    data = await _setup_offering_data(client, auth_headers)
    offering_resp = await client.post(
        "/api/v1/section-offerings",
        headers=auth_headers,
        json=data,
    )
    offering_id = offering_resp.json()["id"]

    user_id = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/faculty-assignments",
        headers=auth_headers,
        json={
            "section_offering_id": offering_id,
            "user_id": user_id,
            "role_in_course": "SECTION_TEACHER",
        },
    )
    assert resp.status_code == 201, resp.text
    result = resp.json()
    assert result["user_id"] == user_id
    assert result["removed_at"] is None


async def test_assign_faculty_duplicate_role(client: AsyncClient, auth_headers):
    import uuid
    data = await _setup_offering_data(client, auth_headers)
    offering_resp = await client.post(
        "/api/v1/section-offerings",
        headers=auth_headers,
        json=data,
    )
    offering_id = offering_resp.json()["id"]
    user_id = str(uuid.uuid4())
    payload = {
        "section_offering_id": offering_id,
        "user_id": user_id,
        "role_in_course": "MODULE_LEADER",
    }
    await client.post("/api/v1/faculty-assignments", headers=auth_headers, json=payload)
    resp = await client.post("/api/v1/faculty-assignments", headers=auth_headers, json=payload)
    assert resp.status_code == 409


async def test_remove_faculty_assignment(client: AsyncClient, auth_headers):
    import uuid
    data = await _setup_offering_data(client, auth_headers)
    offering_resp = await client.post(
        "/api/v1/section-offerings",
        headers=auth_headers,
        json=data,
    )
    offering_id = offering_resp.json()["id"]
    user_id = str(uuid.uuid4())
    assign_resp = await client.post(
        "/api/v1/faculty-assignments",
        headers=auth_headers,
        json={
            "section_offering_id": offering_id,
            "user_id": user_id,
            "role_in_course": "SECTION_TEACHER",
        },
    )
    assignment_id = assign_resp.json()["id"]
    resp = await client.delete(
        f"/api/v1/faculty-assignments/{assignment_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["removed_at"] is not None


# ── Curriculum versioning ─────────────────────────────────────────────────────

async def test_activate_curriculum(client: AsyncClient, auth_headers):
    program_id = await _create_program(client, auth_headers)
    curr_resp = await client.post(
        "/api/v1/curricula",
        headers=auth_headers,
        json={"program_id": program_id, "name": "Activate Curr", "code": "ACT-2024", "effective_year": 2024},
    )
    curr_id = curr_resp.json()["id"]
    resp = await client.post(f"/api/v1/curricula/{curr_id}/activate", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ACTIVE"


async def test_version_curriculum(client: AsyncClient, auth_headers):
    program_id = await _create_program(client, auth_headers)
    curr_resp = await client.post(
        "/api/v1/curricula",
        headers=auth_headers,
        json={"program_id": program_id, "name": "Version Curr", "code": "VER-2024", "effective_year": 2024},
    )
    curr_id = curr_resp.json()["id"]

    # Activate first
    await client.post(f"/api/v1/curricula/{curr_id}/activate", headers=auth_headers)

    # Version it
    resp = await client.post(f"/api/v1/curricula/{curr_id}/version", headers=auth_headers)
    assert resp.status_code == 201, resp.text
    new_data = resp.json()
    assert new_data["status"] == "DRAFT"
    assert new_data["version_number"] == 2
    assert new_data["parent_curriculum_id"] == curr_id

    # Old one should now be VERSIONED
    old_resp = await client.get(f"/api/v1/curricula/{curr_id}", headers=auth_headers)
    assert old_resp.json()["status"] == "VERSIONED"


async def test_cannot_update_archived_curriculum(client: AsyncClient, auth_headers):
    program_id = await _create_program(client, auth_headers)
    curr_resp = await client.post(
        "/api/v1/curricula",
        headers=auth_headers,
        json={"program_id": program_id, "name": "Locked Curr", "code": "LCK-2024", "effective_year": 2024},
    )
    curr_id = curr_resp.json()["id"]
    # Activate then version it (makes it VERSIONED = locked)
    await client.post(f"/api/v1/curricula/{curr_id}/activate", headers=auth_headers)
    await client.post(f"/api/v1/curricula/{curr_id}/version", headers=auth_headers)

    resp = await client.patch(
        f"/api/v1/curricula/{curr_id}",
        headers=auth_headers,
        json={"name": "Should Fail"},
    )
    assert resp.status_code == 409
