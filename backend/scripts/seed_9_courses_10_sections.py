"""
Run: python -m scripts.seed_9_courses_10_sections

Seeds 10 sections for each of the 9 current courses (CSE101, CSE101L, CSE102,
CSE201, CSE201L, CSE203, CSE203L, CSE301, CSE301L):

  - Reuses the same 10 real faculty members (Lecturers) as section teachers,
    one consistently owning "-S01".."-S10" across every course.
  - Splits the existing 50 students into 10 fixed groups of 5, reused
    identically across every course/section so the same students' PO
    attainment is comparable and cumulative across courses.
  - Rebuilds each course's Mid-term/Final CO-marks breakdown (the evaluation
    tools TOTALS set earlier are preserved) so CO-tied exam questions can be
    generated; Quiz/Assignment/Presentation/Attendance are entered as flat
    (non-CO-tied) continuous-assessment marks.
  - Seeds marks with a deliberate spread (top band clears every CO, lowest
    band misses most), submits the result publication, and submits the
    course end report with justifications for any unattained CO.
"""

from __future__ import annotations

import asyncio
import os
import sys
from decimal import Decimal
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.modules.assessment.models import Assessment, Student, StudentMark
from app.modules.curriculum.models import (
    Course,
    CourseCOMarks,
    FacultyAssignment,
    Section,
    SectionOffering,
)
from app.modules.curriculum.schemas import (
    CourseCOMarkInput,
    CourseCOMarksUpdate,
    FacultyAssignmentCreate,
)
from app.modules.curriculum.service import CourseAssessmentPatternService, FacultyAssignmentService
from app.modules.iam.models import Role, User, UserRoleAssignment
from app.modules.obe.models import CourseOutcome
from app.modules.ref_data.models import AssessmentType
from scripts.seed_15_more_course_results import (
    _ratio,
    _d,
    co_index_for,
    ensure_enrollments,
    get_section_teacher_id,
    load_course_mark_plan,
    seed_marks_for_offering,
    submit_result_and_end_report,
)

SECTION_COUNT = 10
ORG_ID = UUID("5b7006ed-03d0-4d19-86b9-34d63b0e298a")
CURRICULUM_ID = UUID("a8c8f7aa-cbfa-4492-8719-01ab5f4de8d4")
BATCH_ID = UUID("90b35363-9d3d-4e24-8bba-ce0263a21841")
TERM_ID = UUID("6455b718-eb90-4603-a152-39772100a231")  # Fall 2026

COURSE_CODES = ["CSE101", "CSE101L", "CSE102", "CSE201", "CSE201L", "CSE203", "CSE203L", "CSE301", "CSE301L"]

# TOTAL evaluation-tool marks set earlier — preserved as-is when rebuilding CO breakdown.
TOOL_TOTALS = {
    "Mid-term Exam": 25,
    "Final Exam": 40,
    "Assignment": 5,
    "Presentation": 8,
    "Attendance": 7,
    "Quiz": 15,
}
FLAT_TOOLS = ["Quiz", "Assignment", "Presentation", "Attendance"]


async def _one(session: AsyncSession, stmt):
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def rebuild_course_co_marks(session: AsyncSession, course: Course) -> None:
    """Re-enter the course's evaluation-tool TOTALs plus a Mid-term/Final
    per-CO breakdown (needed to generate CO-tied exam questions)."""
    cos = (
        await session.execute(
            select(CourseOutcome).where(CourseOutcome.course_id == course.id).order_by(CourseOutcome.code)
        )
    ).scalars().all()
    co_ids = [co.id for co in cos]

    types = {
        t.name: t
        for t in (await session.execute(select(AssessmentType).where(AssessmentType.organization_id == ORG_ID))).scalars().all()
    }

    marks: list[CourseCOMarkInput] = [
        CourseCOMarkInput(assessment_type_id=types[name].id, course_outcome_id=None, marks=val)
        for name, val in TOOL_TOTALS.items()
    ]

    if len(co_ids) == 4:
        mid_split = [13, 12, 0, 0]
        final_split = [5, 10, 10, 15]
    elif len(co_ids) == 3:
        mid_split = [13, 12, 0]
        final_split = [10, 15, 15]
    else:
        raise RuntimeError(f"Unexpected CO count for {course.code}: {len(co_ids)}")

    for co_id, m in zip(co_ids, mid_split):
        if m > 0:
            marks.append(CourseCOMarkInput(assessment_type_id=types["Mid-term Exam"].id, course_outcome_id=co_id, marks=m))
    for co_id, f in zip(co_ids, final_split):
        if f > 0:
            marks.append(CourseCOMarkInput(assessment_type_id=types["Final Exam"].id, course_outcome_id=co_id, marks=f))

    pattern_svc = CourseAssessmentPatternService(session)
    await pattern_svc.set_for_course(course.id, CURRICULUM_ID, CourseCOMarksUpdate(marks=marks), ORG_ID)


async def seed_flat_assessment(
    session: AsyncSession, offering: SectionOffering, tool_name: str, total_marks: Decimal,
    enrollments, teacher_id: UUID, course_index: int, section_index: int,
) -> None:
    """Quiz/Assignment/Presentation/Attendance — not CO-tied, just an overall mark per student."""
    atype = await _one(session, select(AssessmentType).where(AssessmentType.organization_id == ORG_ID, AssessmentType.name == tool_name))
    if atype is None:
        return
    assessment = Assessment(
        organization_id=offering.organization_id,
        section_offering_id=offering.id,
        assessment_type_id=atype.id,
        name=tool_name,
        total_marks=total_marks,
        weightage_percent=total_marks,
        status="CONFIGURED",
    )
    session.add(assessment)
    await session.flush()
    for student_index, enrollment in enumerate(enrollments, start=1):
        ratio = _ratio(student_index, 1, section_index, course_index)
        session.add(
            StudentMark(
                organization_id=offering.organization_id,
                assessment_id=assessment.id,
                student_enrollment_id=enrollment.id,
                marks_obtained=(total_marks * ratio).quantize(Decimal("0.01")),
                is_absent=False,
                entered_by_user_id=teacher_id,
            )
        )


async def get_teachers(session: AsyncSession) -> list[UUID]:
    rows = (
        await session.execute(
            select(User)
            .where(User.organization_id == ORG_ID, User.designation.ilike("%lecturer%"))
            .order_by(User.employee_id)
            .limit(SECTION_COUNT)
        )
    ).scalars().all()
    if len(rows) < SECTION_COUNT:
        raise RuntimeError(f"Expected {SECTION_COUNT} lecturer-designated users, found {len(rows)}")

    role = await _one(session, select(Role).where(Role.organization_id == ORG_ID, Role.name == "Section Teacher"))
    for user in rows:
        existing = await _one(
            session,
            select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == user.id,
                UserRoleAssignment.role_id == role.id,
                UserRoleAssignment.removed_at.is_(None),
            ),
        )
        if existing is None:
            session.add(UserRoleAssignment(user_id=user.id, role_id=role.id, scope_type="GLOBAL", scope_id=None, assigned_by=None))
    await session.flush()
    return [u.id for u in rows]


async def get_student_groups(session: AsyncSession) -> dict[int, list[Student]]:
    students = (
        await session.execute(
            select(Student).where(Student.organization_id == ORG_ID, Student.batch_id == BATCH_ID, Student.status == "ACTIVE")
            .order_by(Student.student_id_number)
        )
    ).scalars().all()
    if len(students) != 50:
        raise RuntimeError(f"Expected 50 students, got {len(students)}")
    groups: dict[int, list[Student]] = {}
    for i in range(SECTION_COUNT):
        groups[i + 1] = list(students[i * 5:(i + 1) * 5])
    return groups


async def ensure_section_and_offering(session: AsyncSession, course: Course, index: int) -> tuple[Section, SectionOffering]:
    section_name = f"{course.code}-S{index:02d}"
    section = await _one(session, select(Section).where(Section.organization_id == ORG_ID, Section.name == section_name))
    if section is None:
        section = Section(organization_id=ORG_ID, name=section_name, capacity=10)
        session.add(section)
        await session.flush()

    offering = await _one(
        session,
        select(SectionOffering).where(
            SectionOffering.batch_id == BATCH_ID,
            SectionOffering.course_id == course.id,
            SectionOffering.academic_term_id == TERM_ID,
            SectionOffering.section_id == section.id,
        ),
    )
    if offering is None:
        offering = SectionOffering(
            organization_id=ORG_ID,
            curriculum_id=CURRICULUM_ID,
            batch_id=BATCH_ID,
            course_id=course.id,
            academic_term_id=TERM_ID,
            section_id=section.id,
            status="UPCOMING",
        )
        session.add(offering)
        await session.flush()
    return section, offering


async def ensure_section_teacher_assignment(session: AsyncSession, offering: SectionOffering, teacher_id: UUID) -> None:
    existing = await _one(
        session,
        select(FacultyAssignment).where(
            FacultyAssignment.section_offering_id == offering.id,
            FacultyAssignment.user_id == teacher_id,
            FacultyAssignment.role_in_course == "SECTION_TEACHER",
            FacultyAssignment.removed_at.is_(None),
        ),
    )
    if existing is not None:
        return
    service = FacultyAssignmentService(session)
    await service.assign(
        FacultyAssignmentCreate(section_offering_id=offering.id, user_id=teacher_id, role_in_course="SECTION_TEACHER"),
        ORG_ID,
    )


async def seed_all() -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        teacher_ids = await get_teachers(session)
        student_groups = await get_student_groups(session)
        await session.commit()
        print(f"Teachers: {len(teacher_ids)}, student groups: {len(student_groups)} x {len(student_groups[1])}")

        total_sections = 0
        total_enrollments = 0

        for course_index, course_code in enumerate(COURSE_CODES, start=1):
            course = await _one(session, select(Course).where(Course.organization_id == ORG_ID, Course.code == course_code, Course.status == "ACTIVE"))
            if course is None:
                raise RuntimeError(f"Course not found: {course_code}")

            await rebuild_course_co_marks(session, course)
            await session.commit()

            mark_plan = await load_course_mark_plan(session, CURRICULUM_ID, course.id)

            print(f"\n=== {course_code} ===")
            for section_index in range(1, SECTION_COUNT + 1):
                section, offering = await ensure_section_and_offering(session, course, section_index)
                teacher_id = teacher_ids[section_index - 1]
                await ensure_section_teacher_assignment(session, offering, teacher_id)
                await session.commit()

                enrollments = await ensure_enrollments(session, offering, student_groups[section_index])

                co_code_by_id = {
                    co.id: co.code
                    for co in (await session.execute(select(CourseOutcome).where(CourseOutcome.course_id == course.id))).scalars().all()
                }

                await seed_marks_for_offering(
                    session, offering, course_index=course_index, section_index=section_index,
                    enrollments=enrollments, teacher_id=teacher_id, co_code_by_id=co_code_by_id, mark_plan=mark_plan,
                )

                for tool_name in FLAT_TOOLS:
                    await seed_flat_assessment(
                        session, offering, tool_name, _d(TOOL_TOTALS[tool_name]),
                        enrollments, teacher_id, course_index, section_index,
                    )

                await submit_result_and_end_report(session, offering, course, section.name, teacher_id)
                await session.commit()

                total_sections += 1
                total_enrollments += len(enrollments)
                print(f"  {section.name}: submitted ({len(enrollments)} students, teacher {teacher_id})")

        print("\nDone.")
        print(f"Courses processed: {len(COURSE_CODES)}")
        print(f"Sections submitted: {total_sections}")
        print(f"Enrollments: {total_enrollments}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_all())
