from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.curriculum.domain.prerequisite_graph import PrerequisiteGraphValidator
from app.modules.curriculum.exceptions import (
    AcademicTermConflictError,
    AcademicTermNotFoundError,
    BatchNameConflictError,
    BatchNotFoundError,
    CourseCodeConflictError,
    CourseNotFoundError,
    CurriculumLockedError,
    CurriculumNotFoundError,
    CycleDetectedError,
    FacultyAssignmentConflictError,
    FacultyAssignmentNotFoundError,
    PrerequisiteNotFoundError,
    SectionConflictError,
    SectionNotFoundError,
    SectionOfferingConflictError,
    SectionOfferingNotFoundError,
)
from app.modules.curriculum.models import (
    AcademicTerm,
    Batch,
    Course,
    CoursePrerequisite,
    Curriculum,
    CurriculumCourseSlot,
    CurriculumTermDefinition,
    FacultyAssignment,
    Section,
    SectionOffering,
)
from app.modules.curriculum.repository import (
    AcademicTermRepository,
    BatchRepository,
    CourseRepository,
    CourseSlotRepository,
    CurriculumRepository,
    CurriculumTermRepository,
    FacultyAssignmentRepository,
    PrerequisiteRepository,
    SectionOfferingRepository,
    SectionRepository,
)
from app.modules.curriculum.schemas import (
    AcademicTermCreate,
    AcademicTermUpdate,
    BatchCreate,
    BatchUpdate,
    CourseCreate,
    CourseSlotCreate,
    CourseUpdate,
    CurriculumCreate,
    CurriculumTermDefinitionCreate,
    CurriculumUpdate,
    FacultyAssignmentCreate,
    PrerequisiteCreate,
    SectionCreate,
    SectionOfferingCreate,
    SectionOfferingUpdate,
)

_MODIFIABLE_STATUSES = {"DRAFT", "ACTIVE"}


class CurriculumService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CurriculumRepository(session)

    async def create(self, body: CurriculumCreate, org_id: UUID) -> Curriculum:
        curriculum = Curriculum(
            organization_id=org_id,
            program_id=body.program_id,
            name=body.name,
            code=body.code,
            effective_year=body.effective_year,
            version_number=1,
            status="DRAFT",
        )
        result = await self._repo.create(curriculum)
        await self._session.commit()
        return result

    async def version(self, curriculum_id: UUID, org_id: UUID) -> Curriculum:
        old = await self._repo.get_by_id(curriculum_id, org_id)
        if old is None:
            raise CurriculumNotFoundError()
        if old.status != "ACTIVE":
            raise CurriculumLockedError()

        # Set old to VERSIONED
        old.status = "VERSIONED"
        await self._repo.update(old, {})

        # Create new version
        new_curriculum = Curriculum(
            organization_id=org_id,
            program_id=old.program_id,
            name=old.name,
            code=old.code,
            effective_year=old.effective_year,
            version_number=old.version_number + 1,
            parent_curriculum_id=old.id,
            status="DRAFT",
        )
        result = await self._repo.create(new_curriculum)
        await self._session.commit()
        return result

    async def activate(self, curriculum_id: UUID, org_id: UUID) -> Curriculum:
        curriculum = await self._repo.get_by_id(curriculum_id, org_id)
        if curriculum is None:
            raise CurriculumNotFoundError()
        if curriculum.status != "DRAFT":
            raise CurriculumLockedError()
        curriculum.status = "ACTIVE"
        result = await self._repo.update(curriculum, {})
        await self._session.commit()
        return result

    async def update(
        self, curriculum_id: UUID, body: CurriculumUpdate, org_id: UUID
    ) -> Curriculum:
        curriculum = await self._repo.get_by_id(curriculum_id, org_id)
        if curriculum is None:
            raise CurriculumNotFoundError()
        if curriculum.status not in _MODIFIABLE_STATUSES:
            raise CurriculumLockedError()
        data = body.model_dump(exclude_none=True)
        result = await self._repo.update(curriculum, data)
        await self._session.commit()
        return result

    async def list_active(
        self, org_id: UUID, program_id: UUID | None = None
    ) -> list[Curriculum]:
        return await self._repo.list_active(org_id, program_id)

    async def get(self, curriculum_id: UUID, org_id: UUID) -> Curriculum:
        curriculum = await self._repo.get_by_id(curriculum_id, org_id)
        if curriculum is None:
            raise CurriculumNotFoundError()
        return curriculum


class CurriculumTermService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CurriculumTermRepository(session)
        self._curriculum_repo = CurriculumRepository(session)

    async def create(
        self, body: CurriculumTermDefinitionCreate, org_id: UUID
    ) -> CurriculumTermDefinition:
        curriculum = await self._curriculum_repo.get_by_id(body.curriculum_id, org_id)
        if curriculum is None:
            raise CurriculumNotFoundError()
        if curriculum.status != "DRAFT":
            raise CurriculumLockedError()
        term = CurriculumTermDefinition(
            curriculum_id=body.curriculum_id,
            term_number=body.term_number,
            name=body.name,
            total_credit_hours=body.total_credit_hours,
        )
        result = await self._repo.create(term)
        await self._session.commit()
        return result

    async def list_by_curriculum(
        self, curriculum_id: UUID
    ) -> list[CurriculumTermDefinition]:
        return await self._repo.list_by_curriculum(curriculum_id)


class CourseService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CourseRepository(session)

    async def create(self, body: CourseCreate, org_id: UUID) -> Course:
        existing = await self._repo.find_by_code(body.code, org_id)
        if existing:
            raise CourseCodeConflictError()
        course = Course(
            organization_id=org_id,
            course_type_id=body.course_type_id,
            code=body.code,
            title=body.title,
            credits=body.credits,
            theory_hours=body.theory_hours,
            lab_hours=body.lab_hours,
            description=body.description,
            status="ACTIVE",
        )
        result = await self._repo.create(course)
        await self._session.commit()
        return result

    async def update(
        self, course_id: UUID, body: CourseUpdate, org_id: UUID
    ) -> Course:
        course = await self._repo.get_by_id(course_id, org_id)
        if course is None:
            raise CourseNotFoundError()
        data = body.model_dump(exclude_none=True)
        result = await self._repo.update(course, data)
        await self._session.commit()
        return result

    async def archive(self, course_id: UUID, org_id: UUID) -> Course:
        course = await self._repo.get_by_id(course_id, org_id)
        if course is None:
            raise CourseNotFoundError()
        course.status = "ARCHIVED"
        course.archived_at = datetime.now(timezone.utc)
        result = await self._repo.update(course, {})
        await self._session.commit()
        return result

    async def list_active(self, org_id: UUID) -> list[Course]:
        return await self._repo.list_active(org_id)

    async def get(self, course_id: UUID, org_id: UUID) -> Course:
        course = await self._repo.get_by_id(course_id, org_id)
        if course is None:
            raise CourseNotFoundError()
        return course


class CourseSlotService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CourseSlotRepository(session)
        self._curriculum_repo = CurriculumRepository(session)

    async def add_slot(
        self, body: CourseSlotCreate, org_id: UUID
    ) -> CurriculumCourseSlot:
        curriculum = await self._curriculum_repo.get_by_id(body.curriculum_id, org_id)
        if curriculum is None:
            raise CurriculumNotFoundError()
        if curriculum.status not in _MODIFIABLE_STATUSES:
            raise CurriculumLockedError()
        existing = await self._repo.find_by_curriculum_course(
            body.curriculum_id, body.course_id
        )
        if existing:
            from app.modules.curriculum.exceptions import SectionOfferingConflictError
            raise SectionOfferingConflictError()
        slot = CurriculumCourseSlot(
            curriculum_id=body.curriculum_id,
            curriculum_term_definition_id=body.curriculum_term_definition_id,
            course_id=body.course_id,
            is_elective=body.is_elective,
        )
        result = await self._repo.create(slot)
        await self._session.commit()
        return result

    async def list_by_curriculum(
        self, curriculum_id: UUID
    ) -> list[CurriculumCourseSlot]:
        return await self._repo.list_by_curriculum(curriculum_id)

    async def remove_slot(self, slot_id: UUID, org_id: UUID) -> None:
        slot = await self._repo.get_by_id(slot_id)
        if slot is None:
            from app.modules.curriculum.exceptions import SectionOfferingNotFoundError
            raise SectionOfferingNotFoundError()
        curriculum = await self._curriculum_repo.get_by_id(slot.curriculum_id, org_id)
        if curriculum is None:
            raise CurriculumNotFoundError()
        if curriculum.status != "DRAFT":
            raise CurriculumLockedError()
        await self._repo.delete(slot)
        await self._session.commit()


class PrerequisiteService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PrerequisiteRepository(session)

    async def add(
        self, body: PrerequisiteCreate, org_id: UUID
    ) -> CoursePrerequisite:
        adjacency = await self._repo.get_all_for_org(org_id)
        if PrerequisiteGraphValidator.would_create_cycle(
            adjacency, body.course_id, body.prerequisite_course_id
        ):
            raise CycleDetectedError()
        existing = await self._repo.find_specific(
            body.course_id, body.prerequisite_course_id
        )
        if existing:
            raise PrerequisiteNotFoundError()
        prereq = CoursePrerequisite(
            organization_id=org_id,
            course_id=body.course_id,
            prerequisite_course_id=body.prerequisite_course_id,
        )
        result = await self._repo.create(prereq)
        await self._session.commit()
        return result

    async def list_by_course(
        self, course_id: UUID, org_id: UUID
    ) -> list[CoursePrerequisite]:
        return await self._repo.list_by_course(course_id, org_id)

    async def remove(self, prereq_id: UUID, org_id: UUID) -> None:
        prereq = await self._repo.get_by_id(prereq_id)
        if prereq is None or prereq.organization_id != org_id:
            raise PrerequisiteNotFoundError()
        await self._repo.delete(prereq)
        await self._session.commit()


class BatchService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = BatchRepository(session)

    async def create(self, body: BatchCreate, org_id: UUID) -> Batch:
        existing = await self._repo.find_by_name(body.name, body.curriculum_id)
        if existing:
            raise BatchNameConflictError()
        batch = Batch(
            organization_id=org_id,
            curriculum_id=body.curriculum_id,
            name=body.name,
            intake_year=body.intake_year,
            graduation_year=body.graduation_year,
            status="ACTIVE",
        )
        result = await self._repo.create(batch)
        await self._session.commit()
        return result

    async def update(self, batch_id: UUID, body: BatchUpdate, org_id: UUID) -> Batch:
        batch = await self._repo.get_by_id(batch_id, org_id)
        if batch is None:
            raise BatchNotFoundError()
        data = body.model_dump(exclude_none=True)
        result = await self._repo.update(batch, data)
        await self._session.commit()
        return result

    async def list_active(
        self, org_id: UUID, curriculum_id: UUID | None = None
    ) -> list[Batch]:
        return await self._repo.list_active(org_id, curriculum_id)

    async def get(self, batch_id: UUID, org_id: UUID) -> Batch:
        batch = await self._repo.get_by_id(batch_id, org_id)
        if batch is None:
            raise BatchNotFoundError()
        return batch


class AcademicTermService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AcademicTermRepository(session)

    async def create(self, body: AcademicTermCreate, org_id: UUID) -> AcademicTerm:
        existing = await self._repo.find_by_year_season(body.year, body.season, org_id)
        if existing:
            raise AcademicTermConflictError()
        term = AcademicTerm(
            organization_id=org_id,
            name=body.name,
            year=body.year,
            season=body.season,
            start_date=body.start_date,
            end_date=body.end_date,
            status="UPCOMING",
        )
        result = await self._repo.create(term)
        await self._session.commit()
        return result

    async def update(
        self, term_id: UUID, body: AcademicTermUpdate, org_id: UUID
    ) -> AcademicTerm:
        term = await self._repo.get_by_id(term_id, org_id)
        if term is None:
            raise AcademicTermNotFoundError()
        data = body.model_dump(exclude_none=True)
        result = await self._repo.update(term, data)
        await self._session.commit()
        return result

    async def list_all(self, org_id: UUID) -> list[AcademicTerm]:
        return await self._repo.list_all(org_id)

    async def get(self, term_id: UUID, org_id: UUID) -> AcademicTerm:
        term = await self._repo.get_by_id(term_id, org_id)
        if term is None:
            raise AcademicTermNotFoundError()
        return term


class SectionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SectionRepository(session)

    async def create(self, body: SectionCreate, org_id: UUID) -> Section:
        existing = await self._repo.find_by_name(body.name, org_id)
        if existing:
            raise SectionConflictError()
        section = Section(
            organization_id=org_id,
            name=body.name,
            capacity=body.capacity,
        )
        result = await self._repo.create(section)
        await self._session.commit()
        return result

    async def list_all(self, org_id: UUID) -> list[Section]:
        return await self._repo.list_all(org_id)


class SectionOfferingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SectionOfferingRepository(session)

    async def create(self, body: SectionOfferingCreate, org_id: UUID) -> SectionOffering:
        existing = await self._repo.find_duplicate(
            body.batch_id, body.course_id, body.academic_term_id, body.section_id
        )
        if existing:
            raise SectionOfferingConflictError()
        offering = SectionOffering(
            organization_id=org_id,
            curriculum_id=body.curriculum_id,
            batch_id=body.batch_id,
            course_id=body.course_id,
            academic_term_id=body.academic_term_id,
            section_id=body.section_id,
            status="UPCOMING",
        )
        result = await self._repo.create(offering)
        await self._session.commit()
        return result

    async def update(
        self, offering_id: UUID, body: SectionOfferingUpdate, org_id: UUID
    ) -> SectionOffering:
        offering = await self._repo.get_by_id(offering_id, org_id)
        if offering is None:
            raise SectionOfferingNotFoundError()
        data = body.model_dump(exclude_none=True)
        result = await self._repo.update(offering, data)
        await self._session.commit()
        return result

    async def list_all(
        self,
        org_id: UUID,
        academic_term_id: UUID | None = None,
        batch_id: UUID | None = None,
    ) -> list[SectionOffering]:
        return await self._repo.list_all(org_id, academic_term_id, batch_id)

    async def get(self, offering_id: UUID, org_id: UUID) -> SectionOffering:
        offering = await self._repo.get_by_id(offering_id, org_id)
        if offering is None:
            raise SectionOfferingNotFoundError()
        return offering


class FacultyAssignmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = FacultyAssignmentRepository(session)

    async def assign(
        self, body: FacultyAssignmentCreate, org_id: UUID
    ) -> FacultyAssignment:
        existing = await self._repo.find_active(
            body.section_offering_id, body.user_id, body.role_in_course
        )
        if existing:
            raise FacultyAssignmentConflictError()
        assignment = FacultyAssignment(
            section_offering_id=body.section_offering_id,
            user_id=body.user_id,
            role_in_course=body.role_in_course,
        )
        result = await self._repo.create(assignment)
        await self._session.commit()
        return result

    async def remove(self, assignment_id: UUID, org_id: UUID) -> FacultyAssignment:
        assignment = await self._repo.get_by_id(assignment_id)
        if assignment is None:
            raise FacultyAssignmentNotFoundError()
        result = await self._repo.remove(assignment)
        await self._session.commit()
        return result

    async def list_active_by_offering(
        self, offering_id: UUID
    ) -> list[FacultyAssignment]:
        return await self._repo.list_active_by_offering(offering_id)
