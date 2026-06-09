from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

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


class CurriculumRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, curriculum_id: UUID, org_id: UUID) -> Curriculum | None:
        result = await self._session.execute(
            select(Curriculum).where(
                and_(Curriculum.id == curriculum_id, Curriculum.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_active(self, org_id: UUID, program_id: UUID | None = None) -> list[Curriculum]:
        stmt = select(Curriculum).where(
            and_(
                Curriculum.organization_id == org_id,
                Curriculum.status.in_(["DRAFT", "ACTIVE"]),
            )
        )
        if program_id:
            stmt = stmt.where(Curriculum.program_id == program_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_code(
        self, code: str, program_id: UUID, version: int
    ) -> Curriculum | None:
        result = await self._session.execute(
            select(Curriculum).where(
                and_(
                    Curriculum.code == code,
                    Curriculum.program_id == program_id,
                    Curriculum.version_number == version,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, curriculum: Curriculum) -> Curriculum:
        self._session.add(curriculum)
        await self._session.flush()
        await self._session.refresh(curriculum)
        return curriculum

    async def update(self, curriculum: Curriculum, data: dict) -> Curriculum:
        for key, value in data.items():
            if value is not None:
                setattr(curriculum, key, value)
        self._session.add(curriculum)
        await self._session.flush()
        await self._session.refresh(curriculum)
        return curriculum


class CurriculumTermRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_curriculum(self, curriculum_id: UUID) -> list[CurriculumTermDefinition]:
        result = await self._session.execute(
            select(CurriculumTermDefinition)
            .where(CurriculumTermDefinition.curriculum_id == curriculum_id)
            .order_by(CurriculumTermDefinition.term_number)
        )
        return list(result.scalars().all())

    async def get_by_id(
        self, term_id: UUID, curriculum_id: UUID
    ) -> CurriculumTermDefinition | None:
        result = await self._session.execute(
            select(CurriculumTermDefinition).where(
                and_(
                    CurriculumTermDefinition.id == term_id,
                    CurriculumTermDefinition.curriculum_id == curriculum_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, term: CurriculumTermDefinition) -> CurriculumTermDefinition:
        self._session.add(term)
        await self._session.flush()
        await self._session.refresh(term)
        return term


class CourseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, course_id: UUID, org_id: UUID) -> Course | None:
        result = await self._session.execute(
            select(Course).where(
                and_(Course.id == course_id, Course.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_active(self, org_id: UUID) -> list[Course]:
        result = await self._session.execute(
            select(Course).where(
                and_(Course.organization_id == org_id, Course.status == "ACTIVE")
            )
        )
        return list(result.scalars().all())

    async def find_by_code(self, code: str, org_id: UUID) -> Course | None:
        result = await self._session.execute(
            select(Course).where(
                and_(
                    Course.code == code,
                    Course.organization_id == org_id,
                    Course.status == "ACTIVE",
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, course: Course) -> Course:
        self._session.add(course)
        await self._session.flush()
        await self._session.refresh(course)
        return course

    async def update(self, course: Course, data: dict) -> Course:
        for key, value in data.items():
            if value is not None:
                setattr(course, key, value)
        self._session.add(course)
        await self._session.flush()
        await self._session.refresh(course)
        return course


class CourseSlotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_curriculum(self, curriculum_id: UUID) -> list[CurriculumCourseSlot]:
        result = await self._session.execute(
            select(CurriculumCourseSlot).where(
                CurriculumCourseSlot.curriculum_id == curriculum_id
            )
        )
        return list(result.scalars().all())

    async def get_by_id(self, slot_id: UUID) -> CurriculumCourseSlot | None:
        result = await self._session.execute(
            select(CurriculumCourseSlot).where(CurriculumCourseSlot.id == slot_id)
        )
        return result.scalar_one_or_none()

    async def find_by_curriculum_course(
        self, curriculum_id: UUID, course_id: UUID
    ) -> CurriculumCourseSlot | None:
        result = await self._session.execute(
            select(CurriculumCourseSlot).where(
                and_(
                    CurriculumCourseSlot.curriculum_id == curriculum_id,
                    CurriculumCourseSlot.course_id == course_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, slot: CurriculumCourseSlot) -> CurriculumCourseSlot:
        self._session.add(slot)
        await self._session.flush()
        await self._session.refresh(slot)
        return slot

    async def delete(self, slot: CurriculumCourseSlot) -> None:
        await self._session.delete(slot)
        await self._session.flush()


class PrerequisiteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_course(self, course_id: UUID, org_id: UUID) -> list[CoursePrerequisite]:
        result = await self._session.execute(
            select(CoursePrerequisite).where(
                and_(
                    CoursePrerequisite.course_id == course_id,
                    CoursePrerequisite.organization_id == org_id,
                )
            )
        )
        return list(result.scalars().all())

    async def get_by_id(self, prereq_id: UUID) -> CoursePrerequisite | None:
        result = await self._session.execute(
            select(CoursePrerequisite).where(CoursePrerequisite.id == prereq_id)
        )
        return result.scalar_one_or_none()

    async def find_specific(
        self, course_id: UUID, prereq_id: UUID
    ) -> CoursePrerequisite | None:
        result = await self._session.execute(
            select(CoursePrerequisite).where(
                and_(
                    CoursePrerequisite.course_id == course_id,
                    CoursePrerequisite.prerequisite_course_id == prereq_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_all_for_org(self, org_id: UUID) -> dict[UUID, list[UUID]]:
        """Returns adjacency dict: course_id → [prerequisite_course_ids]."""
        result = await self._session.execute(
            select(CoursePrerequisite).where(CoursePrerequisite.organization_id == org_id)
        )
        rows = result.scalars().all()
        adjacency: dict[UUID, list[UUID]] = {}
        for row in rows:
            adjacency.setdefault(row.course_id, []).append(row.prerequisite_course_id)
        return adjacency

    async def create(self, prereq: CoursePrerequisite) -> CoursePrerequisite:
        self._session.add(prereq)
        await self._session.flush()
        await self._session.refresh(prereq)
        return prereq

    async def delete(self, prereq: CoursePrerequisite) -> None:
        await self._session.delete(prereq)
        await self._session.flush()


class BatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, batch_id: UUID, org_id: UUID) -> Batch | None:
        result = await self._session.execute(
            select(Batch).where(
                and_(Batch.id == batch_id, Batch.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_active(
        self, org_id: UUID, curriculum_id: UUID | None = None
    ) -> list[Batch]:
        stmt = select(Batch).where(
            and_(Batch.organization_id == org_id, Batch.status == "ACTIVE")
        )
        if curriculum_id:
            stmt = stmt.where(Batch.curriculum_id == curriculum_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_name(self, name: str, curriculum_id: UUID) -> Batch | None:
        result = await self._session.execute(
            select(Batch).where(
                and_(Batch.name == name, Batch.curriculum_id == curriculum_id)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, batch: Batch) -> Batch:
        self._session.add(batch)
        await self._session.flush()
        await self._session.refresh(batch)
        return batch

    async def update(self, batch: Batch, data: dict) -> Batch:
        for key, value in data.items():
            if value is not None:
                setattr(batch, key, value)
        self._session.add(batch)
        await self._session.flush()
        await self._session.refresh(batch)
        return batch


class AcademicTermRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, term_id: UUID, org_id: UUID) -> AcademicTerm | None:
        result = await self._session.execute(
            select(AcademicTerm).where(
                and_(AcademicTerm.id == term_id, AcademicTerm.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_all(self, org_id: UUID) -> list[AcademicTerm]:
        result = await self._session.execute(
            select(AcademicTerm).where(AcademicTerm.organization_id == org_id)
        )
        return list(result.scalars().all())

    async def find_by_year_season(
        self, year: int, season: str, org_id: UUID
    ) -> AcademicTerm | None:
        result = await self._session.execute(
            select(AcademicTerm).where(
                and_(
                    AcademicTerm.year == year,
                    AcademicTerm.season == season,
                    AcademicTerm.organization_id == org_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, term: AcademicTerm) -> AcademicTerm:
        self._session.add(term)
        await self._session.flush()
        await self._session.refresh(term)
        return term

    async def update(self, term: AcademicTerm, data: dict) -> AcademicTerm:
        for key, value in data.items():
            if value is not None:
                setattr(term, key, value)
        self._session.add(term)
        await self._session.flush()
        await self._session.refresh(term)
        return term


class SectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, section_id: UUID, org_id: UUID) -> Section | None:
        result = await self._session.execute(
            select(Section).where(
                and_(Section.id == section_id, Section.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_all(self, org_id: UUID) -> list[Section]:
        result = await self._session.execute(
            select(Section).where(Section.organization_id == org_id)
        )
        return list(result.scalars().all())

    async def find_by_name(self, name: str, org_id: UUID) -> Section | None:
        result = await self._session.execute(
            select(Section).where(
                and_(Section.name == name, Section.organization_id == org_id)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, section: Section) -> Section:
        self._session.add(section)
        await self._session.flush()
        await self._session.refresh(section)
        return section


class SectionOfferingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, offering_id: UUID, org_id: UUID) -> SectionOffering | None:
        result = await self._session.execute(
            select(SectionOffering).where(
                and_(
                    SectionOffering.id == offering_id,
                    SectionOffering.organization_id == org_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        org_id: UUID,
        academic_term_id: UUID | None = None,
        batch_id: UUID | None = None,
    ) -> list[SectionOffering]:
        stmt = select(SectionOffering).where(SectionOffering.organization_id == org_id)
        if academic_term_id:
            stmt = stmt.where(SectionOffering.academic_term_id == academic_term_id)
        if batch_id:
            stmt = stmt.where(SectionOffering.batch_id == batch_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_duplicate(
        self,
        batch_id: UUID,
        course_id: UUID,
        term_id: UUID,
        section_id: UUID,
    ) -> SectionOffering | None:
        result = await self._session.execute(
            select(SectionOffering).where(
                and_(
                    SectionOffering.batch_id == batch_id,
                    SectionOffering.course_id == course_id,
                    SectionOffering.academic_term_id == term_id,
                    SectionOffering.section_id == section_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, offering: SectionOffering) -> SectionOffering:
        self._session.add(offering)
        await self._session.flush()
        await self._session.refresh(offering)
        return offering

    async def update(self, offering: SectionOffering, data: dict) -> SectionOffering:
        for key, value in data.items():
            if value is not None:
                setattr(offering, key, value)
        self._session.add(offering)
        await self._session.flush()
        await self._session.refresh(offering)
        return offering

    async def delete(self, offering: SectionOffering) -> None:
        await self._session.delete(offering)
        await self._session.flush()


class FacultyAssignmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_by_offering(
        self, offering_id: UUID
    ) -> list[FacultyAssignment]:
        result = await self._session.execute(
            select(FacultyAssignment).where(
                and_(
                    FacultyAssignment.section_offering_id == offering_id,
                    FacultyAssignment.removed_at.is_(None),
                )
            )
        )
        return list(result.scalars().all())

    async def get_by_id(self, assignment_id: UUID) -> FacultyAssignment | None:
        result = await self._session.execute(
            select(FacultyAssignment).where(FacultyAssignment.id == assignment_id)
        )
        return result.scalar_one_or_none()

    async def find_active(
        self, offering_id: UUID, user_id: UUID, role: str
    ) -> FacultyAssignment | None:
        result = await self._session.execute(
            select(FacultyAssignment).where(
                and_(
                    FacultyAssignment.section_offering_id == offering_id,
                    FacultyAssignment.user_id == user_id,
                    FacultyAssignment.role_in_course == role,
                    FacultyAssignment.removed_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, assignment: FacultyAssignment) -> FacultyAssignment:
        self._session.add(assignment)
        await self._session.flush()
        await self._session.refresh(assignment)
        return assignment

    async def remove(self, assignment: FacultyAssignment) -> FacultyAssignment:
        """Sets removed_at to now() by marking it dirty and flushing."""
        from datetime import datetime, timezone
        assignment.removed_at = datetime.now(timezone.utc)
        self._session.add(assignment)
        await self._session.flush()
        await self._session.refresh(assignment)
        return assignment
