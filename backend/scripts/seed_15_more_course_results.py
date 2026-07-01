"""
Run: python -m scripts.seed_15_more_course_results

Seeds the full section/assessment/result/end-report workflow for 15 additional
courses using the existing CSE102 students as the shared cohort.

For every target course:
  - creates/reuses module leader, 15 sections, and section teachers
  - enrolls the existing CSE102-Sxx students into the matching course section
  - creates MID/FINAL question marks from the course CO mark pattern
  - creates assessment totals for all configured tools
  - submits each section result publication
  - submits each section end report

The deterministic marks differ by course, section, student band, and CO so that
some CO/PO thresholds are attained and some are not. Because the same students
are reused across courses, the same PO can be attained from multiple courses.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.modules.assessment.models import (
    Assessment,
    AssessmentCOWeight,
    CourseEndReport,
    MarksheetMark,
    MarksheetQuestion,
    ResultPublication,
    Student,
    StudentEnrollment,
    StudentMark,
)
from app.modules.assessment.service import MarksheetService
from app.modules.curriculum.models import (
    Course,
    CourseCOMarks,
    FacultyAssignment,
    Section,
    SectionOffering,
)
from app.modules.obe.models import CourseOutcome
from app.modules.org.models import Organization
from app.modules.ref_data.models import AssessmentType
from scripts.seed_course_staffing import seed_staffing

_ = Organization

TARGET_COURSES = [
    "CSE104",
    "CSE105",
    "CSE106",
    "CSE201",
    "CSE202",
    "CSE203",
    "CSE204",
    "CSE205",
    "CSE206",
    "CSE301",
    "CSE302",
    "CSE303",
    "CSE304",
    "CSE305",
    "CSE306",
]
BASE_STUDENT_COURSE = "CSE102"
SECTION_COUNT = 15


async def _one(session: AsyncSession, stmt):
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _d(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _ratio(student_index: int, co_index: int, section_index: int, course_index: int) -> Decimal:
    wobble = Decimal(((section_index + course_index + student_index + co_index) % 7) - 3) / Decimal("100")
    if student_index <= 5:
        base = Decimal("0.88") - Decimal(co_index - 1) * Decimal("0.03")
    elif student_index <= 12:
        base = Decimal("0.70") - Decimal(co_index - 1) * Decimal("0.07")
    elif student_index <= 17:
        base = Decimal("0.55") - Decimal(co_index - 1) * Decimal("0.08")
    else:
        base = Decimal("0.38") - Decimal(co_index - 1) * Decimal("0.05")
    return max(Decimal("0.05"), min(Decimal("0.98"), base + wobble))


async def load_course_context(
    session: AsyncSession, course_code: str
) -> tuple[Course, list[SectionOffering], list[CourseOutcome], dict[UUID, str]]:
    course = await _one(
        session,
        select(Course).where(Course.code == course_code, Course.status == "ACTIVE"),
    )
    if course is None:
        raise RuntimeError(f"Course not found: {course_code}")

    offerings = (
        await session.execute(
            select(SectionOffering)
            .join(Section, Section.id == SectionOffering.section_id)
            .where(SectionOffering.course_id == course.id, Section.name.like(f"{course_code}-S%"))
            .order_by(Section.name)
        )
    ).scalars().all()
    if len(offerings) != SECTION_COUNT:
        raise RuntimeError(f"Expected {SECTION_COUNT} sections for {course_code}")

    cos = (
        await session.execute(
            select(CourseOutcome)
            .where(CourseOutcome.course_id == course.id)
            .order_by(CourseOutcome.code)
        )
    ).scalars().all()
    if not cos:
        raise RuntimeError(f"No course outcomes found for {course_code}")
    return course, list(offerings), list(cos), {co.id: co.code for co in cos}


async def get_existing_cse102_students_by_section(
    session: AsyncSession, org_id: UUID
) -> dict[int, list[Student]]:
    students_by_section: dict[int, list[Student]] = {}
    for section_index in range(1, SECTION_COUNT + 1):
        prefix = f"{BASE_STUDENT_COURSE}-{section_index:02d}-"
        students = (
            await session.execute(
                select(Student)
                .where(
                    Student.organization_id == org_id,
                    Student.student_id_number.like(f"{prefix}%"),
                    Student.status == "ACTIVE",
                )
                .order_by(Student.student_id_number)
            )
        ).scalars().all()
        if len(students) != 20:
            raise RuntimeError(
                f"Expected 20 existing students for {BASE_STUDENT_COURSE}-S{section_index:02d}; "
                "run seed_cse102_marks first."
            )
        students_by_section[section_index] = list(students)
    return students_by_section


async def ensure_enrollments(
    session: AsyncSession,
    offering: SectionOffering,
    students: list[Student],
) -> list[StudentEnrollment]:
    enrollments: list[StudentEnrollment] = []
    for student in students:
        enrollment = await _one(
            session,
            select(StudentEnrollment).where(
                StudentEnrollment.student_id == student.id,
                StudentEnrollment.section_offering_id == offering.id,
            ),
        )
        if enrollment is None:
            enrollment = StudentEnrollment(
                organization_id=offering.organization_id,
                student_id=student.id,
                section_offering_id=offering.id,
                status="ACTIVE",
            )
            session.add(enrollment)
            await session.flush()
        else:
            enrollment.status = "ACTIVE"
        enrollments.append(enrollment)
    return enrollments


async def reset_offering(session: AsyncSession, offering_id: UUID) -> None:
    report = await _one(
        session,
        select(CourseEndReport).where(CourseEndReport.section_offering_id == offering_id),
    )
    if report is not None:
        report.status = "DRAFT"
        report.submitted_at = None

    pub = await _one(
        session,
        select(ResultPublication).where(ResultPublication.section_offering_id == offering_id),
    )
    if pub is not None:
        pub.status = "DRAFT"
        pub.submitted_by_user_id = None
        pub.submitted_at = None
        pub.ml_approved_by_user_id = None
        pub.ml_approved_at = None
        pub.pc_approved_by_user_id = None
        pub.pc_approved_at = None
        pub.published_by_user_id = None
        pub.published_at = None

    question_ids = (
        await session.execute(
            select(MarksheetQuestion.id).where(MarksheetQuestion.section_offering_id == offering_id)
        )
    ).scalars().all()
    if question_ids:
        await session.execute(delete(MarksheetMark).where(MarksheetMark.question_id.in_(question_ids)))
        await session.execute(delete(MarksheetQuestion).where(MarksheetQuestion.id.in_(question_ids)))

    assessment_ids = (
        await session.execute(select(Assessment.id).where(Assessment.section_offering_id == offering_id))
    ).scalars().all()
    if assessment_ids:
        await session.execute(delete(StudentMark).where(StudentMark.assessment_id.in_(assessment_ids)))
        await session.execute(delete(AssessmentCOWeight).where(AssessmentCOWeight.assessment_id.in_(assessment_ids)))
        await session.execute(delete(Assessment).where(Assessment.id.in_(assessment_ids)))
    await session.flush()


async def load_course_mark_plan(
    session: AsyncSession,
    curriculum_id: UUID,
    course_id: UUID,
) -> dict[str, list[CourseCOMarks]]:
    rows = (
        await session.execute(
            select(CourseCOMarks, AssessmentType.name)
            .join(AssessmentType, AssessmentType.id == CourseCOMarks.assessment_type_id)
            .where(
                CourseCOMarks.curriculum_id == curriculum_id,
                CourseCOMarks.course_id == course_id,
                CourseCOMarks.course_outcome_id.is_not(None),
            )
            .order_by(AssessmentType.name, CourseCOMarks.created_at)
        )
    ).all()
    plan: dict[str, list[CourseCOMarks]] = defaultdict(list)
    for mark, type_name in rows:
        if Decimal(str(mark.marks)) > 0:
            plan[type_name].append(mark)
    return plan


async def get_section_teacher_id(session: AsyncSession, offering_id: UUID) -> UUID:
    user_id = await _one(
        session,
        select(FacultyAssignment.user_id).where(
            FacultyAssignment.section_offering_id == offering_id,
            FacultyAssignment.role_in_course == "SECTION_TEACHER",
            FacultyAssignment.removed_at.is_(None),
        ),
    )
    if user_id is None:
        raise RuntimeError(f"No section teacher for offering {offering_id}")
    return user_id


def co_index_for(co_code: str) -> int:
    digits = "".join(ch for ch in co_code if ch.isdigit())
    return int(digits or "1")


async def seed_marks_for_offering(
    session: AsyncSession,
    offering: SectionOffering,
    course_index: int,
    section_index: int,
    enrollments: list[StudentEnrollment],
    teacher_id: UUID,
    co_code_by_id: dict[UUID, str],
    mark_plan: dict[str, list[CourseCOMarks]],
) -> None:
    for exam_type, tool_name, prefix in [
        ("MID", "Mid-term Exam", "M"),
        ("FINAL", "Final Exam", "F"),
    ]:
        for order_index, mark in enumerate(mark_plan.get(tool_name, []), start=1):
            co_code = co_code_by_id[mark.course_outcome_id]
            max_marks = _d(mark.marks)
            question = MarksheetQuestion(
                organization_id=offering.organization_id,
                section_offering_id=offering.id,
                exam_type=exam_type,
                label=f"{prefix}{order_index}",
                max_marks=max_marks,
                course_outcome_id=mark.course_outcome_id,
                order_index=order_index,
            )
            session.add(question)
            await session.flush()
            for student_index, enrollment in enumerate(enrollments, start=1):
                session.add(
                    MarksheetMark(
                        organization_id=offering.organization_id,
                        question_id=question.id,
                        student_enrollment_id=enrollment.id,
                        marks_obtained=(
                            max_marks
                            * _ratio(student_index, co_index_for(co_code), section_index, course_index)
                        ).quantize(Decimal("0.01")),
                        is_absent=False,
                        entered_by_user_id=teacher_id,
                    )
                )

    assessment_types = {
        row.name: row
        for row in (
            await session.execute(
                select(AssessmentType).where(AssessmentType.organization_id == offering.organization_id)
            )
        ).scalars().all()
    }
    for tool_name, marks in mark_plan.items():
        assessment_type = assessment_types.get(tool_name)
        if assessment_type is None:
            continue
        total_marks = sum((_d(mark.marks) for mark in marks), Decimal("0.00"))
        if total_marks <= 0:
            continue
        assessment = Assessment(
            organization_id=offering.organization_id,
            section_offering_id=offering.id,
            assessment_type_id=assessment_type.id,
            name=tool_name,
            total_marks=total_marks,
            weightage_percent=total_marks,
            status="CONFIGURED",
        )
        session.add(assessment)
        await session.flush()
        for mark in marks:
            contribution = (_d(mark.marks) / total_marks * Decimal("100")).quantize(Decimal("0.01"))
            session.add(
                AssessmentCOWeight(
                    assessment_id=assessment.id,
                    course_outcome_id=mark.course_outcome_id,
                    contribution_percent=contribution,
                )
            )
        for student_index, enrollment in enumerate(enrollments, start=1):
            obtained = Decimal("0.00")
            for mark in marks:
                co_code = co_code_by_id[mark.course_outcome_id]
                obtained += _d(mark.marks) * _ratio(
                    student_index,
                    co_index_for(co_code),
                    section_index,
                    course_index,
                )
            session.add(
                StudentMark(
                    organization_id=offering.organization_id,
                    assessment_id=assessment.id,
                    student_enrollment_id=enrollment.id,
                    marks_obtained=min(total_marks, obtained).quantize(Decimal("0.01")),
                    is_absent=False,
                    entered_by_user_id=teacher_id,
                )
            )


async def submit_result_and_end_report(
    session: AsyncSession,
    offering: SectionOffering,
    course: Course,
    section_name: str,
    teacher_id: UUID,
) -> None:
    now = datetime.now(timezone.utc)
    pub = await _one(
        session,
        select(ResultPublication).where(ResultPublication.section_offering_id == offering.id),
    )
    if pub is None:
        pub = ResultPublication(
            organization_id=offering.organization_id,
            section_offering_id=offering.id,
        )
        session.add(pub)
    pub.status = "SUBMITTED"
    pub.submitted_by_user_id = teacher_id
    pub.submitted_at = now

    marksheet = MarksheetService(session)
    grade_distribution = await marksheet.get_grade_distribution(offering.id, offering.organization_id)
    attainment = await marksheet.get_attainment(offering.id, offering.organization_id)
    co_attainment = {co.co_code: float(co.average_attainment_pct) for co in attainment.cos}
    unattained = [
        {
            "co_code": co.co_code,
            "reason": (
                f"{co.students_above_threshold}/{co.total_students} students met the "
                f"{attainment.threshold_co_score_pct}% threshold."
            ),
            "suggestion": "Provide targeted tutorials and a recovery practice task for this outcome.",
        }
        for co in attainment.cos
        if not co.is_attained
    ]
    report = await _one(
        session,
        select(CourseEndReport).where(CourseEndReport.section_offering_id == offering.id),
    )
    if report is None:
        report = CourseEndReport(
            organization_id=offering.organization_id,
            section_offering_id=offering.id,
            created_by_user_id=teacher_id,
        )
        session.add(report)
    report.grade_distribution = grade_distribution
    report.co_attainment = co_attainment
    report.unattained_co_explanations = unattained
    report.teacher_feedback = (
        f"{section_name}: {course.code} end report submitted with mixed CO/PO attainment. "
        "Follow-up support is recommended for weaker outcome bands."
    )
    report.course_drive_link = f"https://drive.google.com/drive/folders/{course.code.lower()}-{section_name.lower()}"
    report.status = "SUBMITTED"
    report.submitted_at = now


async def seed_all() -> None:
    print("[1/3] Ensuring staffing for target courses...")
    for course_code in TARGET_COURSES:
        await seed_staffing(course_code)

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        first_course, first_offerings, _, _ = await load_course_context(session, TARGET_COURSES[0])
        students_by_section = await get_existing_cse102_students_by_section(session, first_course.organization_id)
        _ = first_offerings

        print("[2/3] Enrolling existing CSE102 students and seeding marks...")
        total_sections = 0
        total_enrollments = 0
        for course_index, course_code in enumerate(TARGET_COURSES, start=1):
            course, offerings, _cos, co_code_by_id = await load_course_context(session, course_code)
            mark_plan = await load_course_mark_plan(session, offerings[0].curriculum_id, course.id)
            for section_index, offering in enumerate(offerings, start=1):
                await reset_offering(session, offering.id)
                teacher_id = await get_section_teacher_id(session, offering.id)
                enrollments = await ensure_enrollments(
                    session,
                    offering,
                    students_by_section[section_index],
                )
                await seed_marks_for_offering(
                    session,
                    offering,
                    course_index,
                    section_index,
                    enrollments,
                    teacher_id,
                    co_code_by_id,
                    mark_plan,
                )
                section = await _one(session, select(Section).where(Section.id == offering.section_id))
                await submit_result_and_end_report(
                    session,
                    offering,
                    course,
                    section.name if section else f"{course.code}-S{section_index:02d}",
                    teacher_id,
                )
                total_sections += 1
                total_enrollments += len(enrollments)
            await session.flush()

        await session.commit()
        print("[3/3] Done.")
        print(f"Courses processed: {len(TARGET_COURSES)}")
        print(f"Sections submitted: {total_sections}")
        print(f"Enrollments reused/created: {total_enrollments}")
        print(f"Students reused from {BASE_STUDENT_COURSE}: {sum(len(v) for v in students_by_section.values())}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_all())
