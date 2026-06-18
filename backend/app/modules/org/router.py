import io
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.storage import presigned_get_url, put_object
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.org.repository import DepartmentRepository
from app.modules.org.schemas import (
    AssignDepartmentHead,
    DepartmentCreate,
    DepartmentHeadHistoryEntry,
    DepartmentHeadInfo,
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

_MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2MB


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
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")
    if len(raw) > _MAX_LOGO_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Logo must be 2MB or smaller")

    content_type = (file.content_type or "").lower()
    is_svg = content_type == "image/svg+xml" or (file.filename or "").lower().endswith(".svg")

    if is_svg:
        # Pillow cannot parse SVG — do a lightweight XML sanity check instead
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SVG file is not valid UTF-8") from exc
        stripped = text.lstrip()
        if "<svg" not in stripped and "<!DOCTYPE svg" not in stripped:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File does not appear to be a valid SVG")
        image_format = "svg"
        mime = "image/svg+xml"
    else:
        try:
            image = Image.open(io.BytesIO(raw))
            image.verify()
            image_format = (image.format or "png").lower()
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is not a valid image") from exc
        mime = file.content_type or f"image/{image_format}"

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
    return await svc.create(body, current_user.organization_id)


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

async def _enrich_program(program, db: AsyncSession, org_id) -> ProgramResponse:
    from app.modules.attainment.repository import AttainmentConfigRepository
    resp = ProgramResponse.model_validate(program)
    config_repo = AttainmentConfigRepository(db)
    config = await config_repo.get_for_program(org_id, program.id)
    if config:
        resp.threshold_co_score_pct = float(config.threshold_co_score_pct)
        resp.threshold_student_pct = float(config.threshold_student_pct)
    return resp


@router.get("/programs", response_model=list[ProgramResponse])
async def list_programs(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("program.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    department_id: UUID | None = None,
):
    svc = ProgramService(db)
    programs = await svc.list_active(current_user.organization_id, department_id)
    return [await _enrich_program(p, db, current_user.organization_id) for p in programs]


@router.post("/programs", response_model=ProgramResponse, status_code=status.HTTP_201_CREATED)
async def create_program(
    body: ProgramCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("program.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramService(db)
    program = await svc.create(body, current_user.organization_id)
    return await _enrich_program(program, db, current_user.organization_id)


@router.get("/programs/{program_id}", response_model=ProgramResponse)
async def get_program(
    program_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("program.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramService(db)
    program = await svc.get(program_id, current_user.organization_id)
    return await _enrich_program(program, db, current_user.organization_id)


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
    return await _enrich_program(program, db, current_user.organization_id)


@router.post("/programs/{program_id}/archive", status_code=status.HTTP_200_OK, response_model=ProgramResponse)
async def archive_program(
    program_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("program.archive"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ProgramService(db)
    program = await svc.archive(program_id, current_user.organization_id)
    return await _enrich_program(program, db, current_user.organization_id)
