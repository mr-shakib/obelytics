from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    require_permission,
    require_super_admin,
)
from app.modules.iam.exceptions import RoleNotFoundError, SystemRoleProtectedError
from app.modules.iam.models import Role, RolePermission, User
from app.modules.iam.repository.role_repository import PermissionRepository, RoleRepository
from app.modules.iam.schemas import (
    AddPermissionRequest,
    PermissionManifestResponse,
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    RoleWithPermissionsResponse,
    SetPermissionsRequest,
)

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("", response_model=list[RoleResponse])
async def list_roles(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = RoleRepository(db)
    return await repo.list_by_org(current_user.organization_id)


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    body: RoleCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("system.roles.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    role = Role(
        organization_id=current_user.organization_id,
        name=body.name,
        description=body.description,
        is_system_role=False,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


# ── Literal paths must come BEFORE /{role_id} to avoid path-param collision ──

@router.get("/permissions/all", response_model=list[PermissionResponse])
async def list_all_permissions(
    _: Annotated[
        PermissionManifestResponse,
        Depends(require_permission("system.permissions.grant")),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = PermissionRepository(db)
    return await repo.list_all()


@router.get("/with-permissions", response_model=list[RoleWithPermissionsResponse])
async def list_roles_with_permissions(
    _: Annotated[
        PermissionManifestResponse,
        Depends(require_permission("system.permissions.grant")),
    ],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Return all roles and permission codes to permission-management users."""
    role_repo = RoleRepository(db)
    roles = await role_repo.list_by_org(current_user.organization_id)
    result = []
    for role in roles:
        role_with_perms = await role_repo.get_by_id(role.id)
        result.append(
            RoleWithPermissionsResponse(
                id=role.id,
                name=role.name,
                description=role.description,
                is_system_role=role.is_system_role,
                permission_codes=[p.code for p in (role_with_perms.permissions if role_with_perms else [])],
            )
        )
    return result


# ── Parameterised routes ──────────────────────────────────────────────────────

@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = RoleRepository(db)
    role = await repo.get_by_id(role_id)
    if not role:
        raise RoleNotFoundError()
    return role


@router.get("/{role_id}/permissions", response_model=list[PermissionResponse])
async def get_role_permissions(
    role_id: UUID,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = RoleRepository(db)
    role = await repo.get_by_id(role_id)
    if not role:
        raise RoleNotFoundError()
    return role.permissions


@router.post("/{role_id}/permissions", status_code=204)
async def add_permission_to_role(
    role_id: UUID,
    body: AddPermissionRequest,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("system.permissions.grant"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = RoleRepository(db)
    role = await repo.get_by_id(role_id)
    if not role:
        raise RoleNotFoundError()
    if role.is_system_role:
        raise SystemRoleProtectedError()
    await repo.add_permission(role_id, body.permission_id)
    await db.commit()


@router.delete("/{role_id}/permissions/{permission_id}", status_code=204)
async def remove_permission_from_role(
    role_id: UUID,
    permission_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("system.permissions.grant"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = RoleRepository(db)
    role = await repo.get_by_id(role_id)
    if not role:
        raise RoleNotFoundError()
    if role.is_system_role:
        raise SystemRoleProtectedError()
    await repo.remove_permission(role_id, permission_id)
    await db.commit()


@router.put("/{role_id}/permissions", status_code=204)
async def set_role_permissions(
    role_id: UUID,
    body: SetPermissionsRequest,
    _: Annotated[PermissionManifestResponse, Depends(require_super_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Replace the full permission set for any role (super admin only, bypasses system-role guard)."""
    repo = RoleRepository(db)
    role = await repo.get_by_id(role_id)
    if not role:
        raise RoleNotFoundError()

    await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    for perm_id in body.permission_ids:
        db.add(RolePermission(role_id=role_id, permission_id=perm_id))

    await db.commit()
