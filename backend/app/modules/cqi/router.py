from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.cqi.exceptions import GapNotFoundError, GapNotWaivableError
from app.modules.cqi.schemas import (
    COAttainmentGapResponse,
    CQISummary,
    GapWaiveRequest,
    POAttainmentGapResponse,
)
from app.modules.cqi.service import CQIGapService
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse

router = APIRouter(prefix="/cqi", tags=["CQI"])

_view = require_permission("cqi.read")
_waive = require_permission("cqi.gap.waive")

_GapStatus = Annotated[
    str | None,
    Query(pattern="^(OPEN|ADDRESSED|CLOSED|WAIVED)$", description="Filter by gap status"),
]


# ── Gap lists ─────────────────────────────────────────────────────────────────

@router.get("/gaps/co", response_model=list[COAttainmentGapResponse])
async def list_co_gaps(
    _: Annotated[PermissionManifestResponse, Depends(_view)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    program_id: UUID | None = None,
    academic_term_id: UUID | None = None,
    gap_status: _GapStatus = None,
):
    svc = CQIGapService(db)
    gaps = await svc.list_co_gaps(
        current_user.organization_id, program_id, academic_term_id, gap_status
    )
    return [COAttainmentGapResponse.model_validate(g) for g in gaps]


@router.get(
    "/section-offerings/{so_id}/gaps",
    response_model=list[COAttainmentGapResponse],
)
async def list_gaps_for_offering(
    so_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_view)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CQIGapService(db)
    gaps = await svc.list_co_gaps_for_offering(current_user.organization_id, so_id)
    return [COAttainmentGapResponse.model_validate(g) for g in gaps]


@router.get("/gaps/po", response_model=list[POAttainmentGapResponse])
async def list_po_gaps(
    _: Annotated[PermissionManifestResponse, Depends(_view)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    program_id: UUID | None = None,
    academic_term_id: UUID | None = None,
    gap_status: _GapStatus = None,
):
    svc = CQIGapService(db)
    gaps = await svc.list_po_gaps(
        current_user.organization_id, program_id, academic_term_id, gap_status
    )
    return [POAttainmentGapResponse.model_validate(g) for g in gaps]


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/summary", response_model=CQISummary)
async def get_cqi_summary(
    _: Annotated[PermissionManifestResponse, Depends(_view)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    program_id: UUID | None = None,
    academic_term_id: UUID | None = None,
):
    svc = CQIGapService(db)
    return await svc.get_summary(current_user.organization_id, program_id, academic_term_id)


# ── Waivers ───────────────────────────────────────────────────────────────────

@router.post("/gaps/co/{gap_id}/waive", response_model=COAttainmentGapResponse)
async def waive_co_gap(
    gap_id: UUID,
    body: GapWaiveRequest,
    _: Annotated[PermissionManifestResponse, Depends(_waive)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CQIGapService(db)
    try:
        gap = await svc.waive_co_gap(
            current_user.organization_id, gap_id, current_user.id, body.reason
        )
    except GapNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except GapNotWaivableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return COAttainmentGapResponse.model_validate(gap)


@router.post("/gaps/po/{gap_id}/waive", response_model=POAttainmentGapResponse)
async def waive_po_gap(
    gap_id: UUID,
    body: GapWaiveRequest,
    _: Annotated[PermissionManifestResponse, Depends(_waive)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CQIGapService(db)
    try:
        gap = await svc.waive_po_gap(
            current_user.organization_id, gap_id, current_user.id, body.reason
        )
    except GapNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except GapNotWaivableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return POAttainmentGapResponse.model_validate(gap)
