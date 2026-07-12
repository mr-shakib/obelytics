import io
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_any_permission, require_permission
from app.core.storage import presigned_get_url, put_object
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.org.repository import DepartmentRepository, ProgramRepository
from app.modules.org.schemas import (
    AssignDepartmentHead,
    AssignProgramCoordinator,
    DepartmentCreate,
    DepartmentHeadHistoryEntry,
    DepartmentHeadInfo,
    DepartmentResponse,
    DepartmentUpdate,
    OrgResponse,
    OrgUpdate,
    ProgramCoordinatorHistoryEntry,
    ProgramCoordinatorInfo,
    ProgramCreate,
    ProgramResponse,
    ProgramUpdate,
)
from app.modules.org.service import DepartmentService, OrgService, ProgramService

router = APIRouter(tags=["Organization"])

_MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2MB


async def _validate_logo_upload(file: UploadFile) -> tuple[bytes, str, str]:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")
    if len(raw) > _MAX_LOGO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Logo must be 2MB or smaller",
        )

    content_type = (file.content_type or "").lower()
    is_svg = content_type == "image/svg+xml" or (file.filename or "").lower().endswith(".svg")

    if is_svg:
        # Pillow cannot parse SVG — do a lightweight XML sanity check instead
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SVG file is not valid UTF-8",
            ) from exc
        stripped = text.lstrip()
        if "<svg" not in stripped and "<!DOCTYPE svg" not in stripped:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File does not appear to be a valid SVG",
            )
        return raw, "svg", "image/svg+xml"

    try:
        image = Image.open(io.BytesIO(raw))
        image.verify()
        image_format = (image.format or "png").lower()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is not a valid image") from exc
    return raw, image_format, file.content_type or f"image/{image_format}"


async def _org_response(org) -> OrgResponse:
    response = OrgResponse.model_validate(org)
    if org.logo_file_key:
        response.logo_url = await presigned_get_url(settings.MINIO_BUCKET_LOGOS, org.logo_file_key)
    return response


async def _department_response(dept, db: AsyncSession) -> DepartmentResponse:
    history = await DepartmentRepository(db).list_head_history(dept.id)
    names: dict[UUID, str] = {}
    user_ids = {h.user_id for h in history}
    if user_ids:
        result = await db.execute(select(User.id, User.full_name).where(User.id.in_(user_ids)))
        names = dict(result.all())

    response = DepartmentResponse.model_validate(dept)
    if dept.logo_file_key:
        response.logo_url = await presigned_get_url(settings.MINIO_BUCKET_LOGOS, dept.logo_file_key)
    current = next((h for h in history if h.effective_to is None), None)
    response.current_hod = (
        DepartmentHeadInfo(user_id=current.user_id, full_name=names.get(current.user_id, "Unknown"))
        if current is not None else None
    )
    response.hod_history = [
        DepartmentHeadHistoryEntry(
            user_id=h.user_id,
            full_name=names.get(h.user_id, "Unknown"),
            effective_from=h.effective_from,
            effective_to=h.effective_to,
        )
        for h in history
    ]
    return response


async def _program_response(program, db: AsyncSession) -> ProgramResponse:
    history = await ProgramRepository(db).list_coordinator_history(program.id)
    names: dict[UUID, str] = {}
    user_ids = {h.user_id for h in history}
    if user_ids:
        result = await db.execute(select(User.id, User.full_name).where(User.id.in_(user_ids)))
        names = dict(result.all())

    response = ProgramResponse.model_validate(program)
    current = next((h for h in history if h.effective_to is None), None)
    response.current_coordinator = (
        ProgramCoordinatorInfo(user_id=current.user_id, full_name=names.get(current.user_id, "Unknown"))
        if current is not None else None
    )
    response.coordinator_history = [
        ProgramCoordinatorHistoryEntry(
            user_id=h.user_id,
            full_name=names.get(h.user_id, "Unknown"),
            effective_from=h.effective_from,
            effective_to=h.effective_to,
        )
        for h in history
    ]
    return response


# ── Organization ──────────────────────────────────────────────────────────────

@router.get("/organization", response_model=OrgResponse)
async def get_organization(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("system.organization.configure"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = OrgService(db)
    org = await svc.get(current_user.organization_id)
    return await _org_response(org)


@router.patch("/organization", response_model=OrgResponse)
async def update_organization(
    body: OrgUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("system.organization.configure"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = OrgService(db)
    org = await svc.update(current_user.organization_id, body)
    return await _org_response(org)


@router.post("/organization/logo", response_model=OrgResponse)
async def upload_organization_logo(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("system.organization.configure"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
):
    raw, image_format, mime = await _validate_logo_upload(file)

    svc = OrgService(db)
    org = await svc.get(current_user.organization_id)
    key = f"{org.id}/logo.{image_format}"
    await put_object(settings.MINIO_BUCKET_LOGOS, key, raw, mime)

    org = await svc.update(current_user.organization_id, OrgUpdate(logo_file_key=key))
    return await _org_response(org)


# ── Departments ───────────────────────────────────────────────────────────────

@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("department.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = DepartmentService(db)
    depts = await svc.list_active(current_user.organization_id)
    return [await _department_response(d, db) for d in depts]


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    body: DepartmentCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("department.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = DepartmentService(db)
    dept = await svc.create(body, current_user.organization_id)
    return await _department_response(dept, db)


@router.get("/departments/{dept_id}", response_model=DepartmentResponse)
async def get_department(
    dept_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("department.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = DepartmentService(db)
    dept = await svc.get(dept_id, current_user.organization_id)
    return await _department_response(dept, db)


@router.patch("/departments/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    dept_id: UUID,
    body: DepartmentUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("department.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = DepartmentService(db)
    dept = await svc.update(dept_id, body, current_user.organization_id)
    return await _department_response(dept, db)


@router.post("/departments/{dept_id}/logo", response_model=DepartmentResponse)
async def upload_department_logo(
    dept_id: UUID,
    _: Annotated[
        PermissionManifestResponse,
        Depends(require_any_permission("department.create", "department.update")),
    ],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
):
    raw, image_format, mime = await _validate_logo_upload(file)

    svc = DepartmentService(db)
    dept = await svc.get(dept_id, current_user.organization_id)
    key = f"{current_user.organization_id}/departments/{dept.id}/logo.{image_format}"
    await put_object(settings.MINIO_BUCKET_LOGOS, key, raw, mime)

    dept = await svc.update(
        dept_id,
        DepartmentUpdate(logo_file_key=key),
        current_user.organization_id,
    )
    return await _department_response(dept, db)


@router.post("/departments/{dept_id}/head", response_model=DepartmentResponse)
async def assign_department_head(
    dept_id: UUID,
    body: AssignDepartmentHead,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("department.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = DepartmentService(db)
    dept = await svc.assign_head(dept_id, body.user_id, current_user.organization_id)
    return await _department_response(dept, db)


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
    programs = await svc.list_active(current_user.organization_id, department_id)
    return [await _program_response(p, db) for p in programs]


@router.post("/programs", response_model=ProgramResponse, status_code=status.HTTP_201_CREATED)
async def create_program(
    body: ProgramCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("program.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramService(db)
    program = await svc.create(body, current_user.organization_id)
    return await _program_response(program, db)


@router.get("/programs/{program_id}", response_model=ProgramResponse)
async def get_program(
    program_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("program.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramService(db)
    program = await svc.get(program_id, current_user.organization_id)
    return await _program_response(program, db)


@router.patch("/programs/{program_id}", response_model=ProgramResponse)
async def update_program(
    program_id: UUID,
    body: ProgramUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("program.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramService(db)
    program = await svc.update(program_id, body, current_user.organization_id)
    return await _program_response(program, db)


@router.post("/programs/{program_id}/coordinator", response_model=ProgramResponse)
async def assign_program_coordinator(
    program_id: UUID,
    body: AssignProgramCoordinator,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("program.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramService(db)
    program = await svc.assign_coordinator(
        program_id, body.user_id, current_user.organization_id, current_user.id
    )
    return await _program_response(program, db)


@router.post("/programs/{program_id}/archive", status_code=status.HTTP_200_OK, response_model=ProgramResponse)
async def archive_program(
    program_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("program.archive"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramService(db)
    program = await svc.archive(program_id, current_user.organization_id)
    return await _program_response(program, db)


@router.delete("/programs/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_program(
    program_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("program.delete"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Permanently deletes a program. Blocked if the program has curricula,
    students, or accreditation cycles — archive it instead in that case."""
    svc = ProgramService(db)
    await svc.delete(program_id, current_user.organization_id)
