"""Course codes are unique per curriculum, not per organization.

The same code may name different courses in different curricula (e.g. CSE214 is
Algorithms in one curriculum and OOP in the next), but a curriculum can't contain
two courses with the same code, and a batch can only offer its curriculum's courses.
"""
import uuid

from httpx import AsyncClient

from tests.integration.test_curriculum_flow import _create_course_type, _create_program


async def _course(client: AsyncClient, headers: dict, ct_id: str, code: str, title: str, credits=3):
    return await client.post(
        "/api/v1/courses",
        headers=headers,
        json={"course_category_id": ct_id, "course_type": "THEORY", "code": code,
              "title": title, "credits": credits},
    )


async def _curriculum_with_term(client: AsyncClient, headers: dict, program_id: str) -> tuple[str, str]:
    suffix = uuid.uuid4().hex[:6]
    curr = await client.post(
        "/api/v1/curricula",
        headers=headers,
        json={"program_id": program_id, "name": f"Code Curr {suffix}", "effective_year": 2024},
    )
    assert curr.status_code == 201, curr.text
    curr_id = curr.json()["id"]
    term = await client.post(
        f"/api/v1/curricula/{curr_id}/terms",
        headers=headers,
        json=[{"term_number": 1, "name": "Semester 1"}],
    )
    assert term.status_code == 201, term.text
    return curr_id, term.json()[0]["id"]


async def _slot(client: AsyncClient, headers: dict, curr_id: str, term_id: str, course_id: str):
    return await client.post(
        f"/api/v1/curricula/{curr_id}/course-slots",
        headers=headers,
        json={"curriculum_term_definition_id": term_id, "course_id": course_id},
    )


async def test_same_code_allowed_for_different_courses(client: AsyncClient, auth_headers):
    ct_id = await _create_course_type(client, auth_headers)
    code = f"RE{uuid.uuid4().hex[:5]}"
    first = await _course(client, auth_headers, ct_id, code, "Algorithms", credits=2)
    second = await _course(client, auth_headers, ct_id, code, "Object Oriented Programming")
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] != second.json()["id"]


async def test_identical_course_rejected(client: AsyncClient, auth_headers):
    ct_id = await _create_course_type(client, auth_headers)
    code = f"ID{uuid.uuid4().hex[:5]}"
    assert (await _course(client, auth_headers, ct_id, code, "Databases")).status_code == 201
    dup = await _course(client, auth_headers, ct_id, code, "databases")
    assert dup.status_code == 409
    assert "identical" in dup.json()["detail"]


async def test_curriculum_rejects_second_course_with_same_code(client: AsyncClient, auth_headers):
    ct_id = await _create_course_type(client, auth_headers)
    program_id = await _create_program(client, auth_headers)
    code = f"CC{uuid.uuid4().hex[:5]}"
    old = (await _course(client, auth_headers, ct_id, code, "Algorithms", credits=2)).json()["id"]
    new = (await _course(client, auth_headers, ct_id, code, "Object Oriented Programming")).json()["id"]

    curr_a, term_a = await _curriculum_with_term(client, auth_headers, program_id)
    curr_b, term_b = await _curriculum_with_term(client, auth_headers, program_id)

    assert (await _slot(client, auth_headers, curr_a, term_a, old)).status_code == 201
    clash = await _slot(client, auth_headers, curr_a, term_a, new)
    assert clash.status_code == 409
    assert code in clash.json()["detail"]
    # the other curriculum can use the new course under the same code
    assert (await _slot(client, auth_headers, curr_b, term_b, new)).status_code == 201


async def test_renaming_code_into_curriculum_clash_rejected(client: AsyncClient, auth_headers):
    ct_id = await _create_course_type(client, auth_headers)
    program_id = await _create_program(client, auth_headers)
    s = uuid.uuid4().hex[:5]
    a = (await _course(client, auth_headers, ct_id, f"RA{s}", "Course A")).json()["id"]
    b = (await _course(client, auth_headers, ct_id, f"RB{s}", "Course B")).json()["id"]
    curr, term = await _curriculum_with_term(client, auth_headers, program_id)
    await _slot(client, auth_headers, curr, term, a)
    await _slot(client, auth_headers, curr, term, b)

    resp = await client.patch(f"/api/v1/courses/{b}", headers=auth_headers, json={"code": f"RA{s}"})
    assert resp.status_code == 409
    # an unslotted course may take the code
    c = (await _course(client, auth_headers, ct_id, f"RC{s}", "Course C")).json()["id"]
    ok = await client.patch(f"/api/v1/courses/{c}", headers=auth_headers, json={"code": f"RA{s}"})
    assert ok.status_code == 200, ok.text


async def test_bulk_import_allows_reused_code_but_not_identical(client: AsyncClient, auth_headers):
    ct_id = await _create_course_type(client, auth_headers)
    code = f"BI{uuid.uuid4().hex[:5]}"
    assert (await _course(client, auth_headers, ct_id, code, "Algorithms", credits=2)).status_code == 201

    row = {"course_category_id": ct_id, "course_type": "THEORY", "code": code}
    resp = await client.post(
        "/api/v1/courses/bulk-import",
        headers=auth_headers,
        json={"courses": [
            {**row, "title": "Algorithms", "credits": 2},             # identical -> error
            {**row, "title": "Object Oriented Programming", "credits": 3},  # new course
        ]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created"] == 1, body
    assert [e["row"] for e in body["errors"]] == [1]
    assert "already exists" in body["errors"][0]["message"]


async def test_batch_offering_requires_curriculum_course(client: AsyncClient, auth_headers):
    ct_id = await _create_course_type(client, auth_headers)
    program_id = await _create_program(client, auth_headers)
    curr, term = await _curriculum_with_term(client, auth_headers, program_id)
    s = uuid.uuid4().hex[:5]
    inside = (await _course(client, auth_headers, ct_id, f"BO{s}", "In Curriculum")).json()["id"]
    outside = (await _course(client, auth_headers, ct_id, f"BO{s}", "Other Curriculum")).json()["id"]
    await _slot(client, auth_headers, curr, term, inside)

    batch = await client.post(
        "/api/v1/batches",
        headers=auth_headers,
        json={"curriculum_id": curr, "name": f"Batch {s}", "start_date": "2031-01-01",
              "term_system": "SEMESTER", "num_semesters": 1},
    )
    assert batch.status_code == 201, batch.text
    batch_id = batch.json()["id"]
    academic_term_id = batch.json()["term_calendar"][0]["academic_term_id"]
    url = f"/api/v1/batches/{batch_id}/terms/{academic_term_id}/offerings"

    wrong = await client.post(url, headers=auth_headers, json={"course_id": outside, "section_name": "A"})
    assert wrong.status_code == 422
    right = await client.post(url, headers=auth_headers, json={"course_id": inside, "section_name": "A"})
    assert right.status_code == 201, right.text
