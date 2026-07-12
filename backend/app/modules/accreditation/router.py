from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.arq_pool import get_arq_pool
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.accreditation.exceptions import (
    CycleClosed,
    CriterionNotFound,
    CycleNotFound,
    DuplicatePOMapping,
    InvalidStatusTransition,
)
from app.modules.accreditation.models import AccreditationCriterion, AccreditationCycle
from app.modules.accreditation.schemas import (
    AccreditationCriterionCreate,
    AccreditationCriterionResponse,
    AccreditationCriterionUpdate,
    AccreditationCycleCreate,
    AccreditationCycleDetailResponse,
    AccreditationCycleResponse,
    AccreditationCycleUpdate,
    CriterionPOMappingCreate,
    CriterionPOMappingResponse,
    CycleCriterionInfo,
)
from app.modules.accreditation.service import (
    AccreditationCriterionService,
    AccreditationCycleService,
    CriterionPOMappingService,
)
from app.modules.org.models import Program

router = APIRouter(prefix="/accreditation", tags=["Accreditation"])

_read = require_permission("accreditation.read")
_manage = require_permission("accreditation.manage")
_create = require_permission("accreditation.cycle.create")


async def _program_names(db: AsyncSession, program_ids: set[UUID]) -> dict[UUID, str]:
    if not program_ids:
        return {}
    rows = (await db.execute(select(Program.id, Program.title).where(Program.id.in_(program_ids)))).all()
    return dict(rows)


async def _cycle_response(cycle: AccreditationCycle, db: AsyncSession) -> AccreditationCycleResponse:
    names = await _program_names(db, {cycle.program_id})
    response = AccreditationCycleResponse.model_validate(cycle)
    response.program_name = names.get(cycle.program_id)
    return response


async def _cycle_detail_response(cycle: AccreditationCycle, db: AsyncSession) -> AccreditationCycleDetailResponse:
    names = await _program_names(db, {cycle.program_id})

    criteria = (
        await db.execute(
            select(AccreditationCriterion)
            .where(AccreditationCriterion.cycle_id == cycle.id)
            .order_by(AccreditationCriterion.order_index)
        )
    ).scalars().all()

    assignee_ids = {c.assigned_to_user_id for c in criteria if c.assigned_to_user_id}
    assignee_names: dict[UUID, str] = {}
    if assignee_ids:
        rows = (await db.execute(select(User.id, User.full_name).where(User.id.in_(assignee_ids)))).all()
        assignee_names = dict(rows)

    total = len(criteria)
    completed = sum(1 for c in criteria if c.status == "COMPLETED")

    response = AccreditationCycleDetailResponse(
        **AccreditationCycleResponse.model_validate(cycle).model_dump(),
        criteria=[
            CycleCriterionInfo(
                id=c.id,
                criterion_code=c.code,
                title=c.title,
                status=c.status,
                assigned_to_user_id=c.assigned_to_user_id,
                assigned_to=assignee_names.get(c.assigned_to_user_id) if c.assigned_to_user_id else None,
            )
            for c in criteria
        ],
        completion_pct=round(completed / total * 100) if total > 0 else 0,
    )
    response.program_name = names.get(cycle.program_id)
    return response


# ── Cycles ────────────────────────────────────────────────────────────────────

@router.post(
    "/cycles",
    response_model=AccreditationCycleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cycle(
    body: AccreditationCycleCreate,
    _: Annotated[PermissionManifestResponse, Depends(_create)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AccreditationCycleService(db)
    cycle = await svc.create(body, current_user.organization_id, current_user.id)
    return await _cycle_response(cycle, db)


@router.get("/cycles", response_model=list[AccreditationCycleResponse])
async def list_cycles(
    _: Annotated[PermissionManifestResponse, Depends(_read)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    program_id: UUID | None = Query(default=None),
):
    svc = AccreditationCycleService(db)
    cycles = await svc.list(current_user.organization_id, program_id)
    return [await _cycle_response(c, db) for c in cycles]


@router.get("/cycles/{cycle_id}", response_model=AccreditationCycleDetailResponse)
async def get_cycle(
    cycle_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_read)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AccreditationCycleService(db)
    try:
        cycle = await svc.get(cycle_id, current_user.organization_id)
        return await _cycle_detail_response(cycle, db)
    except CycleNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/cycles/{cycle_id}", response_model=AccreditationCycleResponse)
async def update_cycle(
    cycle_id: UUID,
    body: AccreditationCycleUpdate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AccreditationCycleService(db)
    try:
        cycle = await svc.update(cycle_id, current_user.organization_id, body)
        return await _cycle_response(cycle, db)
    except CycleNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidStatusTransition as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/cycles/{cycle_id}/activate", response_model=AccreditationCycleResponse)
async def activate_cycle(
    cycle_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AccreditationCycleService(db)
    try:
        cycle = await svc.activate(cycle_id, current_user.organization_id)
        return await _cycle_response(cycle, db)
    except CycleNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidStatusTransition as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/cycles/{cycle_id}/generate-report", status_code=status.HTTP_202_ACCEPTED)
async def generate_cycle_report(
    cycle_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AccreditationCycleService(db)
    try:
        run = await svc.prepare_report_run(cycle_id, current_user.organization_id, current_user.id)
    except CycleNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    pool = await get_arq_pool()
    await pool.enqueue_job("generate_report_run", str(run.id))
    return {"run_id": str(run.id)}


@router.post("/cycles/{cycle_id}/close", response_model=AccreditationCycleResponse)
async def close_cycle(
    cycle_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AccreditationCycleService(db)
    try:
        cycle = await svc.close(cycle_id, current_user.organization_id)
        return await _cycle_response(cycle, db)
    except CycleNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidStatusTransition as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── Criteria ──────────────────────────────────────────────────────────────────

@router.post(
    "/cycles/{cycle_id}/criteria",
    response_model=AccreditationCriterionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_criterion(
    cycle_id: UUID,
    body: AccreditationCriterionCreate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AccreditationCriterionService(db)
    try:
        return await svc.add(cycle_id, current_user.organization_id, body)
    except CycleNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except CycleClosed as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/cycles/{cycle_id}/criteria",
    response_model=list[AccreditationCriterionResponse],
)
async def list_criteria(
    cycle_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_read)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AccreditationCriterionService(db)
    try:
        return await svc.list(cycle_id, current_user.organization_id)
    except CycleNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch(
    "/criteria/{criterion_id}",
    response_model=AccreditationCriterionResponse,
)
async def update_criterion(
    criterion_id: UUID,
    body: AccreditationCriterionUpdate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AccreditationCriterionService(db)
    try:
        return await svc.update(criterion_id, current_user.organization_id, body)
    except CriterionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except CycleNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/criteria/{criterion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_criterion(
    criterion_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AccreditationCriterionService(db)
    try:
        await svc.remove(criterion_id, current_user.organization_id)
    except CriterionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except CycleNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ── PO Mappings ───────────────────────────────────────────────────────────────

@router.post(
    "/criteria/{criterion_id}/po-mappings",
    response_model=CriterionPOMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def map_po(
    criterion_id: UUID,
    body: CriterionPOMappingCreate,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CriterionPOMappingService(db)
    try:
        return await svc.map_po(criterion_id, current_user.organization_id, body)
    except CriterionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DuplicatePOMapping as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/criteria/{criterion_id}/po-mappings",
    response_model=list[CriterionPOMappingResponse],
)
async def list_po_mappings(
    criterion_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_read)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CriterionPOMappingService(db)
    try:
        return await svc.list(criterion_id, current_user.organization_id)
    except CriterionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete(
    "/criteria/{criterion_id}/po-mappings/{po_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unmap_po(
    criterion_id: UUID,
    po_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CriterionPOMappingService(db)
    try:
        await svc.unmap_po(criterion_id, po_id, current_user.organization_id)
    except CriterionNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
