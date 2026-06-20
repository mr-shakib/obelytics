from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_any_permission, require_permission
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.curriculum.schemas import (
    AddSectionOfferingBody,
    AcademicTermCreate,
    AcademicTermResponse,
    AcademicTermUpdate,
    BatchCreate,
    BatchResponse,
    BatchSemesterPlanItem,
    BatchTermCalendarEntry,
    BatchTermOfferingCourse,
    BatchUpdate,
    CourseAssessmentToolResponse,
    CourseAssessmentToolsUpdate,
    CourseBloomDomainsUpdate,
    CourseBloomMarkResponse,
    CourseBloomMarksUpdate,
    CourseBulkImportRequest,
    CourseBulkImportResponse,
    CourseCOMarkResponse,
    CourseCOMarksUpdate,
    CourseCreate,
    CourseLearningMaterialResponse,
    CourseLearningMaterialsUpdate,
    CourseObjectiveResponse,
    CourseObjectivesUpdate,
    CourseResponse,
    CourseSlotCreate,
    CourseSlotResponse,
    CourseUpdate,
    CurriculumCreate,
    CurriculumResponse,
    CurriculumTermDefinitionCreate,
    CurriculumTermDefinitionResponse,
    CurriculumUpdate,
    FacultyAssignmentCreate,
    FacultyAssignmentResponse,
    LessonPlanItemResponse,
    LessonPlanItemsUpdate,
    ModuleLeaderAssignmentCreate,
    ModuleLeaderAssignmentResponse,
    MySectionResponse,
    PrerequisiteCreate,
    PrerequisiteResponse,
    SectionCreate,
    SectionOfferingCreate,
    SectionOfferingDependents,
    SectionOfferingResponse,
    SectionOfferingUpdate,
    SectionResponse,
)
from app.modules.curriculum.service import (
    AcademicTermService,
    BatchService,
    CourseAssessmentPatternService,
    CourseAssessmentToolService,
    CourseBloomDomainService,
    CourseBloomMarksService,
    CourseLearningMaterialService,
    CourseLessonPlanService,
    CourseObjectiveService,
    CourseService,
    CourseSlotService,
    CurriculumService,
    CurriculumTermService,
    FacultyAssignmentService,
    ModuleLeaderAssignmentService,
    PrerequisiteService,
    SectionOfferingService,
    SectionService,
)
from app.modules.curriculum.outline_service import CourseOutlineService, render_course_outline_pdf

router = APIRouter(tags=["Curriculum"])


def _scoped_user_id(manifest: PermissionManifestResponse, current_user: User) -> UUID | None:
    """
    Returns None for users with org-wide section/faculty management rights (PC/SA),
    or the acting user's id for module leaders, who are restricted to courses they lead.
    """
    if manifest.is_super_admin or "batch.create" in manifest.permissions:
        return None
    return current_user.id


# ── Curricula ─────────────────────────────────────────────────────────────────

@router.get("/curricula", response_model=list[CurriculumResponse])
async def list_curricula(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    program_id: UUID | None = None,
):
    svc = CurriculumService(db)
    return await svc.list_active(current_user.organization_id, program_id)


@router.post("/curricula", response_model=CurriculumResponse, status_code=status.HTTP_201_CREATED)
async def create_curriculum(
    body: CurriculumCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CurriculumService(db)
    return await svc.create(body, current_user.organization_id)


@router.get("/curricula/{curriculum_id}", response_model=CurriculumResponse)
async def get_curriculum(
    curriculum_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CurriculumService(db)
    return await svc.get(curriculum_id, current_user.organization_id)


@router.patch("/curricula/{curriculum_id}", response_model=CurriculumResponse)
async def update_curriculum(
    curriculum_id: UUID,
    body: CurriculumUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CurriculumService(db)
    return await svc.update(curriculum_id, body, current_user.organization_id)


@router.post("/curricula/{curriculum_id}/archive", response_model=CurriculumResponse)
async def archive_curriculum(
    curriculum_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CurriculumService(db)
    return await svc.archive(curriculum_id, current_user.organization_id)


@router.post("/curricula/{curriculum_id}/version", response_model=CurriculumResponse, status_code=status.HTTP_201_CREATED)
async def version_curriculum(
    curriculum_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.version"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CurriculumService(db)
    return await svc.version(curriculum_id, current_user.organization_id)


@router.post("/curricula/{curriculum_id}/activate", response_model=CurriculumResponse)
async def activate_curriculum(
    curriculum_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CurriculumService(db)
    return await svc.activate(curriculum_id, current_user.organization_id)


@router.post(
    "/curricula/{curriculum_id}/terms",
    response_model=list[CurriculumTermDefinitionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_curriculum_terms(
    curriculum_id: UUID,
    body: list[CurriculumTermDefinitionCreate],
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CurriculumTermService(db)
    results = []
    for term_body in body:
        # Ensure curriculum_id from path is used
        term_body_with_id = term_body.model_copy(update={"curriculum_id": curriculum_id})
        results.append(await svc.create(term_body_with_id, current_user.organization_id))
    return results


@router.get("/curricula/{curriculum_id}/terms", response_model=list[CurriculumTermDefinitionResponse])
async def list_curriculum_terms(
    curriculum_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CurriculumTermService(db)
    return await svc.list_by_curriculum(curriculum_id)


# ── Courses ───────────────────────────────────────────────────────────────────

@router.get("/courses", response_model=list[CourseResponse])
async def list_courses(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseService(db)
    return await svc.list_active(current_user.organization_id)


@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    body: CourseCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("course.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseService(db)
    return await svc.create(body, current_user.organization_id)


@router.post("/courses/bulk-import", response_model=CourseBulkImportResponse)
async def bulk_import_courses(
    body: CourseBulkImportRequest,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("course.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseService(db)
    return await svc.bulk_import(body.courses, current_user.organization_id)


@router.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseService(db)
    return await svc.get(course_id, current_user.organization_id)


@router.patch("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: UUID,
    body: CourseUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("course.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseService(db)
    return await svc.update(course_id, body, current_user.organization_id)


@router.post("/courses/{course_id}/archive", response_model=CourseResponse)
async def archive_course(
    course_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("course.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseService(db)
    return await svc.archive(course_id, current_user.organization_id)


@router.get("/courses/{course_id}/bloom-domains", response_model=list[UUID])
async def list_course_bloom_domains(
    course_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseBloomDomainService(db)
    return await svc.list_for_course(course_id, current_user.organization_id)


@router.put("/courses/{course_id}/bloom-domains", response_model=list[UUID])
async def set_course_bloom_domains(
    course_id: UUID,
    body: CourseBloomDomainsUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("course.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseBloomDomainService(db)
    return await svc.set_for_course(course_id, body, current_user.organization_id)


@router.get("/courses/{course_id}/objectives", response_model=list[CourseObjectiveResponse])
async def list_course_objectives(
    course_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseObjectiveService(db)
    return await svc.list_for_course(course_id, current_user.organization_id)


@router.put("/courses/{course_id}/objectives", response_model=list[CourseObjectiveResponse])
async def set_course_objectives(
    course_id: UUID,
    body: CourseObjectivesUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("course.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseObjectiveService(db)
    return await svc.set_for_course(course_id, body, current_user.organization_id)


@router.get("/courses/{course_id}/learning-materials", response_model=list[CourseLearningMaterialResponse])
async def list_course_learning_materials(
    course_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseLearningMaterialService(db)
    return await svc.list_for_course(course_id, current_user.organization_id)


@router.put("/courses/{course_id}/learning-materials", response_model=list[CourseLearningMaterialResponse])
async def set_course_learning_materials(
    course_id: UUID,
    body: CourseLearningMaterialsUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("course.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseLearningMaterialService(db)
    return await svc.set_for_course(course_id, body, current_user.organization_id)


@router.get("/courses/{course_id}/lesson-plan", response_model=list[LessonPlanItemResponse])
async def list_course_lesson_plan(
    course_id: UUID,
    curriculum_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseLessonPlanService(db)
    return await svc.list_for_course(course_id, curriculum_id, current_user.organization_id)


@router.put("/courses/{course_id}/lesson-plan", response_model=list[LessonPlanItemResponse])
async def set_course_lesson_plan(
    course_id: UUID,
    curriculum_id: UUID,
    body: LessonPlanItemsUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("course.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseLessonPlanService(db)
    return await svc.set_for_course(course_id, curriculum_id, body, current_user.organization_id)


@router.get("/courses/{course_id}/assessment-tools", response_model=list[CourseAssessmentToolResponse])
async def list_course_assessment_tools(
    course_id: UUID,
    curriculum_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseAssessmentToolService(db)
    return await svc.list_for_course(course_id, curriculum_id, current_user.organization_id)


@router.put("/courses/{course_id}/assessment-tools", response_model=list[CourseAssessmentToolResponse])
async def set_course_assessment_tools(
    course_id: UUID,
    curriculum_id: UUID,
    body: CourseAssessmentToolsUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("course.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseAssessmentToolService(db)
    return await svc.set_tools(course_id, curriculum_id, body, current_user.organization_id)


@router.get("/courses/{course_id}/assessment-pattern", response_model=list[CourseCOMarkResponse])
async def list_course_assessment_pattern(
    course_id: UUID,
    curriculum_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseAssessmentPatternService(db)
    return await svc.list_for_course(course_id, curriculum_id, current_user.organization_id)


@router.put("/courses/{course_id}/assessment-pattern", response_model=list[CourseCOMarkResponse])
async def set_course_assessment_pattern(
    course_id: UUID,
    curriculum_id: UUID,
    body: CourseCOMarksUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("course.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseAssessmentPatternService(db)
    return await svc.set_for_course(course_id, curriculum_id, body, current_user.organization_id)


@router.get("/courses/{course_id}/outline-pdf")
async def get_course_outline_pdf(
    course_id: UUID,
    curriculum_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    excluded_tool_ids: Annotated[list[UUID], Query()] = [],
):
    svc = CourseOutlineService(db)
    context = await svc.build_context(
        course_id, curriculum_id, current_user.organization_id,
        excluded_tool_ids=excluded_tool_ids or [],
    )
    pdf_bytes = render_course_outline_pdf(context)
    filename = f"{context['course']['code']}_course_outline.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/courses/{course_id}/bloom-marks", response_model=list[CourseBloomMarkResponse])
async def list_course_bloom_marks(
    course_id: UUID,
    curriculum_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseBloomMarksService(db)
    return await svc.list_for_course(course_id, curriculum_id, current_user.organization_id)


@router.put("/courses/{course_id}/bloom-marks", response_model=list[CourseBloomMarkResponse])
async def set_course_bloom_marks(
    course_id: UUID,
    curriculum_id: UUID,
    body: CourseBloomMarksUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("course.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseBloomMarksService(db)
    return await svc.set_for_course(course_id, curriculum_id, body, current_user.organization_id)


@router.get("/courses/{course_id}/prerequisites", response_model=list[PrerequisiteResponse])
async def list_prerequisites(
    course_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = PrerequisiteService(db)
    return await svc.list_by_course(course_id, current_user.organization_id)


@router.post(
    "/courses/{course_id}/prerequisites",
    response_model=PrerequisiteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_prerequisite(
    course_id: UUID,
    body: PrerequisiteCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("course.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = PrerequisiteService(db)
    # Override course_id from path
    body_with_id = body.model_copy(update={"course_id": course_id})
    return await svc.add(body_with_id, current_user.organization_id)


@router.delete(
    "/courses/{course_id}/prerequisites/{prereq_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_prerequisite(
    course_id: UUID,
    prereq_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("course.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = PrerequisiteService(db)
    await svc.remove(prereq_id, current_user.organization_id)


# ── Course Slots ──────────────────────────────────────────────────────────────

@router.get("/curricula/{curriculum_id}/course-slots", response_model=list[CourseSlotResponse])
async def list_course_slots(
    curriculum_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseSlotService(db)
    return await svc.list_by_curriculum(curriculum_id)


@router.post(
    "/curricula/{curriculum_id}/course-slots",
    response_model=CourseSlotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_course_slot(
    curriculum_id: UUID,
    body: CourseSlotCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseSlotService(db)
    body_with_id = body.model_copy(update={"curriculum_id": curriculum_id})
    return await svc.add_slot(body_with_id, current_user.organization_id)


@router.delete(
    "/curricula/{curriculum_id}/course-slots/{slot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_course_slot(
    curriculum_id: UUID,
    slot_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = CourseSlotService(db)
    await svc.remove_slot(slot_id, current_user.organization_id)


# ── Batches ───────────────────────────────────────────────────────────────────

async def _batch_response(batch, db: AsyncSession) -> BatchResponse:
    svc = BatchService(db)
    calendar_rows = await svc.get_term_calendar(batch.id, batch.organization_id)
    response = BatchResponse.model_validate(batch)
    response.term_calendar = [
        BatchTermCalendarEntry(
            term_number=num,
            academic_term_id=term.id,
            name=term.name,
            year=term.year,
            season=term.season,
            start_date=term.start_date,
            end_date=term.end_date,
            status=term.status,
        )
        for num, term in calendar_rows
    ]
    return response


@router.get("/batches", response_model=list[BatchResponse])
async def list_batches(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    curriculum_id: UUID | None = None,
):
    svc = BatchService(db)
    batches = await svc.list_active(current_user.organization_id, curriculum_id)
    return [await _batch_response(b, db) for b in batches]


@router.post("/batches", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    body: BatchCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("batch.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = BatchService(db)
    batch = await svc.create(body, current_user.organization_id)
    return await _batch_response(batch, db)


@router.get("/batches/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = BatchService(db)
    batch = await svc.get(batch_id, current_user.organization_id)
    return await _batch_response(batch, db)


@router.get("/batches/{batch_id}/terms", response_model=list[BatchTermCalendarEntry])
async def get_batch_terms(
    batch_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = BatchService(db)
    batch = await svc.get(batch_id, current_user.organization_id)
    rows = await svc.get_term_calendar(batch.id, batch.organization_id)
    return [
        BatchTermCalendarEntry(
            term_number=num,
            academic_term_id=term.id,
            name=term.name,
            year=term.year,
            season=term.season,
            start_date=term.start_date,
            end_date=term.end_date,
            status=term.status,
        )
        for num, term in rows
    ]


@router.get("/batches/{batch_id}/semester-plan", response_model=list[BatchSemesterPlanItem])
async def get_batch_semester_plan(
    batch_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = BatchService(db)
    return await svc.get_semester_plan(batch_id, current_user.organization_id)


@router.get("/batches/{batch_id}/terms/{academic_term_id}/offerings", response_model=list[BatchTermOfferingCourse])
async def get_batch_term_offerings(
    batch_id: UUID,
    academic_term_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = BatchService(db)
    return await svc.get_batch_term_offerings(batch_id, academic_term_id, current_user.organization_id)


@router.post(
    "/batches/{batch_id}/terms/{academic_term_id}/offerings",
    response_model=SectionOfferingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_batch_term_offering(
    batch_id: UUID,
    academic_term_id: UUID,
    body: AddSectionOfferingBody,
    manifest: Annotated[PermissionManifestResponse, Depends(require_any_permission("section_offering.create", "section_offering.manage_own"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = BatchService(db)
    return await svc.add_section_offering(
        batch_id, academic_term_id, body.course_id, body.section_name, current_user.organization_id,
        acting_user_id=_scoped_user_id(manifest, current_user),
    )


@router.get(
    "/section-offerings/{offering_id}/dependents",
    response_model=SectionOfferingDependents,
)
async def get_section_offering_dependents(
    offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_any_permission("section_offering.create", "section_offering.manage_own"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = SectionOfferingService(db)
    counts = await svc.get_dependents(offering_id, current_user.organization_id)
    return SectionOfferingDependents(**counts)


@router.delete("/section-offerings/{offering_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section_offering(
    offering_id: UUID,
    manifest: Annotated[PermissionManifestResponse, Depends(require_any_permission("section_offering.create", "section_offering.manage_own"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    cascade: Annotated[bool, Query(description="Delete dependent records (enrollments, marks, results, reports) along with the section")] = False,
):
    svc = SectionOfferingService(db)
    await svc.delete(
        offering_id,
        current_user.organization_id,
        acting_user_id=_scoped_user_id(manifest, current_user),
        cascade=cascade,
    )


@router.patch("/batches/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: UUID,
    body: BatchUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("batch.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = BatchService(db)
    batch = await svc.update(batch_id, body, current_user.organization_id)
    return await _batch_response(batch, db)


# ── Academic Terms ────────────────────────────────────────────────────────────

@router.get("/academic-terms", response_model=list[AcademicTermResponse])
async def list_academic_terms(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AcademicTermService(db)
    return await svc.list_all(current_user.organization_id)


@router.post("/academic-terms", response_model=AcademicTermResponse, status_code=status.HTTP_201_CREATED)
async def create_academic_term(
    body: AcademicTermCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AcademicTermService(db)
    return await svc.create(body, current_user.organization_id)


@router.get("/academic-terms/{term_id}", response_model=AcademicTermResponse)
async def get_academic_term(
    term_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AcademicTermService(db)
    return await svc.get(term_id, current_user.organization_id)


@router.patch("/academic-terms/{term_id}", response_model=AcademicTermResponse)
async def update_academic_term(
    term_id: UUID,
    body: AcademicTermUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.update"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = AcademicTermService(db)
    return await svc.update(term_id, body, current_user.organization_id)


# ── Sections ──────────────────────────────────────────────────────────────────

@router.get("/sections", response_model=list[SectionResponse])
async def list_sections(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = SectionService(db)
    return await svc.list_all(current_user.organization_id)


@router.post("/sections", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
async def create_section(
    body: SectionCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = SectionService(db)
    return await svc.create(body, current_user.organization_id)


# ── Section Offerings ─────────────────────────────────────────────────────────

@router.get("/section-offerings", response_model=list[SectionOfferingResponse])
async def list_section_offerings(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    course_id: UUID | None = None,
    academic_term_id: UUID | None = None,
    batch_id: UUID | None = None,
):
    svc = SectionOfferingService(db)
    return await svc.list_all(current_user.organization_id, course_id, academic_term_id, batch_id)


@router.post(
    "/section-offerings",
    response_model=SectionOfferingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_section_offering(
    body: SectionOfferingCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("section_offering.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = SectionOfferingService(db)
    return await svc.create(body, current_user.organization_id)


@router.get("/section-offerings/{offering_id}", response_model=SectionOfferingResponse)
async def get_section_offering(
    offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = SectionOfferingService(db)
    return await svc.get(offering_id, current_user.organization_id)


@router.patch("/section-offerings/{offering_id}", response_model=SectionOfferingResponse)
async def update_section_offering(
    offering_id: UUID,
    body: SectionOfferingUpdate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("section_offering.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = SectionOfferingService(db)
    return await svc.update(offering_id, body, current_user.organization_id)


# ── Faculty Assignments ───────────────────────────────────────────────────────

@router.get("/faculty-assignments", response_model=list[FacultyAssignmentResponse])
async def list_faculty_assignments(
    offering_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = FacultyAssignmentService(db)
    return await svc.list_active_by_offering(offering_id)


@router.post(
    "/faculty-assignments",
    response_model=FacultyAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_faculty(
    body: FacultyAssignmentCreate,
    manifest: Annotated[PermissionManifestResponse, Depends(require_any_permission("faculty_assignment.create", "faculty_assignment.section_teacher"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = FacultyAssignmentService(db)
    return await svc.assign(body, current_user.organization_id, acting_user_id=_scoped_user_id(manifest, current_user))


@router.delete("/faculty-assignments/{assignment_id}", status_code=status.HTTP_200_OK, response_model=FacultyAssignmentResponse)
async def remove_faculty_assignment(
    assignment_id: UUID,
    manifest: Annotated[PermissionManifestResponse, Depends(require_any_permission("faculty_assignment.create", "faculty_assignment.section_teacher"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = FacultyAssignmentService(db)
    return await svc.remove(assignment_id, current_user.organization_id, acting_user_id=_scoped_user_id(manifest, current_user))


@router.get("/faculty-assignments/my-sections", response_model=list[MySectionResponse])
async def list_my_sections(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("assessment.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = FacultyAssignmentService(db)
    return await svc.list_my_sections(current_user.organization_id, current_user.id)


# ── Module Leader Assignments ────────────────────────────────────────────────

@router.get("/module-leader-assignments/mine", response_model=list[ModuleLeaderAssignmentResponse])
async def list_my_module_leader_assignments(
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ModuleLeaderAssignmentService(db)
    return await svc.list_mine(current_user.organization_id, current_user.id)


@router.get("/module-leader-assignments", response_model=list[ModuleLeaderAssignmentResponse])
async def list_module_leader_assignments(
    batch_id: UUID,
    academic_term_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("curriculum.read"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ModuleLeaderAssignmentService(db)
    return await svc.list_active(current_user.organization_id, batch_id, academic_term_id)


@router.post(
    "/module-leader-assignments",
    response_model=ModuleLeaderAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_module_leader(
    body: ModuleLeaderAssignmentCreate,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("faculty_assignment.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ModuleLeaderAssignmentService(db)
    return await svc.assign(body, current_user.organization_id)


@router.delete(
    "/module-leader-assignments/{assignment_id}",
    status_code=status.HTTP_200_OK,
    response_model=ModuleLeaderAssignmentResponse,
)
async def remove_module_leader_assignment(
    assignment_id: UUID,
    _: Annotated[PermissionManifestResponse, Depends(require_permission("faculty_assignment.create"))],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    svc = ModuleLeaderAssignmentService(db)
    return await svc.remove(assignment_id, current_user.organization_id)
