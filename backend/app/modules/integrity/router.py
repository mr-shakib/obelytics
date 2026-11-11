import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.integrity.exceptions import JobSubmissionError
from app.modules.integrity.jobs import JobRunner, get_job_runner
from app.modules.integrity.models import IntegrityJob
from app.modules.integrity.schemas import (
    AuditableSection,
    AuditReviewRequest,
    ExamType,
    IntegrityOverview,
    QuestionTextsUpdate,
)
from app.modules.integrity.service import IntegrityService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrity", tags=["Integrity"])

_read = require_permission("integrity.read")
_manage = require_permission("integrity.manage")


async def _submit(svc: IntegrityService, runner: JobRunner, job: IntegrityJob, payload: dict | None) -> None:
    try:
        await runner.submit(job.id, payload)
    except Exception as exc:
        logger.exception("Could not hand integrity job %s to the worker", job.id)
        await svc.submission_failed(job, "The background worker could not be reached. Try again.")
        raise JobSubmissionError() from exc


@router.get("/sections", response_model=list[AuditableSection])
async def list_auditable_sections(
    manifest: Annotated[PermissionManifestResponse, Depends(_read)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await IntegrityService(db).list_sections(current_user, manifest)


@router.get("/sections/{section_offering_id}", response_model=IntegrityOverview)
async def get_integrity_overview(
    section_offering_id: UUID,
    exam_type: ExamType,
    manifest: Annotated[PermissionManifestResponse, Depends(_read)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Poll this while `job` is QUEUED or RUNNING to follow its progress."""
    svc = IntegrityService(db)
    offering = await svc.get_offering(section_offering_id, current_user, manifest)
    return await svc.overview(offering, exam_type)


@router.post(
    "/sections/{section_offering_id}/paper",
    response_model=IntegrityOverview,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_question_paper(
    section_offering_id: UUID,
    exam_type: ExamType,
    manifest: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    runner: Annotated[JobRunner, Depends(get_job_runner)],
    file: Annotated[UploadFile, File(description="Question paper: PDF, Word (.docx), JPEG, PNG or WebP")],
):
    """Start reading the paper in the background. The file itself is not stored."""
    svc = IntegrityService(db)
    offering = await svc.get_offering(section_offering_id, current_user, manifest)
    data = await file.read(settings.INTEGRITY_MAX_UPLOAD_BYTES + 1)
    job, payload = await svc.start_reading(
        offering, exam_type, file.filename, file.content_type, data, current_user.id
    )
    await _submit(svc, runner, job, payload)
    return await svc.overview(offering, exam_type)


@router.put("/sections/{section_offering_id}/question-texts", response_model=IntegrityOverview)
async def save_question_texts(
    section_offering_id: UUID,
    exam_type: ExamType,
    body: QuestionTextsUpdate,
    manifest: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = IntegrityService(db)
    offering = await svc.get_offering(section_offering_id, current_user, manifest)
    await svc.save_question_texts(offering, exam_type, body.items, current_user.id)
    return await svc.overview(offering, exam_type)


@router.post(
    "/sections/{section_offering_id}/audit",
    response_model=IntegrityOverview,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_integrity_audit(
    section_offering_id: UUID,
    exam_type: ExamType,
    manifest: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    runner: Annotated[JobRunner, Depends(get_job_runner)],
):
    """Start judging every question that has wording. Advisory: marks and attainment are untouched."""
    svc = IntegrityService(db)
    offering = await svc.get_offering(section_offering_id, current_user, manifest)
    job = await svc.start_audit(offering, exam_type, current_user.id)
    await _submit(svc, runner, job, None)
    return await svc.overview(offering, exam_type)


@router.post("/audits/{audit_id}/review", response_model=IntegrityOverview)
async def review_question_audit(
    audit_id: UUID,
    body: AuditReviewRequest,
    manifest: Annotated[PermissionManifestResponse, Depends(_manage)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = IntegrityService(db)
    offering, exam_type = await svc.review(audit_id, body.decision, body.reason, current_user, manifest)
    return await svc.overview(offering, exam_type)
