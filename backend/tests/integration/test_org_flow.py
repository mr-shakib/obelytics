"""Integration tests for Organization, Department, and Program endpoints."""
import pytest
from httpx import AsyncClient


# ── Organization ──────────────────────────────────────────────────────────────

async def test_get_organization_as_admin(client: AsyncClient, auth_headers):
    resp = await client.get("/api/v1/organization", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test University"
    assert data["short_name"] == "TU"
    assert data["status"] == "ACTIVE"


async def test_get_organization_denied_for_teacher(client: AsyncClient, teacher_auth_headers):
    resp = await client.get("/api/v1/organization", headers=teacher_auth_headers)
    assert resp.status_code == 403


async def test_update_organization(client: AsyncClient, auth_headers):
    resp = await client.patch(
        "/api/v1/organization",
        headers=auth_headers,
        json={"description": "A great test university", "website": "https://tu.edu"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "A great test university"
    assert data["website"] == "https://tu.edu"


# ── Departments ───────────────────────────────────────────────────────────────

async def test_create_department(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "Computer Science", "short_name": "CS", "year_established": 2000},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Computer Science"
    assert data["short_name"] == "CS"
    assert data["status"] == "ACTIVE"
    return data["id"]


async def test_list_departments(client: AsyncClient, auth_headers):
    await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "Electrical Engineering", "short_name": "EE"},
    )
    resp = await client.get("/api/v1/departments", headers=auth_headers)
    assert resp.status_code == 200
    names = [d["name"] for d in resp.json()]
    assert "Electrical Engineering" in names


async def test_create_department_duplicate_short_name(client: AsyncClient, auth_headers):
    await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "Mechanical Engineering", "short_name": "ME"},
    )
    resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "Mining Engineering", "short_name": "ME"},
    )
    assert resp.status_code == 409


async def test_create_department_denied_for_teacher(client: AsyncClient, teacher_auth_headers):
    resp = await client.post(
        "/api/v1/departments",
        headers=teacher_auth_headers,
        json={"name": "Physics", "short_name": "PHY"},
    )
    assert resp.status_code == 403


async def test_update_department(client: AsyncClient, auth_headers):
    create_resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "Civil Engineering", "short_name": "CE"},
    )
    dept_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/v1/departments/{dept_id}",
        headers=auth_headers,
        json={"description": "The civil dept"},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "The civil dept"


async def test_archive_department(client: AsyncClient, auth_headers):
    create_resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "To Archive Dept", "short_name": "TAD"},
    )
    dept_id = create_resp.json()["id"]
    resp = await client.post(f"/api/v1/departments/{dept_id}/archive", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ARCHIVED"
    assert resp.json()["archived_at"] is not None


async def test_archive_already_archived_department(client: AsyncClient, auth_headers):
    create_resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "Double Archive", "short_name": "DA"},
    )
    dept_id = create_resp.json()["id"]
    await client.post(f"/api/v1/departments/{dept_id}/archive", headers=auth_headers)
    resp = await client.post(f"/api/v1/departments/{dept_id}/archive", headers=auth_headers)
    assert resp.status_code == 409


async def test_delete_department_as_super_admin(client: AsyncClient, auth_headers):
    create_resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "To Delete Dept", "short_name": "TDD"},
    )
    dept_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/departments/{dept_id}", headers=auth_headers)
    assert resp.status_code == 204
    # Gone afterwards
    resp = await client.get(f"/api/v1/departments/{dept_id}", headers=auth_headers)
    assert resp.status_code == 404


async def test_delete_department_denied_for_non_super_admin(client: AsyncClient, auth_headers, teacher_auth_headers):
    create_resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "Protected Dept", "short_name": "PDD"},
    )
    dept_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/departments/{dept_id}", headers=teacher_auth_headers)
    assert resp.status_code == 403


async def test_delete_department_blocked_when_it_has_programs(client: AsyncClient, auth_headers):
    create_resp = await client.post(
        "/api/v1/departments",
        headers=auth_headers,
        json={"name": "Dept With Program", "short_name": "DWP"},
    )
    dept_id = create_resp.json()["id"]
    prog_resp = await client.post(
        "/api/v1/programs",
        headers=auth_headers,
        json={
            "department_id": dept_id,
            "title": "Blocking Program",
            "acronym": "BLKP",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 140,
            "study_mode": "FULL_TIME",
        },
    )
    assert prog_resp.status_code == 201
    resp = await client.delete(f"/api/v1/departments/{dept_id}", headers=auth_headers)
    assert resp.status_code == 409
    assert "programs" in resp.json()["detail"]


# ── Programs ──────────────────────────────────────────────────────────────────

async def _create_dept(client: AsyncClient, headers, name: str, short_name: str) -> str:
    resp = await client.post(
        "/api/v1/departments",
        headers=headers,
        json={"name": name, "short_name": short_name},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_create_program(client: AsyncClient, auth_headers):
    dept_id = await _create_dept(client, auth_headers, "Software Dept", "SW")
    resp = await client.post(
        "/api/v1/programs",
        headers=auth_headers,
        json={
            "department_id": dept_id,
            "title": "Bachelor of Software Engineering",
            "acronym": "BSE",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 136,
            "study_mode": "FULL_TIME",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["acronym"] == "BSE"
    assert data["status"] == "ACTIVE"


async def test_create_program_duplicate_acronym(client: AsyncClient, auth_headers):
    dept_id = await _create_dept(client, auth_headers, "Data Dept", "DD")
    payload = {
        "department_id": dept_id,
        "title": "Bachelor of Science",
        "acronym": "BS_DUP",
        "program_type": "UNDERGRADUATE",
        "minimum_duration_semesters": 8,
        "total_credits": 120,
        "study_mode": "FULL_TIME",
    }
    await client.post("/api/v1/programs", headers=auth_headers, json=payload)
    resp = await client.post("/api/v1/programs", headers=auth_headers, json=payload)
    assert resp.status_code == 409


async def test_list_programs(client: AsyncClient, auth_headers):
    dept_id = await _create_dept(client, auth_headers, "Bio Dept", "BIO")
    await client.post(
        "/api/v1/programs",
        headers=auth_headers,
        json={
            "department_id": dept_id,
            "title": "Bachelor of Biology",
            "acronym": "BBIO",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 120,
            "study_mode": "FULL_TIME",
        },
    )
    resp = await client.get("/api/v1/programs", headers=auth_headers)
    assert resp.status_code == 200
    acronyms = [p["acronym"] for p in resp.json()]
    assert "BBIO" in acronyms


async def test_list_programs_filter_by_department(client: AsyncClient, auth_headers):
    dept_id = await _create_dept(client, auth_headers, "Chem Dept", "CHEM")
    await client.post(
        "/api/v1/programs",
        headers=auth_headers,
        json={
            "department_id": dept_id,
            "title": "Bachelor of Chemistry",
            "acronym": "BCHEM",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 120,
            "study_mode": "FULL_TIME",
        },
    )
    resp = await client.get(f"/api/v1/programs?department_id={dept_id}", headers=auth_headers)
    assert resp.status_code == 200
    results = resp.json()
    assert all(p["department_id"] == dept_id for p in results)
    assert any(p["acronym"] == "BCHEM" for p in results)


async def test_archive_program(client: AsyncClient, auth_headers):
    dept_id = await _create_dept(client, auth_headers, "Arch Dept", "AD")
    create_resp = await client.post(
        "/api/v1/programs",
        headers=auth_headers,
        json={
            "department_id": dept_id,
            "title": "Program To Archive",
            "acronym": "PTA",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 120,
            "study_mode": "FULL_TIME",
        },
    )
    program_id = create_resp.json()["id"]
    resp = await client.post(f"/api/v1/programs/{program_id}/archive", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ARCHIVED"


async def test_create_program_denied_for_ml(client: AsyncClient, ml_auth_headers):
    resp = await client.post(
        "/api/v1/programs",
        headers=ml_auth_headers,
        json={
            "department_id": "00000000-0000-0000-0000-000000000001",
            "title": "Unauthorized",
            "acronym": "UNAUTH",
            "program_type": "UNDERGRADUATE",
            "minimum_duration_semesters": 8,
            "total_credits": 120,
            "study_mode": "FULL_TIME",
        },
    )
    assert resp.status_code == 403
