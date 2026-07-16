"""
Integration tests for the IAM HTTP layer.

Covers:
  - Login → token → /me  (happy path)
  - Refresh cycle (old token revoked after refresh)
  - Logout
  - Permission denied (403) for endpoints that require a permission
  - Super admin bypass (is_super_admin=True skips permission check)
  - User creation by admin
"""
import pytest
from httpx import AsyncClient

from tests.conftest import (
    TEST_ADMIN_EMAIL,
    TEST_ADMIN_PASSWORD,
    TEST_ML_EMAIL,
    TEST_ML_PASSWORD,
    TEST_TEACHER_EMAIL,
    TEST_TEACHER_PASSWORD,
)


# ── Auth flow ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_returns_tokens(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


@pytest.mark.asyncio
async def test_login_bad_credentials_returns_401(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": "WRONG"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user_returns_401(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@nowhere.test", "password": "anything"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_returns_current_user(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/users/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == TEST_ADMIN_EMAIL
    assert body["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_get_me_without_token_returns_403(client: AsyncClient):
    # HTTPBearer returns 403 when the Authorization header is missing
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_me_with_invalid_token_returns_401(client: AsyncClient):
    resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer totally.invalid.token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_full_refresh_cycle(client: AsyncClient):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    tokens = login.json()

    # Refresh
    refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 200
    new_tokens = refresh.json()
    # refresh token must rotate; access tokens may be identical within the same second
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # Old refresh token is now revoked
    reuse = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert reuse.status_code == 401


@pytest.mark.asyncio
async def test_logout_then_refresh_returns_401(client: AsyncClient):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    tokens = login.json()

    await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )

    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 401


# ── Permission manifest ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_manifest_is_super_admin(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/users/me/permissions", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_super_admin"] is True
    assert len(body["permissions"]) > 0


@pytest.mark.asyncio
async def test_teacher_manifest_not_super_admin(
    client: AsyncClient, teacher_auth_headers: dict
):
    resp = await client.get("/api/v1/users/me/permissions", headers=teacher_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_super_admin"] is False
    assert "co.create" in body["permissions"]
    assert "user.create" not in body["permissions"]


# ── Permission-denied scenarios ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_teacher_cannot_list_all_users(
    client: AsyncClient, teacher_auth_headers: dict
):
    """GET /users requires user.read which Section Teacher does not have."""
    resp = await client.get("/api/v1/users", headers=teacher_auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_teacher_cannot_create_user(
    client: AsyncClient, teacher_auth_headers: dict
):
    resp = await client.post(
        "/api/v1/users",
        headers=teacher_auth_headers,
        json={
            "email": "newuser@obelytics-test.com",
            "full_name": "New User",
            "password": "Password1!",
            "role_id": "00000000-0000-0000-0000-000000000000",
            "scope_type": "GLOBAL",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_ml_cannot_deactivate_user(
    client: AsyncClient, ml_auth_headers: dict
):
    """POST /users/{id}/deactivate requires super admin."""
    from uuid import uuid4
    resp = await client.post(
        f"/api/v1/users/{uuid4()}/deactivate",
        headers=ml_auth_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_teacher_cannot_create_role(
    client: AsyncClient, teacher_auth_headers: dict
):
    """POST /roles requires system.roles.create."""
    resp = await client.post(
        "/api/v1/roles",
        headers=teacher_auth_headers,
        json={"name": "Fake Role"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_list_all_permissions(
    client: AsyncClient, auth_headers: dict
):
    resp = await client.get("/api/v1/roles/permissions/all", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    codes = [p["code"] for p in data]
    assert "co.create" in codes
    assert "attainment.initiate" in codes


@pytest.mark.asyncio
async def test_program_coordinator_can_view_permission_matrix(
    client: AsyncClient, pc_auth_headers: dict
):
    permissions_resp = await client.get(
        "/api/v1/roles/permissions/all",
        headers=pc_auth_headers,
    )
    roles_resp = await client.get(
        "/api/v1/roles/with-permissions",
        headers=pc_auth_headers,
    )

    assert permissions_resp.status_code == 200
    assert roles_resp.status_code == 200
    assert len(permissions_resp.json()) > 0
    assert any(role["name"] == "Program Coordinator" for role in roles_resp.json())


@pytest.mark.asyncio
async def test_teacher_cannot_list_all_permissions(
    client: AsyncClient, teacher_auth_headers: dict
):
    resp = await client.get("/api/v1/roles/permissions/all", headers=teacher_auth_headers)
    assert resp.status_code == 403


# ── User management ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_can_create_user(client: AsyncClient, auth_headers: dict):
    # Get a valid role ID first
    roles_resp = await client.get("/api/v1/roles", headers=auth_headers)
    roles = roles_resp.json()
    teacher_role = next(r for r in roles if r["name"] == "Section Teacher")

    resp = await client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "email": "newteacher@obelytics-test.com",
            "full_name": "New Teacher",
            "password": "Secure@Pass123",
            "role_id": teacher_role["id"],
            "scope_type": "PROGRAM",
            "scope_id": None,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "newteacher@obelytics-test.com"
    assert body["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_duplicate_email_returns_409(client: AsyncClient, auth_headers: dict):
    roles_resp = await client.get("/api/v1/roles", headers=auth_headers)
    teacher_role = next(r for r in roles_resp.json() if r["name"] == "Section Teacher")

    # First creation
    await client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "email": "dup@obelytics-test.com",
            "full_name": "First",
            "password": "Secure@Pass123",
            "role_id": teacher_role["id"],
            "scope_type": "PROGRAM",
        },
    )

    # Second creation with same email
    resp = await client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "email": "dup@obelytics-test.com",
            "full_name": "Second",
            "password": "Secure@Pass123",
            "role_id": teacher_role["id"],
            "scope_type": "PROGRAM",
        },
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_admin_can_list_roles(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/roles", headers=auth_headers)
    assert resp.status_code == 200
    names = [r["name"] for r in resp.json()]
    assert "Super Admin" in names
    assert "Section Teacher" in names
    assert "Student" in names


# ── Change password ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_change_password_requires_auth(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "x", "new_password": "NewSecure@123"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_change_password_wrong_current_returns_400(client: AsyncClient):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_TEACHER_EMAIL, "password": TEST_TEACHER_PASSWORD},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "definitely-wrong", "new_password": "NewSecure@123"},
    )
    assert resp.status_code == 400

    # password unchanged — original still works
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_TEACHER_EMAIL, "password": TEST_TEACHER_PASSWORD},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_change_password_flow(client: AsyncClient):
    new_password = "NewSecure@123"

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_TEACHER_EMAIL, "password": TEST_TEACHER_PASSWORD},
    )
    old_refresh = login.json()["refresh_token"]
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": TEST_TEACHER_PASSWORD, "new_password": new_password},
    )
    assert resp.status_code == 204

    # old password rejected, new one accepted
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_TEACHER_EMAIL, "password": TEST_TEACHER_PASSWORD},
    )
    assert resp.status_code == 401
    relogin = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_TEACHER_EMAIL, "password": new_password},
    )
    assert relogin.status_code == 200

    # refresh tokens issued before the change are revoked
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 401

    # restore original password so other tests keep working
    headers = {"Authorization": f"Bearer {relogin.json()['access_token']}"}
    resp = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": new_password, "new_password": TEST_TEACHER_PASSWORD},
    )
    assert resp.status_code == 204
