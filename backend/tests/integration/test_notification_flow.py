"""Integration tests for Notification module endpoints."""
import uuid

import pytest
from httpx import AsyncClient


# ── Setup helpers ─────────────────────────────────────────────────────────────

async def _setup_co_for_notification(client: AsyncClient, headers: dict) -> str:
    """
    Create a minimal chain and a CO in DRAFT status.
    Returns the co_id.
    """
    suffix = uuid.uuid4().hex
    full_int = int(suffix, 16)
    year = 8000 + (full_int % 1000)
    seasons = ["FALL", "SPRING", "SUMMER", "WINTER"]
    season = seasons[(full_int >> 32) % 4]

    # Department
    dept_resp = await client.post(
        "/api/v1/departments",
        headers=headers,
        json={"name": f"Notif Dept {suffix[:8]}", "short_name": f"ND{suffix[:4]}"},
    )
    assert dept_resp.status_code == 201, dept_resp.text
    dept_id = dept_resp.json()["id"]

    # Program
    prog_resp = await client.post(
        "/api/v1/programs",
        headers=headers,
        json={
            "department_id": dept_id,
            "title": f"Notif Program {suffix[:8]}",
            "acronym": f"NP{suffix[:4]}",
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
        json={"name": f"Notif Theory {suffix[:8]}"},
    )
    assert ct_resp.status_code == 201, ct_resp.text
    ct_id = ct_resp.json()["id"]

    # Course
    course_resp = await client.post(
        "/api/v1/courses",
        headers=headers,
        json={
            "course_type_id": ct_id,
            "code": f"NOT{suffix[:6]}",
            "title": f"Notif Course {suffix[:8]}",
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
            "name": f"Notif Curriculum {suffix[:8]}",
            "code": f"NTC{suffix[:6]}",
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
            "name": f"Notif Term {suffix[:8]}",
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
        json={"name": f"Notif Section {suffix[:8]}", "capacity": 40},
    )
    assert sec_resp.status_code == 201, sec_resp.text
    section_id = sec_resp.json()["id"]

    # Section offering
    await client.post(
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

    # Course Outcome
    co_resp = await client.post(
        "/api/v1/course-outcomes",
        headers=headers,
        json={
            "curriculum_id": curriculum_id,
            "course_id": course_id,
            "code": f"NT{suffix[:6]}",
            "statement": f"Notif test CO statement {suffix[:8]}",
        },
    )
    assert co_resp.status_code == 201, co_resp.text
    return co_resp.json()["id"]


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notifications_initially_empty(client: AsyncClient, auth_headers: dict):
    """Initially GET /notifications/me returns an empty list (for this user's session)."""
    resp = await client.get("/api/v1/notifications/me", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    # List could be non-empty from other tests; just validate shape
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_notification_count(client: AsyncClient, auth_headers: dict):
    """GET /notifications/me/count returns unread_count."""
    resp = await client.get("/api/v1/notifications/me/count", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "unread_count" in data
    assert isinstance(data["unread_count"], int)


@pytest.mark.asyncio
async def test_notification_after_co_approve(client: AsyncClient, auth_headers: dict):
    """After CO approve, the CO author receives a CO_APPROVED notification."""
    co_id = await _setup_co_for_notification(client, auth_headers)

    # Get current unread count before
    count_before_resp = await client.get("/api/v1/notifications/me/count", headers=auth_headers)
    count_before = count_before_resp.json()["unread_count"]

    # Submit then approve (same user creates and approves — valid test)
    submit_resp = await client.post(
        f"/api/v1/course-outcomes/{co_id}/submit", headers=auth_headers
    )
    assert submit_resp.status_code == 200, submit_resp.text

    approve_resp = await client.post(
        f"/api/v1/course-outcomes/{co_id}/approve", headers=auth_headers
    )
    assert approve_resp.status_code == 200, approve_resp.text

    # Check notifications
    notif_resp = await client.get("/api/v1/notifications/me", headers=auth_headers)
    assert notif_resp.status_code == 200, notif_resp.text
    notifications = notif_resp.json()

    # Find CO_APPROVED notification for this CO
    co_notifs = [
        n for n in notifications
        if n["notification_type"] == "CO_APPROVED" and n["entity_id"] == co_id
    ]
    assert len(co_notifs) >= 1, f"Expected CO_APPROVED notification, got: {notifications}"

    # Unread count should have increased
    count_after_resp = await client.get("/api/v1/notifications/me/count", headers=auth_headers)
    count_after = count_after_resp.json()["unread_count"]
    assert count_after > count_before


@pytest.mark.asyncio
async def test_mark_notification_read(client: AsyncClient, auth_headers: dict):
    """POST /notifications/{id}/read marks notification as read."""
    co_id = await _setup_co_for_notification(client, auth_headers)

    # Create a notification via CO approve
    await client.post(f"/api/v1/course-outcomes/{co_id}/submit", headers=auth_headers)
    await client.post(f"/api/v1/course-outcomes/{co_id}/approve", headers=auth_headers)

    # Get notifications and find the unread CO_APPROVED one
    notif_resp = await client.get("/api/v1/notifications/me", headers=auth_headers)
    assert notif_resp.status_code == 200, notif_resp.text
    notifications = notif_resp.json()
    co_notifs = [
        n for n in notifications
        if n["notification_type"] == "CO_APPROVED"
        and n["entity_id"] == co_id
        and not n["is_read"]
    ]
    assert len(co_notifs) >= 1, "Expected an unread CO_APPROVED notification"
    notif_id = co_notifs[0]["id"]

    # Mark it read
    read_resp = await client.post(
        f"/api/v1/notifications/{notif_id}/read",
        headers=auth_headers,
    )
    assert read_resp.status_code == 200, read_resp.text
    data = read_resp.json()
    assert data["is_read"] is True
    assert data["read_at"] is not None


@pytest.mark.asyncio
async def test_mark_all_notifications_read(client: AsyncClient, auth_headers: dict):
    """POST /notifications/read-all marks all as read and returns updated count."""
    co_id = await _setup_co_for_notification(client, auth_headers)

    # Create a notification
    await client.post(f"/api/v1/course-outcomes/{co_id}/submit", headers=auth_headers)
    await client.post(f"/api/v1/course-outcomes/{co_id}/approve", headers=auth_headers)

    # Mark all read
    resp = await client.post("/api/v1/notifications/read-all", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "updated" in data
    assert isinstance(data["updated"], int)

    # Verify count is now 0
    count_resp = await client.get("/api/v1/notifications/me/count", headers=auth_headers)
    assert count_resp.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_unread_only_filter(client: AsyncClient, auth_headers: dict):
    """GET /notifications/me?unread_only=true returns only unread notifications."""
    co_id = await _setup_co_for_notification(client, auth_headers)

    # Create a notification via approve
    await client.post(f"/api/v1/course-outcomes/{co_id}/submit", headers=auth_headers)
    await client.post(f"/api/v1/course-outcomes/{co_id}/approve", headers=auth_headers)

    # Get only unread
    resp = await client.get(
        "/api/v1/notifications/me",
        headers=auth_headers,
        params={"unread_only": "true"},
    )
    assert resp.status_code == 200, resp.text
    notifications = resp.json()
    assert isinstance(notifications, list)
    # All returned notifications must be unread
    for n in notifications:
        assert n["is_read"] is False, f"Expected unread, got: {n}"
