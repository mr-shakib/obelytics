"""
Unit tests for AuthService.

These use the real test database (seeded once per session) so they test
real SQL interactions — they are "unit" in the sense that they test a single
service class in isolation from the HTTP layer.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.iam.exceptions import InvalidCredentialsError, InvalidRefreshTokenError
from app.modules.iam.service.auth_service import AuthService
from tests.conftest import TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD


@pytest.mark.asyncio
async def test_login_returns_both_tokens(db_session: AsyncSession):
    svc = AuthService(db_session)
    result = await svc.login(TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD)

    assert result.access_token
    assert result.refresh_token
    assert result.token_type == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_raises(db_session: AsyncSession):
    svc = AuthService(db_session)
    with pytest.raises(InvalidCredentialsError):
        await svc.login(TEST_ADMIN_EMAIL, "definitely_wrong")


@pytest.mark.asyncio
async def test_login_unknown_email_raises(db_session: AsyncSession):
    svc = AuthService(db_session)
    with pytest.raises(InvalidCredentialsError):
        await svc.login("nobody@nowhere.test", "anypassword")


@pytest.mark.asyncio
async def test_login_deactivated_user_raises(db_session: AsyncSession):
    from sqlalchemy import select
    from app.modules.iam.models import User

    # Temporarily deactivate the admin, then restore
    result = await db_session.execute(
        select(User).where(User.email == TEST_ADMIN_EMAIL)
    )
    user = result.scalar_one()
    user.status = "DEACTIVATED"
    db_session.add(user)
    await db_session.flush()

    svc = AuthService(db_session)
    with pytest.raises(InvalidCredentialsError):
        await svc.login(TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD)

    # Restore (session will rollback anyway, but be explicit)
    user.status = "ACTIVE"
    db_session.add(user)
    await db_session.flush()


@pytest.mark.asyncio
async def test_refresh_issues_new_token_pair(db_session: AsyncSession):
    svc = AuthService(db_session)
    tokens = await svc.login(TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD)

    new_tokens = await svc.refresh(tokens.refresh_token)

    assert new_tokens.access_token
    assert new_tokens.refresh_token
    # Refresh token must rotate; access tokens may be identical if both
    # were generated within the same second (same iat/exp → same JWT).
    assert new_tokens.refresh_token != tokens.refresh_token


@pytest.mark.asyncio
async def test_refresh_revokes_old_token(db_session: AsyncSession):
    svc = AuthService(db_session)
    tokens = await svc.login(TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD)

    await svc.refresh(tokens.refresh_token)

    # Original refresh token must now be invalid
    with pytest.raises(InvalidRefreshTokenError):
        await svc.refresh(tokens.refresh_token)


@pytest.mark.asyncio
async def test_refresh_with_garbage_token_raises(db_session: AsyncSession):
    svc = AuthService(db_session)
    with pytest.raises(InvalidRefreshTokenError):
        await svc.refresh("not-a-real-token-at-all")


@pytest.mark.asyncio
async def test_logout_invalidates_refresh_token(db_session: AsyncSession):
    svc = AuthService(db_session)
    tokens = await svc.login(TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD)

    await svc.logout(tokens.refresh_token)

    with pytest.raises(InvalidRefreshTokenError):
        await svc.refresh(tokens.refresh_token)


@pytest.mark.asyncio
async def test_logout_is_idempotent(db_session: AsyncSession):
    """Logging out with an already-revoked token should not raise."""
    svc = AuthService(db_session)
    tokens = await svc.login(TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD)

    await svc.logout(tokens.refresh_token)
    # Second call with same token — should not raise
    await svc.logout(tokens.refresh_token)


@pytest.mark.asyncio
async def test_access_token_payload(db_session: AsyncSession):
    from app.core.security import decode_access_token

    svc = AuthService(db_session)
    tokens = await svc.login(TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD)

    payload = decode_access_token(tokens.access_token)
    assert payload["type"] == "access"
    assert "sub" in payload
    assert "org" in payload
    assert "exp" in payload
