from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.assessment.schemas import (
    AssessmentCOWeightCreate,
    AssessmentCOWeightResponse,
    AssessmentCreate,
    AssessmentResponse,
    AssessmentUpdate,
    EnrollmentCreate,
    EnrollmentResponse,
    MarkCreate,
    MarkResponse,
    MarkUpdate,
    MLRejectRequest,
    ResultPublicationResponse,
    StudentCreate,
    StudentResponse,
    StudentUpdate,
)
from app.modules.assessment.service import (
    AssessmentService,
    EnrollmentService,
    MarksService,
    ResultPublicationService,
    StudentService,
)

router = APIRouter(tags=["Assessment"])


# ── Students ──────────────────────────────────────────────────────────────────

@router.get("/students", response_model=list[StudentResponse])
async def list_students(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    program_id: UUID | None = None,
):
    svc = StudentService(db)
    return await svc.list_active(current_user.organization_id, program_id)


@router.post("/students", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    body: StudentCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.configure"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = StudentService(db)
    return await svc.create(body, current_user.organization_id)


@router.get("/students/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = StudentService(db)
    return await svc.get(student_id, current_user.organization_id)


@router.patch("/students/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: UUID,
    body: StudentUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.configure"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = StudentService(db)
    return await svc.update(student_id, body, current_user.organization_id)


# ── Enrollments ───────────────────────────────────────────────────────────────

@router.get("/enrollments", response_model=list[EnrollmentResponse])
async def list_enrollments(
    section_offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = EnrollmentService(db)
    return await svc.list_by_offering(section_offering_id, current_user.organization_id)


@router.post("/enrollments", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def create_enrollment(
    body: EnrollmentCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.configure"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = EnrollmentService(db)
    return await svc.enroll(body, current_user.organization_id)


# ── Assessments ───────────────────────────────────────────────────────────────

@router.get("/assessments", response_model=list[AssessmentResponse])
async def list_assessments(
    section_offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AssessmentService(db)
    return await svc.list_by_offering(section_offering_id, current_user.organization_id)


@router.post("/assessments", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    body: AssessmentCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.configure"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AssessmentService(db)
    return await svc.create(body, current_user.organization_id)


@router.get("/assessments/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AssessmentService(db)
    return await svc.get(assessment_id, current_user.organization_id)


@router.patch("/assessments/{assessment_id}", response_model=AssessmentResponse)
async def update_assessment(
    assessment_id: UUID,
    body: AssessmentUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.configure"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AssessmentService(db)
    return await svc.update(assessment_id, body, current_user.organization_id)


@router.post("/assessments/{assessment_id}/open-marks", response_model=AssessmentResponse)
async def open_marks(
    assessment_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.publish_config"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AssessmentService(db)
    return await svc.open_marks(assessment_id, current_user.organization_id)


@router.get("/assessments/{assessment_id}/co-weights", response_model=list[AssessmentCOWeightResponse])
async def list_co_weights(
    assessment_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AssessmentService(db)
    return await svc.list_co_weights(assessment_id, current_user.organization_id)


@router.post(
    "/assessments/{assessment_id}/co-weights",
    response_model=AssessmentCOWeightResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_co_weight(
    assessment_id: UUID,
    body: AssessmentCOWeightCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.configure"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AssessmentService(db)
    return await svc.add_co_weight(assessment_id, body, current_user.organization_id)


@router.delete(
    "/assessments/{assessment_id}/co-weights/{weight_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_co_weight(
    assessment_id: UUID,
    weight_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.configure"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AssessmentService(db)
    await svc.remove_co_weight(assessment_id, weight_id, current_user.organization_id)


# ── Marks ─────────────────────────────────────────────────────────────────────

@router.get("/marks", response_model=list[MarkResponse])
async def list_marks(
    assessment_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("marks.read.section"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MarksService(db)
    return await svc.list_by_assessment(assessment_id, current_user.organization_id)


@router.post("/marks", response_model=MarkResponse, status_code=status.HTTP_201_CREATED)
async def enter_mark(
    body: MarkCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("marks.enter"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MarksService(db)
    return await svc.enter_mark(body, current_user.organization_id, current_user.id)


@router.get("/marks/{mark_id}", response_model=MarkResponse)
async def get_mark(
    mark_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("marks.read.section"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MarksService(db)
    return await svc.get_mark(mark_id, current_user.organization_id)


@router.patch("/marks/{mark_id}", response_model=MarkResponse)
async def update_mark(
    mark_id: UUID,
    body: MarkUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("marks.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MarksService(db)
    return await svc.update_mark(mark_id, body, current_user.organization_id)


# ── Results ───────────────────────────────────────────────────────────────────

@router.get("/results/{section_offering_id}", response_model=ResultPublicationResponse)
async def get_result_publication(
    section_offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ResultPublicationService(db)
    return await svc.get_by_offering(section_offering_id, current_user.organization_id)


@router.post("/results/{section_offering_id}/submit", response_model=ResultPublicationResponse)
async def submit_results(
    section_offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("result.submit"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ResultPublicationService(db)
    return await svc.submit(section_offering_id, current_user.organization_id, current_user.id)


@router.post("/results/{section_offering_id}/approve-ml", response_model=ResultPublicationResponse)
async def approve_ml(
    section_offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("result.approve.ml"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ResultPublicationService(db)
    return await svc.approve_ml(section_offering_id, current_user.organization_id, current_user.id)


@router.post("/results/{section_offering_id}/reject-ml", response_model=ResultPublicationResponse)
async def reject_ml(
    section_offering_id: UUID,
    body: MLRejectRequest,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("result.reject.ml"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ResultPublicationService(db)
    return await svc.reject_ml(
        section_offering_id, current_user.organization_id, current_user.id, body.comment
    )


@router.post("/results/{section_offering_id}/approve-pc", response_model=ResultPublicationResponse)
async def approve_pc(
    section_offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("result.approve.pc"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ResultPublicationService(db)
    return await svc.approve_pc(section_offering_id, current_user.organization_id, current_user.id)


@router.post("/results/{section_offering_id}/publish", response_model=ResultPublicationResponse)
async def publish_results(
    section_offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("result.publish"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ResultPublicationService(db)
    return await svc.publish(section_offering_id, current_user.organization_id, current_user.id)
