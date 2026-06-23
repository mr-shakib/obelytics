import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.core.security import decode_access_token
from app.modules.iam.models import User
from app.modules.iam.repository.user_repository import UserRepository
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.iam.service.permission_service import PermissionManifestBuilder

logger = logging.getLogger("app.auth")

_bearer = HTTPBearer()

_unauthorized = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

USER_CACHE_TTL = 900  # 15 minutes, matches access token lifetime


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("type") != "access":
            raise _unauthorized
        user_id: str = payload.get("sub", "")
    except JWTError:
        raise _unauthorized

    uid = UUID(user_id)

    # Try Redis cache — store user_id to skip the decode+DB query on repeated calls
    # but we still need the User ORM object, so only skip the find_by_id if we can
    # attach the cached user to the request for downstream use.
    try:
        redis = await get_redis()
        cached = await redis.get(f"auth:{user_id}:user")
        if cached:
            data = json.loads(cached)
            # Build a minimal User-like object from cache
            user = User.__new__(User)
            user.id = uid
            user.organization_id = UUID(data["organization_id"])
            user.email = data["email"]
            user.full_name = data.get("full_name")
            user.employee_id = data.get("employee_id")
            user.faculty_type = data.get("faculty_type")
            user.title = data.get("title")
            user.designation = data.get("designation")
            user.department_id = UUID(data["department_id"]) if data.get("department_id") else None
            user.status = data["status"]
            if user.status != "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated"
                )
            return user
    except (HTTPException, json.JSONDecodeError):
        raise
    except Exception:
        pass  # cache miss or redis down — fall through to DB

    repo = UserRepository(db)
    user = await repo.find_by_id(uid)
    if user is None:
        raise _unauthorized
    if user.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    # Cache user for subsequent requests
    try:
        redis = await get_redis()
        user_data = {
            "organization_id": str(user.organization_id),
            "email": user.email,
            "full_name": user.full_name,
            "employee_id": user.employee_id,
            "faculty_type": user.faculty_type,
            "title": user.title,
            "designation": user.designation,
            "department_id": str(user.department_id) if user.department_id else None,
            "status": user.status,
        }
        await redis.setex(f"auth:{user_id}:user", USER_CACHE_TTL, json.dumps(user_data))
    except Exception:
        pass  # non-critical

    return user


async def get_permission_manifest(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PermissionManifestResponse:
    builder = PermissionManifestBuilder(db)
    return await builder.build_manifest(current_user.id)


def require_permission(code: str):
    async def gate(
        manifest: Annotated[PermissionManifestResponse, Depends(get_permission_manifest)],
    ) -> PermissionManifestResponse:
        if manifest.is_super_admin:
            return manifest
        if code not in manifest.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return manifest

    return gate


def require_any_permission(*codes: str):
    async def gate(
        manifest: Annotated[PermissionManifestResponse, Depends(get_permission_manifest)],
    ) -> PermissionManifestResponse:
        if manifest.is_super_admin:
            return manifest
        if not any(code in manifest.permissions for code in codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return manifest

    return gate


def require_super_admin():
    async def gate(
        manifest: Annotated[PermissionManifestResponse, Depends(get_permission_manifest)],
    ) -> PermissionManifestResponse:
        if not manifest.is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return manifest

    return gate
