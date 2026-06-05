from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.org.schemas import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    OrgResponse,
    OrgUpdate,
    ProgramCreate,
    ProgramResponse,
    ProgramUpdate,
)
from app.modules.org.service import DepartmentService, OrgService, ProgramService

router = APIRouter(tags=["Organization"])


# ── Organization ──────────────────────────────────────────────────────────────

@router.get("/organization", response_model=OrgResponse)
async def get_organization(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("system.organization.configure"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = OrgService(db)
    return await svc.get(current_user.organization_id)


@router.patch("/organization", response_model=OrgResponse)
async def update_organization(
    body: OrgUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("system.organization.configure"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = OrgService(db)
    return await svc.update(current_user.organization_id, body)


# ── Departments ───────────────────────────────────────────────────────────────

@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("department.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = DepartmentService(db)
    return await svc.list_active(current_user.organization_id)


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    body: DepartmentCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("department.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = DepartmentService(db)
    return await svc.create(body, current_user.organization_id)


@router.get("/departments/{dept_id}", response_model=DepartmentResponse)
async def get_department(
    dept_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("department.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = DepartmentService(db)
    return await svc.get(dept_id, current_user.organization_id)


@router.patch("/departments/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    dept_id: UUID,
    body: DepartmentUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("department.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = DepartmentService(db)
    return await svc.update(dept_id, body, current_user.organization_id)


@router.post("/departments/{dept_id}/archive", status_code=status.HTTP_200_OK, response_model=DepartmentResponse)
async def archive_department(
    dept_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("department.archive"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = DepartmentService(db)
    return await svc.archive(dept_id, current_user.organization_id)


# ── Programs ──────────────────────────────────────────────────────────────────

@router.get("/programs", response_model=list[ProgramResponse])
async def list_programs(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("program.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    department_id: UUID | None = None,
):
    svc = ProgramService(db)
    return await svc.list_active(current_user.organization_id, department_id)


@router.post("/programs", response_model=ProgramResponse, status_code=status.HTTP_201_CREATED)
async def create_program(
    body: ProgramCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("program.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramService(db)
    return await svc.create(body, current_user.organization_id)


@router.get("/programs/{program_id}", response_model=ProgramResponse)
async def get_program(
    program_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("program.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramService(db)
    return await svc.get(program_id, current_user.organization_id)


@router.patch("/programs/{program_id}", response_model=ProgramResponse)
async def update_program(
    program_id: UUID,
    body: ProgramUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("program.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramService(db)
    return await svc.update(program_id, body, current_user.organization_id)


@router.post("/programs/{program_id}/archive", status_code=status.HTTP_200_OK, response_model=ProgramResponse)
async def archive_program(
    program_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("program.archive"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramService(db)
    return await svc.archive(program_id, current_user.organization_id)
