from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.arq_pool import get_arq_pool
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_any_permission, require_permission
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.reporting.exceptions import UnknownReportDefinitionError
from app.modules.reporting.models import ReportRun
from app.modules.reporting.schemas import (
    AssessmentSummaryReport,
    COAttainmentReport,
    ProgramPOAttainmentReport,
    ReportDefinition,
    ReportRunCreate,
    ReportRunDetailResponse,
    ReportRunResponse,
)
from app.modules.reporting.service import (
    REPORT_DEFINITIONS,
    AssessmentSummaryService,
    COAttainmentReportService,
    ProgramPOAttainmentReportService,
    ReportRunService,
    list_available_definitions,
)

router = APIRouter(prefix="/reports", tags=["Reports"])

_assess_perm = require_permission("report.assessment.generate")
_co_perm = require_permission("report.co.generate")
_prog_perm = require_permission("report.generate")
_any_report_perm = require_any_permission(
    "report.generate", "report.assessment.generate", "report.co.generate"
)


async def _run_response(run: ReportRun, svc: ReportRunService) -> ReportRunResponse:
    return ReportRunResponse(
        id=run.id,
        definition_id=run.definition_id,
        definition_name=run.definition_name,
        status=run.status,
        created_at=run.created_at,
        completed_at=run.completed_at,
        output_url=await svc.output_url(run),
    )


async def _run_detail_response(run: ReportRun, svc: ReportRunService) -> ReportRunDetailResponse:
    return ReportRunDetailResponse(
        id=run.id,
        definition_id=run.definition_id,
        definition_name=run.definition_name,
        status=run.status,
        created_at=run.created_at,
        completed_at=run.completed_at,
        output_url=await svc.output_url(run),
        params=run.params,
        summary=run.summary,
        error=run.error,
    )


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


# ── Report runs (async generation) ──────────────────────────────────────────────

@router.get("/definitions", response_model=list[ReportDefinition])
async def list_report_definitions(
    manifest: Annotated[PermissionManifestResponse, Depends(_any_report_perm)],
):
    return list_available_definitions(manifest)


@router.get("/runs", response_model=list[ReportRunResponse])
async def list_report_runs(
    _: Annotated[PermissionManifestResponse, Depends(_any_report_perm)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ReportRunService(db)
    runs = await svc.list_runs(current_user.organization_id, current_user.id)
    return [await _run_response(r, svc) for r in runs]


@router.post("/runs", response_model=ReportRunResponse, status_code=status.HTTP_201_CREATED)
async def create_report_run(
    body: ReportRunCreate,
    manifest: Annotated[PermissionManifestResponse, Depends(_any_report_perm)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    definition = next((d for d in REPORT_DEFINITIONS if d["id"] == body.definition_id), None)
    if definition is None:
        raise UnknownReportDefinitionError(body.definition_id)
    if not manifest.is_super_admin and definition["permission"] not in manifest.permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted to generate this report")

    params: dict = {}
    if body.definition_id == "program_po_attainment" and not manifest.is_super_admin and manifest.program_ids:
        params["program_ids"] = [str(pid) for pid in manifest.program_ids]

    svc = ReportRunService(db)
    run = await svc.create_run(
        current_user.organization_id,
        current_user.id,
        definition_id=definition["id"],
        definition_name=definition["name"],
        params=params,
    )

    pool = await get_arq_pool()
    await pool.enqueue_job("generate_report_run", str(run.id))

    return await _run_response(run, svc)


@router.get("/runs/{run_id}", response_model=ReportRunDetailResponse)
async def get_report_run(
    run_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(_any_report_perm)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ReportRunService(db)
    run = await svc.get_run(run_id, current_user.organization_id, current_user.id)
    return await _run_detail_response(run, svc)
