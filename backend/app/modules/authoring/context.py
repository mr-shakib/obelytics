"""
Loads what the outcome-authoring prompts need about one course, as plain objects.

Everything here is curriculum data (course text, outcomes, reference lists): no
student or marks data is ever read, so nothing personal can reach a model.
The objects are detached from the session, so callers can release the database
connection while the model works.
"""
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.curriculum.exceptions import CourseNotFoundError, CurriculumNotFoundError
from app.modules.curriculum.models import (
    Course,
    CourseBloomDomain,
    CourseLessonPlanItem,
    CourseObjective,
    CoursePrerequisite,
    Curriculum,
)
from app.modules.obe.mapping_rules import natural_key
from app.modules.obe.models import (
    COCAMapping,
    COCPMapping,
    COKPMapping,
    POKnowledgeProfile,
    ProgramOutcome,
)
from app.modules.obe.service import COService
from app.modules.org.models import Program
from app.modules.ref_data.models import (
    BloomDomain,
    BloomLevel,
    ComplexActivity,
    ComplexProblem,
    KnowledgeProfile,
)

# Keep prompts a sensible size whatever a syllabus contains.
MAX_DESCRIPTION = 1500
MAX_SYLLABUS = 4000
MAX_TOPICS = 40
MAX_TOPIC = 200
MAX_OBJECTIVES = 15


@dataclass(frozen=True)
class Level:
    id: UUID
    code: str
    name: str
    domain_id: UUID
    domain_name: str


@dataclass(frozen=True)
class Attribute:
    """A knowledge profile, complex engineering problem or complex engineering activity."""

    id: UUID
    code: str
    name: str | None
    description: str


@dataclass
class Outcome:
    id: UUID
    code: str
    statement: str
    bloom_level_ids: list[UUID] = field(default_factory=list)
    kp_ids: set[UUID] = field(default_factory=set)
    cep_ids: set[UUID] = field(default_factory=set)
    cea_ids: set[UUID] = field(default_factory=set)


@dataclass
class ProgramOutcomeInfo:
    id: UUID
    code: str
    statement: str
    bloom_domain_id: UUID | None
    kp_ids: set[UUID] = field(default_factory=set)


@dataclass
class CourseContext:
    organization_id: UUID
    curriculum_id: UUID
    course_id: UUID
    code: str
    title: str
    course_type: str
    credits: float
    theory_hours: float
    lab_hours: float
    description: str
    syllabus: str
    objectives: list[str]
    topics: list[str]
    prerequisites: list[str]
    domain_names: list[str]
    # Bloom levels a CO of this course may use (the course's domains, else all).
    levels: list[Level]
    # Every active level in the organization, to read the tags on existing COs.
    all_levels: list[Level]
    outcomes: list[Outcome]
    program_outcomes: list[ProgramOutcomeInfo]
    knowledge_profiles: list[Attribute] = field(default_factory=list)
    complex_problems: list[Attribute] = field(default_factory=list)
    complex_activities: list[Attribute] = field(default_factory=list)

    def level_by_id(self, level_id: UUID) -> Level | None:
        return next((lvl for lvl in self.all_levels if lvl.id == level_id), None)

    def levels_for(self, level_ids: list[UUID]) -> list[Level]:
        return [lvl for lvl in (self.level_by_id(i) for i in level_ids) if lvl]


def _clip(text: str | None, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


async def load_course_context(
    session: AsyncSession,
    organization_id: UUID,
    curriculum_id: UUID,
    course_id: UUID,
    *,
    with_attributes: bool = False,
) -> CourseContext:
    curriculum = (await session.execute(select(Curriculum).where(and_(
        Curriculum.id == curriculum_id, Curriculum.organization_id == organization_id,
    )))).scalar_one_or_none()
    if curriculum is None:
        raise CurriculumNotFoundError()
    course = (await session.execute(select(Course).where(and_(
        Course.id == course_id, Course.organization_id == organization_id,
    )))).scalar_one_or_none()
    if course is None:
        raise CourseNotFoundError()

    objectives = (await session.execute(
        select(CourseObjective.statement).where(CourseObjective.course_id == course_id)
        .order_by(CourseObjective.order_index)
    )).scalars().all()
    topics = (await session.execute(
        select(CourseLessonPlanItem.week_number, CourseLessonPlanItem.topic).where(and_(
            CourseLessonPlanItem.curriculum_id == curriculum_id,
            CourseLessonPlanItem.course_id == course_id,
        )).order_by(CourseLessonPlanItem.week_number, CourseLessonPlanItem.order_index)
    )).all()
    prerequisites = (await session.execute(
        select(Course.code, Course.title)
        .join(CoursePrerequisite, CoursePrerequisite.prerequisite_course_id == Course.id)
        .where(CoursePrerequisite.course_id == course_id)
    )).all()

    domains = {d.id: d for d in (await session.execute(
        select(BloomDomain).where(and_(
            BloomDomain.organization_id == organization_id, BloomDomain.is_active.is_(True),
        ))
    )).scalars().all()}
    level_rows = (await session.execute(
        select(BloomLevel).where(and_(
            BloomLevel.organization_id == organization_id, BloomLevel.is_active.is_(True),
        )).order_by(BloomLevel.order_index)
    )).scalars().all()
    all_levels = [
        Level(lvl.id, lvl.code, lvl.name, lvl.bloom_domain_id, domains[lvl.bloom_domain_id].name)
        for lvl in level_rows if lvl.bloom_domain_id in domains
    ]
    all_levels.sort(key=lambda lvl: (lvl.domain_name, natural_key(lvl.code)))
    course_domain_ids = set((await session.execute(
        select(CourseBloomDomain.bloom_domain_id).where(CourseBloomDomain.course_id == course_id)
    )).scalars().all())
    levels = [lvl for lvl in all_levels if not course_domain_ids or lvl.domain_id in course_domain_ids]

    co_rows = await COService(session).list_by_curriculum_course(
        curriculum_id, course_id, organization_id
    )
    outcomes = [
        Outcome(co.id, co.code, co.statement, list(co.bloom_level_ids))
        for co in sorted(co_rows, key=lambda co: natural_key(co.code))
    ]

    context = CourseContext(
        organization_id=organization_id,
        curriculum_id=curriculum_id,
        course_id=course_id,
        code=course.code,
        title=course.title,
        course_type=course.course_type,
        credits=course.credits,
        theory_hours=course.theory_hours or 0,
        lab_hours=course.lab_hours or 0,
        description=_clip(course.description, MAX_DESCRIPTION),
        syllabus=_clip(course.syllabus_content, MAX_SYLLABUS),
        objectives=[_clip(o, 400) for o in objectives[:MAX_OBJECTIVES]],
        topics=[f"Week {week}: {_clip(topic, MAX_TOPIC)}" for week, topic in topics[:MAX_TOPICS]],
        prerequisites=[f"{code} {title}" for code, title in prerequisites],
        domain_names=sorted(domains[d].name for d in course_domain_ids if d in domains),
        levels=levels,
        all_levels=all_levels,
        outcomes=outcomes,
        program_outcomes=await program_outcomes_for(session, organization_id, curriculum.program_id),
    )
    if with_attributes:
        await _load_attributes(session, context)
    return context


async def program_outcomes_for(
    session: AsyncSession, organization_id: UUID, program_id: UUID
) -> list[ProgramOutcomeInfo]:
    """
    The POs a course in this program maps to: the program's own POs, else the
    template set of the program's PO version, else every active PO (as the mapping
    page shows). One PO per code.
    """
    active = and_(ProgramOutcome.organization_id == organization_id, ProgramOutcome.status == "ACTIVE")
    rows = (await session.execute(
        select(ProgramOutcome).where(active, ProgramOutcome.program_id == program_id)
    )).scalars().all()
    if not rows:
        version_id = (await session.execute(
            select(Program.po_version_id).where(Program.id == program_id)
        )).scalar_one_or_none()
        if version_id:
            rows = (await session.execute(select(ProgramOutcome).where(
                active, ProgramOutcome.po_version_id == version_id, ProgramOutcome.program_id.is_(None),
            ))).scalars().all()
    if not rows:
        rows = (await session.execute(select(ProgramOutcome).where(active))).scalars().all()

    by_code: dict[str, ProgramOutcomeInfo] = {}
    for po in sorted(rows, key=lambda po: (po.order_index, natural_key(po.code))):
        by_code.setdefault(po.code, ProgramOutcomeInfo(po.id, po.code, po.statement, po.bloom_domain_id))
    pos = sorted(by_code.values(), key=lambda po: natural_key(po.code))
    if pos:
        kp_rows = (await session.execute(
            select(POKnowledgeProfile.program_outcome_id, POKnowledgeProfile.knowledge_profile_id)
            .where(POKnowledgeProfile.program_outcome_id.in_([po.id for po in pos]))
        )).all()
        by_id = {po.id: po for po in pos}
        for po_id, kp_id in kp_rows:
            by_id[po_id].kp_ids.add(kp_id)
    return pos


async def _load_attributes(session: AsyncSession, context: CourseContext) -> None:
    org = context.organization_id

    async def active(model) -> list[Attribute]:
        rows = (await session.execute(select(model).where(and_(
            model.organization_id == org, model.is_active.is_(True),
        )))).scalars().all()
        attrs = [Attribute(r.id, r.code, getattr(r, "name", None), r.description) for r in rows]
        return sorted(attrs, key=lambda a: natural_key(a.code))

    context.knowledge_profiles = await active(KnowledgeProfile)
    context.complex_problems = await active(ComplexProblem)
    context.complex_activities = await active(ComplexActivity)

    co_ids = [co.id for co in context.outcomes]
    if not co_ids:
        return
    by_id = {co.id: co for co in context.outcomes}
    for model, column, target in (
        (COKPMapping, COKPMapping.knowledge_profile_id, "kp_ids"),
        (COCPMapping, COCPMapping.complex_problem_id, "cep_ids"),
        (COCAMapping, COCAMapping.complex_activity_id, "cea_ids"),
    ):
        rows = (await session.execute(
            select(model.course_outcome_id, column).where(model.course_outcome_id.in_(co_ids))
        )).all()
        for co_id, attr_id in rows:
            getattr(by_id[co_id], target).add(attr_id)
