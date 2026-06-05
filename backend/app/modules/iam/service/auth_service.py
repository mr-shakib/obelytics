from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis_client import get_redis
from app.core.security import (
    create_access_token,
    generate_password_reset_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.modules.iam.exceptions import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from app.modules.iam.models import PasswordCredential, RefreshToken
from app.modules.iam.repository.token_repository import RefreshTokenRepository
from app.modules.iam.repository.user_repository import UserRepository
from app.modules.iam.schemas import TokenResponse
from app.modules.iam.service.permission_service import PermissionManifestBuilder

PASSWORD_RESET_TTL = 3600  # 1 hour


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._tokens = RefreshTokenRepository(session)

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self._users.find_by_email(email)
        if user is None or user.status != "ACTIVE":
            raise InvalidCredentialsError()

        cred = user.credential
        if cred is None or not verify_password(password, cred.hashed_password):
            raise InvalidCredentialsError()

        return await self._issue_tokens(user.id, user.organization_id)

    async def refresh(self, raw_refresh_token: str) -> TokenResponse:
        token_hash = hash_refresh_token(raw_refresh_token)
        stored = await self._tokens.find_by_hash(token_hash)
        if stored is None:
            raise InvalidRefreshTokenError()

        user = await self._users.find_by_id(stored.user_id)
        if user is None or user.status != "ACTIVE":
            raise InvalidRefreshTokenError()

        await self._tokens.revoke(stored)
        return await self._issue_tokens(user.id, user.organization_id)

    async def logout(self, raw_refresh_token: str) -> None:
        token_hash = hash_refresh_token(raw_refresh_token)
        stored = await self._tokens.find_by_hash(token_hash)
        if stored:
            await self._tokens.revoke(stored)
        await self._session.commit()

    async def request_password_reset(self, email: str) -> None:
        user = await self._users.find_by_email(email)
        if user is None:
            return  # silent — don't reveal whether email exists

        reset_token = generate_password_reset_token()
        redis = await get_redis()
        await redis.setex(
            f"pwd_reset:{reset_token}",
            PASSWORD_RESET_TTL,
            str(user.id),
        )
        # TODO Phase 8: emit PasswordResetRequested event → email notification

    async def confirm_password_reset(self, token: str, new_password: str) -> None:
        redis = await get_redis()
        user_id_str = await redis.get(f"pwd_reset:{token}")
        if not user_id_str:
            from app.modules.iam.exceptions import InvalidCredentialsError
            raise InvalidCredentialsError()

        user = await self._users.find_by_id(UUID(user_id_str))
        if user is None or not user.credential:
            raise InvalidCredentialsError()

        user.credential.hashed_password = hash_password(new_password)
        user.credential.must_change_password = False
        self._session.add(user.credential)
        await self._session.commit()
        await redis.delete(f"pwd_reset:{token}")

        manifest_builder = PermissionManifestBuilder(self._session)
        await manifest_builder.invalidate(user.id)

    async def _issue_tokens(self, user_id: UUID, organization_id: UUID) -> TokenResponse:
        access_token = create_access_token(user_id, organization_id)
        raw_refresh = generate_refresh_token()

        stored = RefreshToken(
            user_id=user_id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self._session.add(stored)
        await self._session.commit()

        return TokenResponse(access_token=access_token, refresh_token=raw_refresh)
