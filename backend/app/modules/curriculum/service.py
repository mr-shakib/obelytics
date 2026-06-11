from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.curriculum.domain.prerequisite_graph import PrerequisiteGraphValidator
from app.modules.ref_data.exceptions import RefDataNotFoundError
from app.modules.ref_data.repository import AssessmentTypeRepository, BloomDomainRepository
from app.modules.curriculum.exceptions import (
    AcademicTermConflictError,
    AcademicTermNotFoundError,
    BatchNameConflictError,
    BatchNotFoundError,
    CourseCodeConflictError,
    CourseNotFoundError,
    CurriculumCodeConflictError,
    CurriculumLockedError,
    CurriculumNotFoundError,
    CycleDetectedError,
    FacultyAssignmentConflictError,
    FacultyAssignmentNotFoundError,
    ModuleLeaderAssignmentNotFoundError,
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
    CourseAssessmentTool,
    CoursePrerequisite,
    Curriculum,
    CurriculumCourseSlot,
    CurriculumTermDefinition,
    FacultyAssignment,
    ModuleLeaderAssignment,
    Section,
    SectionOffering,
)
from app.modules.curriculum.repository import (
    AcademicTermRepository,
    BatchRepository,
    CourseAssessmentToolRepository,
    CourseBloomDomainRepository,
    CourseRepository,
    CourseSlotRepository,
    CurriculumRepository,
    CurriculumTermRepository,
    FacultyAssignmentRepository,
    ModuleLeaderAssignmentRepository,
    PrerequisiteRepository,
    SectionOfferingRepository,
    SectionRepository,
)
from app.modules.curriculum.schemas import (
    AcademicTermCreate,
    AcademicTermUpdate,
    BatchCreate,
    BatchUpdate,
    CourseAssessmentToolResponse,
    CourseAssessmentToolsUpdate,
    CourseBloomDomainsUpdate,
    CourseCreate,
    CourseSlotCreate,
    CourseUpdate,
    CurriculumCreate,
    CurriculumTermDefinitionCreate,
    CurriculumUpdate,
    FacultyAssignmentCreate,
    ModuleLeaderAssignmentCreate,
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
        existing = await self._repo.find_by_code(body.code, body.program_id, version=1)
        if existing:
            raise CurriculumCodeConflictError()
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

    async def archive(self, curriculum_id: UUID, org_id: UUID) -> Curriculum:
        curriculum = await self._repo.get_by_id(curriculum_id, org_id)
        if curriculum is None:
            raise CurriculumNotFoundError()
        if curriculum.status == "ARCHIVED":
            raise CurriculumLockedError()
        curriculum.status = "ARCHIVED"
        curriculum.archived_at = datetime.now(timezone.utc)
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
            course_category_id=body.course_category_id,
            course_type=body.course_type,
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


class CourseBloomDomainService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CourseBloomDomainRepository(session)
        self._course_repo = CourseRepository(session)
        self._bloom_domain_repo = BloomDomainRepository(session)

    async def list_for_course(self, course_id: UUID, org_id: UUID) -> list[UUID]:
        course = await self._course_repo.get_by_id(course_id, org_id)
        if course is None:
            raise CourseNotFoundError()
        records = await self._repo.list_by_course(course_id)
        return [r.bloom_domain_id for r in records]

    async def set_for_course(
        self, course_id: UUID, body: CourseBloomDomainsUpdate, org_id: UUID
    ) -> list[UUID]:
        course = await self._course_repo.get_by_id(course_id, org_id)
        if course is None:
            raise CourseNotFoundError()
        valid_ids = {d.id for d in await self._bloom_domain_repo.list_active(org_id)}
        for domain_id in body.bloom_domain_ids:
            if domain_id not in valid_ids:
                raise RefDataNotFoundError("Bloom domain")
        records = await self._repo.replace_for_course(course_id, body.bloom_domain_ids)
        await self._session.commit()
        return [r.bloom_domain_id for r in records]


class CourseAssessmentToolService:
    _LAB_TOOL_NAMES = ["Lab Final"]
    _THEORY_TOOL_NAMES = ["Mid-term Exam", "Final Exam"]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CourseAssessmentToolRepository(session)
        self._course_repo = CourseRepository(session)
        self._curriculum_repo = CurriculumRepository(session)
        self._assessment_type_repo = AssessmentTypeRepository(session)

    async def _to_response_list(
        self, records: list[CourseAssessmentTool], org_id: UUID
    ) -> list[CourseAssessmentToolResponse]:
        types = {a.id: a for a in await self._assessment_type_repo.list_active(org_id)}
        return [
            CourseAssessmentToolResponse(
                id=r.id,
                curriculum_id=r.curriculum_id,
                course_id=r.course_id,
                assessment_type_id=r.assessment_type_id,
                assessment_type_name=types[r.assessment_type_id].name if r.assessment_type_id in types else "",
                is_sessional=types[r.assessment_type_id].is_sessional if r.assessment_type_id in types else False,
                is_locked=r.is_locked,
                created_at=r.created_at,
            )
            for r in records
        ]

    async def _seed_defaults(
        self, course: Course, curriculum_id: UUID, org_id: UUID
    ) -> list[CourseAssessmentTool]:
        names_with_lock: list[tuple[str, bool]] = []
        if course.course_type in ("LAB", "THEORY_LAB"):
            names_with_lock += [(name, True) for name in self._LAB_TOOL_NAMES]
        if course.course_type in ("THEORY", "THEORY_LAB"):
            names_with_lock += [(name, False) for name in self._THEORY_TOOL_NAMES]
        if not names_with_lock:
            return []

        entries: list[tuple[UUID, bool]] = []
        for name, is_locked in names_with_lock:
            assessment_type = await self._assessment_type_repo.find_by_name(name, org_id)
            if assessment_type is not None:
                entries.append((assessment_type.id, is_locked))
        if not entries:
            return []
        return await self._repo.replace_for_course(curriculum_id, course.id, entries)

    async def list_for_course(
        self, course_id: UUID, curriculum_id: UUID, org_id: UUID
    ) -> list[CourseAssessmentToolResponse]:
        course = await self._course_repo.get_by_id(course_id, org_id)
        if course is None:
            raise CourseNotFoundError()
        if await self._curriculum_repo.get_by_id(curriculum_id, org_id) is None:
            raise CurriculumNotFoundError()

        records = await self._repo.list_for_course(curriculum_id, course_id)
        if not records:
            records = await self._seed_defaults(course, curriculum_id, org_id)
            await self._session.commit()
        return await self._to_response_list(records, org_id)

    async def set_tools(
        self, course_id: UUID, curriculum_id: UUID, body: CourseAssessmentToolsUpdate, org_id: UUID
    ) -> list[CourseAssessmentToolResponse]:
        course = await self._course_repo.get_by_id(course_id, org_id)
        if course is None:
            raise CourseNotFoundError()
        if await self._curriculum_repo.get_by_id(curriculum_id, org_id) is None:
            raise CurriculumNotFoundError()

        valid_types = {a.id: a for a in await self._assessment_type_repo.list_active(org_id)}
        for assessment_type_id in body.assessment_type_ids:
            if assessment_type_id not in valid_types:
                raise RefDataNotFoundError("Assessment type")

        existing = await self._repo.list_for_course(curriculum_id, course_id)
        locked_ids = {r.assessment_type_id for r in existing if r.is_locked}

        selected_ids = set(body.assessment_type_ids) | locked_ids
        entries = [(aid, aid in locked_ids) for aid in selected_ids]
        records = await self._repo.replace_for_course(curriculum_id, course_id, entries)
        await self._session.commit()
        return await self._to_response_list(records, org_id)


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


# Season schedule: (season, start_month, start_day, end_month, end_day)
_TERM_SCHEDULES: dict[str, list[tuple[str, int, int, int, int]]] = {
    "TRIMESTER": [
        ("SPRING", 1, 1, 4, 30),
        ("SUMMER", 5, 1, 8, 31),
        ("FALL",   9, 1, 12, 31),
    ],
    "SEMESTER": [
        ("SPRING", 1, 1, 6, 30),
        ("FALL",   7, 1, 12, 31),
    ],
}


class BatchService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = BatchRepository(session)

    async def create(self, body: BatchCreate, org_id: UUID) -> Batch:
        from datetime import date as date_type
        existing = await self._repo.find_by_name(body.name, body.curriculum_id)
        if existing:
            raise BatchNameConflictError()

        batch = Batch(
            organization_id=org_id,
            curriculum_id=body.curriculum_id,
            name=body.name,
            intake_year=body.start_date.year,
            start_date=body.start_date,
            term_system=body.term_system,
            num_semesters=body.num_semesters,
            status="ACTIVE",
        )
        result = await self._repo.create(batch)

        # Auto-generate academic terms and batch calendar
        await self._generate_term_calendar(result, body, org_id)

        await self._session.commit()
        return result

    async def _generate_term_calendar(
        self, batch: Batch, body: BatchCreate, org_id: UUID
    ) -> None:
        from datetime import date as date_type
        from app.modules.curriculum.models import AcademicTerm, BatchTermCalendar

        schedule = _TERM_SCHEDULES[body.term_system]
        terms_per_year = len(schedule)
        start_month = body.start_date.month
        start_year = body.start_date.year

        # Find the season index that contains the start month
        start_idx = 0
        for i, (_, sm, _, _, _) in enumerate(schedule):
            if start_month >= sm:
                start_idx = i

        term_repo = AcademicTermRepository(self._session)

        for term_num in range(1, body.num_semesters + 1):
            abs_idx = start_idx + (term_num - 1)
            season_idx = abs_idx % terms_per_year
            year_offset = abs_idx // terms_per_year
            year = start_year + year_offset

            season, sm, sd, em, ed = schedule[season_idx]
            t_start = date_type(year, sm, sd)
            t_end = date_type(year, em, ed)
            name = f"{season.capitalize()} {year}"

            # Upsert: reuse existing term for this org/year/season
            term = await term_repo.find_by_year_season(year, season, org_id)
            if term is None:
                term = AcademicTerm(
                    organization_id=org_id,
                    name=name,
                    year=year,
                    season=season,
                    start_date=t_start,
                    end_date=t_end,
                    status="UPCOMING",
                )
                self._session.add(term)
                await self._session.flush()
                await self._session.refresh(term)

            calendar_entry = BatchTermCalendar(
                batch_id=batch.id,
                term_number=term_num,
                academic_term_id=term.id,
            )
            self._session.add(calendar_entry)

        await self._session.flush()

    async def get_term_calendar(
        self, batch_id: UUID, org_id: UUID
    ) -> list[tuple[int, "AcademicTerm"]]:
        from app.modules.curriculum.models import AcademicTerm, BatchTermCalendar
        from sqlalchemy import select
        result = await self._session.execute(
            select(BatchTermCalendar, AcademicTerm)
            .join(AcademicTerm, BatchTermCalendar.academic_term_id == AcademicTerm.id)
            .where(BatchTermCalendar.batch_id == batch_id)
            .order_by(BatchTermCalendar.term_number)
        )
        return [(row.BatchTermCalendar.term_number, row.AcademicTerm) for row in result]

    async def get_semester_plan(self, batch_id: UUID, org_id: UUID) -> list[dict]:
        from sqlalchemy import select
        from app.modules.curriculum.models import (
            BatchTermCalendar, AcademicTerm, Batch,
            CurriculumTermDefinition, CurriculumCourseSlot, Course,
        )

        batch = await self._repo.get_by_id(batch_id, org_id)
        if batch is None:
            raise BatchNotFoundError()

        stmt = (
            select(
                BatchTermCalendar.term_number,
                AcademicTerm.id.label("academic_term_id"),
                AcademicTerm.name,
                AcademicTerm.year,
                AcademicTerm.season,
                AcademicTerm.start_date,
                AcademicTerm.end_date,
                AcademicTerm.status,
                Course.id.label("course_id"),
                Course.code,
                Course.title,
                Course.credits,
                Course.theory_hours,
                Course.lab_hours,
                CurriculumCourseSlot.is_elective,
            )
            .select_from(BatchTermCalendar)
            .join(AcademicTerm, BatchTermCalendar.academic_term_id == AcademicTerm.id)
            .join(Batch, BatchTermCalendar.batch_id == Batch.id)
            .outerjoin(
                CurriculumTermDefinition,
                (CurriculumTermDefinition.curriculum_id == Batch.curriculum_id)
                & (CurriculumTermDefinition.term_number == BatchTermCalendar.term_number),
            )
            .outerjoin(
                CurriculumCourseSlot,
                CurriculumCourseSlot.curriculum_term_definition_id == CurriculumTermDefinition.id,
            )
            .outerjoin(Course, CurriculumCourseSlot.course_id == Course.id)
            .where(BatchTermCalendar.batch_id == batch_id)
            .order_by(BatchTermCalendar.term_number, Course.code)
        )

        rows = (await self._session.execute(stmt)).all()

        plan: dict[int, dict] = {}
        for row in rows:
            tn = row.term_number
            if tn not in plan:
                plan[tn] = {
                    "term_number": tn,
                    "academic_term_id": row.academic_term_id,
                    "name": row.name,
                    "year": row.year,
                    "season": row.season,
                    "start_date": row.start_date,
                    "end_date": row.end_date,
                    "status": row.status,
                    "courses": [],
                }
            if row.course_id is not None:
                plan[tn]["courses"].append({
                    "course_id": row.course_id,
                    "code": row.code,
                    "title": row.title,
                    "credits": row.credits,
                    "theory_hours": row.theory_hours,
                    "lab_hours": row.lab_hours,
                    "is_elective": bool(row.is_elective),
                })

        result = []
        for tn in sorted(plan.keys()):
            entry = plan[tn]
            entry["total_credits"] = sum(c["credits"] for c in entry["courses"])
            result.append(entry)
        return result

    async def get_batch_term_offerings(
        self, batch_id: UUID, academic_term_id: UUID, org_id: UUID
    ) -> list[dict]:
        from sqlalchemy import select
        from app.modules.curriculum.models import (
            BatchTermCalendar, CurriculumTermDefinition, CurriculumCourseSlot,
            Course, SectionOffering, Section,
        )
        from app.modules.curriculum.exceptions import AcademicTermNotFoundError

        batch = await self._repo.get_by_id(batch_id, org_id)
        if batch is None:
            raise BatchNotFoundError()

        # Resolve term_number for this academic_term within this batch
        btc_result = await self._session.execute(
            select(BatchTermCalendar).where(
                BatchTermCalendar.batch_id == batch_id,
                BatchTermCalendar.academic_term_id == academic_term_id,
            )
        )
        btc = btc_result.scalar_one_or_none()
        if btc is None:
            raise AcademicTermNotFoundError()

        # Courses for this curriculum+term_number
        courses_result = await self._session.execute(
            select(
                CurriculumCourseSlot.id.label("slot_id"),
                CurriculumCourseSlot.course_id,
                CurriculumCourseSlot.curriculum_term_definition_id,
                CurriculumCourseSlot.is_elective,
                Course.code,
                Course.title,
                Course.credits,
                Course.theory_hours,
                Course.lab_hours,
            )
            .join(CurriculumTermDefinition, CurriculumCourseSlot.curriculum_term_definition_id == CurriculumTermDefinition.id)
            .join(Course, CurriculumCourseSlot.course_id == Course.id)
            .where(
                CurriculumTermDefinition.curriculum_id == batch.curriculum_id,
                CurriculumTermDefinition.term_number == btc.term_number,
            )
            .order_by(Course.code)
        )
        courses = courses_result.all()

        # Existing section offerings for this batch+term with section names
        offerings_result = await self._session.execute(
            select(
                SectionOffering.id,
                SectionOffering.course_id,
                SectionOffering.section_id,
                SectionOffering.status,
                Section.name.label("section_name"),
                Section.capacity,
            )
            .join(Section, SectionOffering.section_id == Section.id)
            .where(
                SectionOffering.batch_id == batch_id,
                SectionOffering.academic_term_id == academic_term_id,
            )
            .order_by(SectionOffering.course_id, Section.name)
        )
        offerings_by_course: dict = {}
        for o in offerings_result.all():
            offerings_by_course.setdefault(o.course_id, []).append({
                "id": o.id,
                "section_id": o.section_id,
                "section_name": o.section_name,
                "capacity": o.capacity,
                "status": o.status,
            })

        return [
            {
                "course_id": c.course_id,
                "curriculum_term_definition_id": c.curriculum_term_definition_id,
                "code": c.code,
                "title": c.title,
                "credits": c.credits,
                "theory_hours": c.theory_hours,
                "lab_hours": c.lab_hours,
                "is_elective": bool(c.is_elective),
                "offerings": offerings_by_course.get(c.course_id, []),
            }
            for c in courses
        ]

    async def add_section_offering(
        self,
        batch_id: UUID,
        academic_term_id: UUID,
        course_id: UUID,
        section_name: str,
        org_id: UUID,
    ) -> SectionOffering:
        batch = await self._repo.get_by_id(batch_id, org_id)
        if batch is None:
            raise BatchNotFoundError()

        section_svc = SectionService(self._session)
        section = await section_svc.get_or_create(section_name.strip().upper(), org_id)

        repo = SectionOfferingRepository(self._session)
        if await repo.find_duplicate(batch_id, course_id, academic_term_id, section.id):
            raise SectionOfferingConflictError()

        offering = SectionOffering(
            organization_id=org_id,
            curriculum_id=batch.curriculum_id,
            batch_id=batch_id,
            course_id=course_id,
            academic_term_id=academic_term_id,
            section_id=section.id,
            status="UPCOMING",
        )
        self._session.add(offering)
        await self._session.flush()
        await self._session.refresh(offering)
        await self._session.commit()
        return offering

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

    async def get_or_create(self, name: str, org_id: UUID) -> Section:
        existing = await self._repo.find_by_name(name, org_id)
        if existing:
            return existing
        section = Section(organization_id=org_id, name=name)
        self._session.add(section)
        await self._session.flush()
        await self._session.refresh(section)
        return section


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

    async def delete(self, offering_id: UUID, org_id: UUID) -> None:
        offering = await self._repo.get_by_id(offering_id, org_id)
        if offering is None:
            raise SectionOfferingNotFoundError()
        await self._repo.delete(offering)
        await self._session.commit()


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


class ModuleLeaderAssignmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ModuleLeaderAssignmentRepository(session)

    async def list_active(
        self, org_id: UUID, batch_id: UUID, academic_term_id: UUID
    ) -> list[ModuleLeaderAssignment]:
        return await self._repo.list_active(org_id, batch_id, academic_term_id)

    async def list_mine(self, org_id: UUID, user_id: UUID) -> list[ModuleLeaderAssignment]:
        return await self._repo.list_for_user(org_id, user_id)

    async def assign(
        self, body: ModuleLeaderAssignmentCreate, org_id: UUID
    ) -> ModuleLeaderAssignment:
        existing = await self._repo.find_active(
            body.batch_id, body.academic_term_id, body.course_id
        )
        if existing:
            await self._repo.remove(existing)
        assignment = ModuleLeaderAssignment(
            organization_id=org_id,
            batch_id=body.batch_id,
            academic_term_id=body.academic_term_id,
            course_id=body.course_id,
            user_id=body.user_id,
        )
        result = await self._repo.create(assignment)
        await self._session.commit()
        return result

    async def remove(self, assignment_id: UUID, org_id: UUID) -> ModuleLeaderAssignment:
        assignment = await self._repo.get_by_id(assignment_id)
        if assignment is None or assignment.organization_id != org_id:
            raise ModuleLeaderAssignmentNotFoundError()
        result = await self._repo.remove(assignment)
        await self._session.commit()
        return result
