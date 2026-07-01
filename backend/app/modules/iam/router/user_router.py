from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    get_permission_manifest,
    require_any_permission,
    require_permission,
    require_super_admin,
)
from app.modules.iam.models import User
from app.modules.iam.schemas import (
    BootstrapProgram,
    BootstrapScope,
    BootstrapUser,
    BulkCreateResult,
    BulkFacultyTypeUpdateRequest,
    BulkFacultyTypeUpdateResponse,
    FacultyRosterEntry,
    PermissionManifestResponse,
    ResetPasswordRequest,
    RoleAssignRequest,
    UserBootstrapResponse,
    UserCreate,
    UserResponse,
    UserRoleAssignmentResponse,
    UserUpdate,
)
from app.modules.iam.service.user_service import UserService
from app.modules.org.service import ProgramService


class SendCredentialsRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.get("/me/permissions", response_model=PermissionManifestResponse)
async def get_my_permissions(
    manifest: Annotated[PermissionManifestResponse, Depends(get_permission_manifest)],
):
    return manifest


@router.get("/me/bootstrap", response_model=UserBootstrapResponse)
async def get_my_bootstrap(
    current_user: Annotated[User, Depends(get_current_user)],
    manifest: Annotated[PermissionManifestResponse, Depends(get_permission_manifest)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    programs: list[BootstrapProgram] = []
    program_ids = {str(program_id) for program_id in manifest.program_ids}

    if not manifest.is_super_admin and program_ids:
        svc = ProgramService(db)
        active_programs = await svc.list_active(current_user.organization_id)
        programs = [
            BootstrapProgram(id=p.id, name=p.title, acronym=p.acronym)
            for p in active_programs
            if str(p.id) in program_ids
        ]

    full_name = current_user.full_name or ""
    first_name = getattr(current_user, "first_name", None)
    last_name = getattr(current_user, "last_name", None)
    if not first_name:
        first_name = full_name.split(" ", 1)[0] if full_name else ""
    if last_name is None and " " in full_name:
        last_name = full_name.split(" ", 1)[1]

    return UserBootstrapResponse(
        user=BootstrapUser(
            id=current_user.id,
            email=current_user.email,
            full_name=full_name,
            first_name=first_name,
            last_name=last_name or "",
            employee_id=current_user.employee_id,
            faculty_type=current_user.faculty_type,
            title=getattr(current_user, "title", None),
            designation=getattr(current_user, "designation", None),
            department=None,
            status=current_user.status,
        ),
        permissions=manifest.permissions,
        scope=BootstrapScope(programs=programs, is_global=manifest.is_super_admin),
        offering_ids=[],
    )


@router.get("", response_model=list[UserResponse])
async def list_users(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("user.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.modules.iam.repository.user_repository import UserRepository
    repo = UserRepository(db)
    return await repo.list_by_org(current_user.organization_id, include_inactive=True)


@router.get("/faculty-roster", response_model=list[FacultyRosterEntry])
async def list_faculty_roster(
    _: Annotated[
        PermissionManifestResponse,
        Depends(require_any_permission("user.read", "section_offering.manage_own", "faculty_assignment.section_teacher")),
    ],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.modules.iam.repository.user_repository import UserRepository
    repo = UserRepository(db)
    return await repo.list_active_faculty(current_user.organization_id)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("user.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = UserService(db)
    return await svc.create_user(body, current_user.organization_id, current_user.id)


@router.post("/bulk", response_model=BulkCreateResult, status_code=status.HTTP_200_OK)
async def bulk_create_users(
    body: list[UserCreate],
    _: Annotated[PermissionManifestResponse, Depends(require_permission("user.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = UserService(db)
    created: list[UserResponse] = []
    errors: list[dict] = []
    for idx, user_data in enumerate(body):
        try:
            user = await svc.create_user(user_data, current_user.organization_id, current_user.id)
            created.append(UserResponse.model_validate(user))
        except Exception as exc:
            errors.append({"row": idx + 1, "email": user_data.email, "error": str(exc)})
    return BulkCreateResult(created=created, errors=errors)


@router.post("/send-credentials", status_code=204)
async def send_credentials(
    body: SendCredentialsRequest,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("user.create"))],
):
    from app.core.email import send_credentials_email
    try:
        await send_credentials_email(body.email, body.full_name, body.password)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to send email: {exc}",
        )


@router.post("/bulk/faculty-type", response_model=BulkFacultyTypeUpdateResponse)
async def bulk_update_faculty_type(
    body: BulkFacultyTypeUpdateRequest,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("user.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = UserService(db)
    updated_count = await svc.bulk_update_faculty_type(
        body.user_ids, body.faculty_type, current_user.organization_id
    )
    return BulkFacultyTypeUpdateResponse(updated_count=updated_count)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("user.read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.modules.iam.exceptions import UserNotFoundError
    from app.modules.iam.repository.user_repository import UserRepository
    repo = UserRepository(db)
    user = await repo.find_by_id(user_id)
    if not user:
        raise UserNotFoundError(user_id)
    return user


@router.get("/{user_id}/roles", response_model=list[UserRoleAssignmentResponse])
async def get_user_roles(
    user_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("user.read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = UserService(db)
    assignments = await svc.list_roles(user_id)
    return [
        UserRoleAssignmentResponse(
            id=assignment.id,
            role_id=assignment.role_id,
            role_name=assignment.role.name,
            scope_type=assignment.scope_type,
            scope_id=assignment.scope_id,
            assigned_at=assignment.assigned_at,
        )
        for assignment in assignments
    ]


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("user.update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = UserService(db)
    return await svc.update_user(user_id, body)


@router.post("/{user_id}/reset-password", status_code=204)
async def reset_password(
    user_id: UUID,
    body: ResetPasswordRequest,
    _: Annotated[PermissionManifestResponse, Depends(require_super_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = UserService(db)
    await svc.reset_password(user_id, body.password)


@router.post("/{user_id}/deactivate", status_code=204)
async def deactivate_user(
    user_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_super_admin())],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = UserService(db)
    await svc.deactivate_user(user_id, current_user.id)


@router.post("/{user_id}/activate", status_code=204)
async def activate_user(
    user_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_super_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = UserService(db)
    await svc.activate_user(user_id)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("user.delete"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = UserService(db)
    await svc.delete_user(user_id)


@router.post("/{user_id}/roles", response_model=UserRoleAssignmentResponse, status_code=201)
async def assign_role(
    user_id: UUID,
    body: RoleAssignRequest,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("user.role.assign"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = UserService(db)
    assignment = await svc.assign_role(
        user_id, body.role_id, body.scope_type, body.scope_id, current_user.id
    )
    return UserRoleAssignmentResponse(
        id=assignment.id,
        role_id=assignment.role_id,
        role_name=assignment.role.name,
        scope_type=assignment.scope_type,
        scope_id=assignment.scope_id,
        assigned_at=assignment.assigned_at,
    )


@router.delete("/{user_id}/roles/{assignment_id}", status_code=204)
async def remove_role(
    user_id: UUID,
    assignment_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("user.role.assign"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = UserService(db)
    await svc.remove_role(user_id, assignment_id)
