from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.reporting.schemas import (
    AssessmentSummaryReport,
    COAttainmentReport,
    ProgramPOAttainmentReport,
)
from app.modules.reporting.service import (
    AssessmentSummaryService,
    COAttainmentReportService,
    ProgramPOAttainmentReportService,
)

router = APIRouter(prefix="/reports", tags=["Reports"])

_assess_perm = require_permission("report.assessment.generate")
_co_perm = require_permission("report.co.generate")
_prog_perm = require_permission("report.generate")


@router.get(
    "/section-offerings/{so_id}/assessment-summary",
    response_model=AssessmentSummaryReport,
)
async def get_assessment_summary(
    so_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_assess_perm)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AssessmentSummaryService(db)
    return await svc.generate(current_user.organization_id, so_id)


@router.get(
    "/section-offerings/{so_id}/co-attainment",
    response_model=COAttainmentReport,
)
async def get_co_attainment_report(
    so_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_co_perm)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = COAttainmentReportService(db)
    return await svc.generate(current_user.organization_id, so_id)


@router.get(
    "/programs/{program_id}/po-attainment",
    response_model=ProgramPOAttainmentReport,
)
async def get_program_po_attainment(
    program_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_prog_perm)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    academic_term_id: UUID = Query(...),
):
    svc = ProgramPOAttainmentReportService(db)
    return await svc.generate(current_user.organization_id, program_id, academic_term_id)
