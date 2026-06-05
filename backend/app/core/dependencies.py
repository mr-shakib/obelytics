from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.modules.iam.models import User
from app.modules.iam.repository.user_repository import UserRepository
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.iam.service.permission_service import PermissionManifestBuilder

_bearer = HTTPBearer()

_unauthorized = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
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

    repo = UserRepository(db)
    user = await repo.find_by_id(UUID(user_id))
    if user is None:
        raise _unauthorized
    if user.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
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
                detail=f"Permission '{code}' required",
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
                detail="Super admin access required",
            )
        return manifest
    return gate
