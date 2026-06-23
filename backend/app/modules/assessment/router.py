from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_any_permission, require_permission
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.assessment.schemas import (
    AssessmentCOWeightCreate,
    AssessmentCOWeightResponse,
    BulkApproveMLRequest,
    BulkApproveMLResponse,
    AssessmentCreate,
    AssessmentResponse,
    AssessmentUpdate,
    BulkApprovePCRequest,
    BulkApprovePCResponse,
    CombinedEndReportPdfRequest,
    CourseEndReportResponse,
    CourseEndReportSubmit,
    PublicStudentResults,
    StudentCourseResult,
    EnrollmentBulkCreate,
    EnrollmentBulkResponse,
    EnrollmentCreate,
    EnrollmentResponse,
    EnrollmentWithStudentResponse,
    MarkCreate,
    MarkResponse,
    MarkUpdate,
    MarksheetAttainmentResponse,
    MarksheetCellUpdate,
    MarksheetGridResponse,
    MarksheetMarkResponse,
    MarksheetQuestionResponse,
    MarksheetQuestionsUpdate,
    MLRejectRequest,
    ResultPublicationResponse,
    ResultSubmissionListItem,
    StudentBulkImportRequest,
    StudentBulkImportResponse,
    StudentCreate,
    StudentResponse,
    StudentUpdate,
)
from app.modules.assessment.exceptions import MarksheetModuleLeaderScopeError
from app.modules.assessment.service import (
    AssessmentService,
    CourseEndReportService,
    EnrollmentService,
    MarksheetService,
    MarksService,
    ResultPublicationService,
    StudentService,
    render_end_report_pdf,
    render_marksheet_course_report_pdf,
    render_marksheet_report_pdf,
)
from app.modules.curriculum.models import SectionOffering
from app.modules.curriculum.repository import ModuleLeaderAssignmentRepository

router = APIRouter(tags=["Assessment"])


def _marksheet_scoped_user_id(manifest: PermissionManifestResponse, current_user: User) -> UUID | None:
    """
    Returns None for users with org-wide assessment configuration rights (PC/SA),
    or the acting user's id for section teachers, who are restricted to sections they teach.
    """
    if manifest.is_super_admin or "assessment.configure" in manifest.permissions:
        return None
    return current_user.id


def _result_scoped_user_id(manifest: PermissionManifestResponse, current_user: User) -> UUID | None:
    """
    Returns None for users with org-wide result review rights (PC/SA),
    or the acting user's id for Module Leaders, who are restricted to courses they lead.
    """
    if manifest.is_super_admin or "result.approve.pc" in manifest.permissions or "result.publish" in manifest.permissions:
        return None
    return current_user.id


# ── Public result lookup (no authentication) ──────────────────────────────────

@router.get("/public/student-results", response_model=PublicStudentResults)
async def public_student_results(
    uid: Annotated[str, Query(description="Student ID number")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Public lookup of a student's published CO/PO attainment by their student ID
    number. No authentication required."""
    svc = MarksheetService(db)
    data = await svc.get_public_results_by_uid(uid.strip())
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No student found with that ID. Please check and try again.",
        )
    return data


# ── Students ──────────────────────────────────────────────────────────────────

@router.get("/students/me/results", response_model=list[StudentCourseResult])
async def get_my_results(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Published CO/PO attainment results for the logged-in student.
    Returns an empty list if the user is not linked to a student record."""
    if current_user.linked_student_id is None:
        return []
    svc = MarksheetService(db)
    return await svc.get_results_for_student(
        current_user.linked_student_id, current_user.organization_id
    )


@router.get("/students", response_model=list[StudentResponse])
async def list_students(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    program_id: UUID | None = None,
    batch_id: UUID | None = None,
    search: str | None = None,
):
    svc = StudentService(db)
    return await svc.list_active(current_user.organization_id, program_id, batch_id, search)


@router.post("/students", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    body: StudentCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_any_permission("assessment.configure", "enrollment.manage_own"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = StudentService(db)
    return await svc.create(body, current_user.organization_id)


@router.post("/students/bulk-import", response_model=StudentBulkImportResponse)
async def bulk_import_students(
    body: StudentBulkImportRequest,
    _: Annotated[PermissionManifestResponse, Depends(require_any_permission("assessment.configure", "enrollment.manage_own"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = StudentService(db)
    return await svc.bulk_import(body.students, current_user.organization_id)


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


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.configure"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = StudentService(db)
    await svc.delete(student_id, current_user.organization_id)


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


@router.get("/enrollments/roster", response_model=list[EnrollmentWithStudentResponse])
async def get_enrollment_roster(
    section_offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_any_permission("assessment.read", "marks.read.section"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = EnrollmentService(db)
    rows = await svc.list_roster(section_offering_id, current_user.organization_id)
    return [
        EnrollmentWithStudentResponse(
            id=enrollment.id,
            student_id=student.id,
            student_id_number=student.student_id_number,
            full_name=student.full_name,
            email=student.email,
            status=enrollment.status,
            enrolled_at=enrollment.enrolled_at,
        )
        for enrollment, student in rows
    ]


@router.post("/enrollments", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def create_enrollment(
    body: EnrollmentCreate,
    manifest: Annotated[PermissionManifestResponse, Depends(require_any_permission("assessment.configure", "enrollment.manage_own"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = EnrollmentService(db)
    return await svc.enroll(
        body, current_user.organization_id, acting_user_id=_marksheet_scoped_user_id(manifest, current_user)
    )


@router.post("/enrollments/bulk", response_model=EnrollmentBulkResponse, status_code=status.HTTP_201_CREATED)
async def bulk_enroll(
    body: EnrollmentBulkCreate,
    manifest: Annotated[PermissionManifestResponse, Depends(require_any_permission("assessment.configure", "enrollment.manage_own"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = EnrollmentService(db)
    return await svc.bulk_enroll(
        body, current_user.organization_id, acting_user_id=_marksheet_scoped_user_id(manifest, current_user)
    )


@router.delete("/enrollments/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unenroll_student(
    enrollment_id: UUID,
    manifest: Annotated[PermissionManifestResponse, Depends(require_any_permission("assessment.configure", "enrollment.manage_own"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = EnrollmentService(db)
    await svc.unenroll(
        enrollment_id, current_user.organization_id, acting_user_id=_marksheet_scoped_user_id(manifest, current_user)
    )


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

@router.get("/results", response_model=list[ResultSubmissionListItem])
async def list_result_submissions(
    manifest: Annotated[
        PermissionManifestResponse,
        Depends(require_any_permission("result.approve.ml", "result.approve.pc", "result.publish")),
    ],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    course_id: Annotated[UUID | None, Query()] = None,
):
    svc = ResultPublicationService(db)
    return await svc.list_submissions(
        current_user.organization_id,
        acting_user_id=_result_scoped_user_id(manifest, current_user),
        status=status_filter,
        course_id=course_id,
    )


@router.post("/results/bulk-approve-ml", response_model=BulkApproveMLResponse)
async def bulk_approve_ml(
    body: BulkApproveMLRequest,
    manifest: Annotated[PermissionManifestResponse, Depends(require_permission("result.approve.ml"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ResultPublicationService(db)
    approved_count = await svc.bulk_approve_ml(
        current_user.organization_id,
        body.course_id,
        current_user.id,
        acting_user_id=_result_scoped_user_id(manifest, current_user),
        batch_id=body.batch_id,
        academic_term_id=body.academic_term_id,
    )
    return BulkApproveMLResponse(approved_count=approved_count)


@router.post("/results/bulk-approve-pc", response_model=BulkApprovePCResponse)
async def bulk_approve_pc(
    body: BulkApprovePCRequest,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("result.approve.pc"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ResultPublicationService(db)
    published_count = await svc.bulk_approve_pc(
        current_user.organization_id,
        body.course_id,
        current_user.id,
        batch_id=body.batch_id,
        academic_term_id=body.academic_term_id,
    )
    return BulkApprovePCResponse(published_count=published_count)


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
    manifest: Annotated[PermissionManifestResponse, Depends(require_permission("result.submit"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ResultPublicationService(db)
    return await svc.submit(
        section_offering_id,
        current_user.organization_id,
        current_user.id,
        acting_user_id=_marksheet_scoped_user_id(manifest, current_user),
    )


@router.post("/results/{section_offering_id}/approve-ml", response_model=ResultPublicationResponse)
async def approve_ml(
    section_offering_id: UUID,
    manifest: Annotated[PermissionManifestResponse, Depends(require_permission("result.approve.ml"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ResultPublicationService(db)
    return await svc.approve_ml(
        section_offering_id,
        current_user.organization_id,
        current_user.id,
        acting_user_id=_result_scoped_user_id(manifest, current_user),
    )


@router.post("/results/{section_offering_id}/reject-ml", response_model=ResultPublicationResponse)
async def reject_ml(
    section_offering_id: UUID,
    body: MLRejectRequest,
    manifest: Annotated[PermissionManifestResponse, Depends(require_permission("result.reject.ml"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ResultPublicationService(db)
    return await svc.reject_ml(
        section_offering_id,
        current_user.organization_id,
        current_user.id,
        body.comment,
        acting_user_id=_result_scoped_user_id(manifest, current_user),
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


# ── Marksheets ────────────────────────────────────────────────────────────────

@router.get("/marksheets/{section_offering_id}/questions", response_model=list[MarksheetQuestionResponse])
async def list_marksheet_questions(
    section_offering_id: UUID,
    exam_type: Literal["MID", "FINAL"],
    _: Annotated[PermissionManifestResponse, Depends(require_any_permission("assessment.read", "marks.read.section"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MarksheetService(db)
    return await svc.list_questions(section_offering_id, exam_type, current_user.organization_id)


@router.put("/marksheets/{section_offering_id}/questions", response_model=list[MarksheetQuestionResponse])
async def replace_marksheet_questions(
    section_offering_id: UUID,
    exam_type: Literal["MID", "FINAL"],
    body: MarksheetQuestionsUpdate,
    manifest: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.configure"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # MLs (have assessment.configure but not curriculum.create) may only configure
    # questions for courses they are the assigned Module Leader of.
    is_org_admin = manifest.is_super_admin or "curriculum.create" in manifest.permissions
    if not is_org_admin:
        from sqlalchemy import select
        offering = (await db.execute(
            select(SectionOffering).where(SectionOffering.id == section_offering_id)
        )).scalar_one_or_none()
        if offering is not None:
            ml_repo = ModuleLeaderAssignmentRepository(db)
            assignment = await ml_repo.find_active(
                offering.batch_id, offering.academic_term_id, offering.course_id
            )
            if assignment is None or assignment.user_id != current_user.id:
                raise MarksheetModuleLeaderScopeError()

    svc = MarksheetService(db)
    return await svc.replace_questions(
        section_offering_id,
        exam_type,
        current_user.organization_id,
        body.questions,
        acting_user_id=_marksheet_scoped_user_id(manifest, current_user),
    )


@router.get("/marksheets/{section_offering_id}/grid", response_model=MarksheetGridResponse)
async def get_marksheet_grid(
    section_offering_id: UUID,
    exam_type: Literal["MID", "FINAL"],
    _: Annotated[PermissionManifestResponse, Depends(require_any_permission("assessment.read", "marks.read.section"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MarksheetService(db)
    return await svc.get_grid(section_offering_id, exam_type, current_user.organization_id)


@router.patch("/marksheets/{section_offering_id}/marks", response_model=MarksheetMarkResponse)
async def update_marksheet_mark(
    section_offering_id: UUID,
    body: MarksheetCellUpdate,
    manifest: Annotated[PermissionManifestResponse, Depends(require_any_permission("marks.enter", "marks.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MarksheetService(db)
    return await svc.upsert_mark(
        body,
        current_user.organization_id,
        current_user.id,
        acting_user_id=_marksheet_scoped_user_id(manifest, current_user),
    )


@router.get("/marksheets/{section_offering_id}/attainment", response_model=MarksheetAttainmentResponse)
async def get_marksheet_attainment(
    section_offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_any_permission("assessment.read", "attainment.read", "marks.read.section"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MarksheetService(db)
    return await svc.get_attainment(section_offering_id, current_user.organization_id)


@router.get("/marksheets/{section_offering_id}/grade-distribution")
async def get_grade_distribution(
    section_offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_any_permission("assessment.read", "attainment.read", "marks.read.section"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MarksheetService(db)
    return await svc.get_grade_distribution(section_offering_id, current_user.organization_id)


@router.get("/marksheets/{section_offering_id}/report-pdf")
async def get_marksheet_report_pdf(
    section_offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_any_permission("assessment.read", "marks.read.section"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MarksheetService(db)
    context = await svc.build_report_context(section_offering_id, current_user.organization_id)
    pdf_bytes = await render_marksheet_report_pdf(context)
    filename = f"{context['section']['course_code']}_{context['section']['section_name']}_section_report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/marksheets/course-report-pdf")
async def get_marksheet_course_report_pdf(
    course_id: UUID,
    batch_id: UUID,
    academic_term_id: UUID,
    _: Annotated[
        PermissionManifestResponse,
        Depends(require_any_permission("assessment.read", "result.approve.ml", "result.approve.pc", "result.publish")),
    ],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = MarksheetService(db)
    context = await svc.build_course_report_context(course_id, batch_id, academic_term_id, current_user.organization_id)
    pdf_bytes = await render_marksheet_course_report_pdf(context)
    filename = f"{context['course']['course_code']}_combined_section_report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Course End Reports ────────────────────────────────────────────────────────

@router.get("/end-reports/pending/list")
async def list_pending_end_reports(
    _: Annotated[PermissionManifestResponse, Depends(require_any_permission("result.approve.ml", "result.approve.pc"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseEndReportService(db)
    return await svc.list_pending_for_ml(current_user.organization_id)


@router.get("/end-reports/combined")
async def get_combined_end_report_data(
    course_id: UUID,
    batch_id: UUID,
    academic_term_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_any_permission("result.approve.ml", "result.approve.pc"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseEndReportService(db)
    return await svc.get_combined_data(course_id, batch_id, academic_term_id, current_user.organization_id)


@router.post("/end-reports/combined/pdf")
async def download_combined_end_report_pdf(
    body: CombinedEndReportPdfRequest,
    _: Annotated[PermissionManifestResponse, Depends(require_any_permission("result.approve.ml", "result.approve.pc"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseEndReportService(db)
    context = await svc.build_combined_end_report_context(
        body.course_id,
        body.batch_id,
        body.academic_term_id,
        current_user.organization_id,
        body.ml_feedback,
        [j.model_dump() for j in body.unattained_justifications],
    )
    pdf_bytes = await render_end_report_pdf(context)
    course_code = context["section"]["course_code"]
    filename = f"{course_code}_Combined_End_Report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/end-reports/{section_offering_id}", response_model=CourseEndReportResponse)
async def get_end_report(
    section_offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_any_permission("result.submit", "result.approve.ml"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseEndReportService(db)
    report = await svc.get(section_offering_id)
    if report is None:
        return CourseEndReportResponse(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            organization_id=current_user.organization_id,
            section_offering_id=section_offering_id,
            created_by_user_id=None,
            grade_distribution={},
            co_attainment={},
            unattained_co_explanations=[],
            teacher_feedback=None,
            course_drive_link=None,
            status="DRAFT",
            submitted_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    return report


@router.post("/end-reports/{section_offering_id}/save-draft", response_model=CourseEndReportResponse)
async def save_end_report_draft(
    section_offering_id: UUID,
    body: CourseEndReportSubmit,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("result.submit"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseEndReportService(db)
    return await svc.save_draft(section_offering_id, body, current_user.organization_id, current_user.id)


@router.post("/end-reports/{section_offering_id}/submit", response_model=CourseEndReportResponse)
async def submit_end_report(
    section_offering_id: UUID,
    body: CourseEndReportSubmit,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("result.submit"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseEndReportService(db)
    return await svc.submit(section_offering_id, body, current_user.organization_id, current_user.id)


@router.get("/end-reports/{section_offering_id}/pdf")
async def download_end_report_pdf(
    section_offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_any_permission("result.submit", "result.approve.ml"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseEndReportService(db)
    context = await svc.build_end_report_context(section_offering_id, current_user.organization_id)
    pdf_bytes = await render_end_report_pdf(context)
    course_code = context["section"]["course_code"]
    section_name = context["section"]["section_name"]
    filename = f"{course_code}_Section_{section_name}_End_Report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
