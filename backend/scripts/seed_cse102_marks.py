"""
Run: python -m scripts.seed_cse102_marks

Seeds CSE102 theory-course assessment data for every section offering:
  - 20 students per section, enrolled into the section
  - MID and FINAL marksheet questions mapped to COs
  - marksheet marks entered by each assigned section teacher
  - normal assessment marks for attendance, presentation, quiz, assignment,
    mid-term, and final totals
  - result publication submitted by each section teacher

The mark pattern intentionally mixes high, medium, and weak students so some
students attain CO/PO thresholds and some do not.
"""

from __future__ import annotations

import asyncio
import os
import sys
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
    MarksheetMark,
    MarksheetQuestion,
    ResultPublication,
    Student,
    StudentEnrollment,
    StudentMark,
)
from app.modules.curriculum.models import Course, FacultyAssignment, Section, SectionOffering
from app.modules.obe.models import CourseOutcome
from app.modules.org.models import Organization
from app.modules.ref_data.models import AssessmentType

_ = Organization

COURSE_CODE = "CSE102"
STUDENTS_PER_SECTION = 20

QUESTION_PLANS = {
    "MID": [
        ("M1", "CO1", Decimal("5.00")),
        ("M2", "CO2", Decimal("5.00")),
        ("M3", "CO3", Decimal("10.00")),
        ("M4", "CO4", Decimal("5.00")),
    ],
    "FINAL": [
        ("F1", "CO1", Decimal("5.00")),
        ("F2", "CO2", Decimal("10.00")),
        ("F3", "CO3", Decimal("10.00")),
        ("F4", "CO4", Decimal("15.00")),
    ],
}

ASSESSMENT_PLANS = [
    ("Mid-term Exam", Decimal("25.00"), {"CO1": 5, "CO2": 5, "CO3": 10, "CO4": 5}),
    ("Final Exam", Decimal("40.00"), {"CO1": 5, "CO2": 10, "CO3": 10, "CO4": 15}),
    ("Attendance", Decimal("7.00"), {"CO1": 2, "CO2": 2, "CO3": 2, "CO4": 1}),
    ("Presentation", Decimal("8.00"), {"CO2": 2, "CO3": 3, "CO4": 3}),
    ("Quiz", Decimal("15.00"), {"CO1": 3, "CO2": 4, "CO3": 4, "CO4": 4}),
    ("Assignment", Decimal("5.00"), {"CO1": 1, "CO2": 1, "CO3": 1, "CO4": 2}),
]


async def _one(session: AsyncSession, stmt):
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _ratio(student_index: int, co_code: str, section_index: int) -> Decimal:
    """Deterministic score ratios with mixed attainment outcomes."""
    wobble = Decimal(((section_index + student_index) % 5) - 2) / Decimal("100")
    if student_index <= 6:
        base = {
            "CO1": Decimal("0.90"),
            "CO2": Decimal("0.86"),
            "CO3": Decimal("0.82"),
            "CO4": Decimal("0.78"),
        }[co_code]
    elif student_index <= 14:
        base = {
            "CO1": Decimal("0.72"),
            "CO2": Decimal("0.64"),
            "CO3": Decimal("0.54"),
            "CO4": Decimal("0.46"),
        }[co_code]
    else:
        base = {
            "CO1": Decimal("0.48"),
            "CO2": Decimal("0.42"),
            "CO3": Decimal("0.34"),
            "CO4": Decimal("0.28"),
        }[co_code]
    ratio = base + wobble
    return max(Decimal("0.00"), min(Decimal("0.98"), ratio))


def _question_mark(max_marks: Decimal, student_index: int, co_code: str, section_index: int) -> Decimal:
    return (max_marks * _ratio(student_index, co_code, section_index)).quantize(Decimal("0.01"))


def _assessment_mark(
    total_marks: Decimal,
    co_marks: dict[str, int],
    student_index: int,
    section_index: int,
) -> Decimal:
    obtained = Decimal("0")
    for co_code, marks in co_marks.items():
        obtained += Decimal(str(marks)) * _ratio(student_index, co_code, section_index)
    return min(total_marks, obtained).quantize(Decimal("0.01"))


async def resolve_context(session: AsyncSession) -> tuple[Course, list[SectionOffering], dict[str, CourseOutcome]]:
    course = await _one(
        session,
        select(Course).where(Course.code == COURSE_CODE, Course.status == "ACTIVE"),
    )
    if course is None:
        raise RuntimeError(f"{COURSE_CODE} not found. Seed demo courses first.")

    offerings = (
        await session.execute(
            select(SectionOffering)
            .join(Section, Section.id == SectionOffering.section_id)
            .where(SectionOffering.course_id == course.id, Section.name.like(f"{COURSE_CODE}-S%"))
            .order_by(Section.name)
        )
    ).scalars().all()
    if len(offerings) != 15:
        raise RuntimeError(f"Expected 15 {COURSE_CODE} section offerings. Run seed_course_staffing first.")

    cos = (
        await session.execute(
            select(CourseOutcome)
            .where(CourseOutcome.course_id == course.id)
            .order_by(CourseOutcome.code)
        )
    ).scalars().all()
    co_by_code = {co.code: co for co in cos}
    missing = {"CO1", "CO2", "CO3", "CO4"} - set(co_by_code)
    if missing:
        raise RuntimeError(f"Missing course outcomes for {COURSE_CODE}: {sorted(missing)}")

    return course, list(offerings), co_by_code


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
        raise RuntimeError(f"No section teacher assigned for offering {offering_id}")
    return user_id


async def ensure_students_and_enrollments(
    session: AsyncSession,
    offering: SectionOffering,
    section_index: int,
) -> list[StudentEnrollment]:
    enrollments: list[StudentEnrollment] = []
    for student_index in range(1, STUDENTS_PER_SECTION + 1):
        sid = f"{COURSE_CODE}-{section_index:02d}-{student_index:03d}"
        student = await _one(
            session,
            select(Student).where(
                Student.organization_id == offering.organization_id,
                Student.student_id_number == sid,
                Student.status != "WITHDRAWN",
            ),
        )
        if student is None:
            student = Student(
                organization_id=offering.organization_id,
                student_id_number=sid,
                full_name=f"{COURSE_CODE} Student S{section_index:02d}-{student_index:03d}",
                email=f"{sid.lower()}@student.obelytics.local",
                batch_id=offering.batch_id,
                status="ACTIVE",
            )
            session.add(student)
            await session.flush()
        else:
            student.batch_id = offering.batch_id
            student.status = "ACTIVE"

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


async def reset_offering_assessment_data(session: AsyncSession, offering_id: UUID) -> None:
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


async def seed_questions_and_marks(
    session: AsyncSession,
    offering: SectionOffering,
    co_by_code: dict[str, CourseOutcome],
    enrollments: list[StudentEnrollment],
    teacher_id: UUID,
    section_index: int,
) -> None:
    for exam_type, plan in QUESTION_PLANS.items():
        for order_index, (label, co_code, max_marks) in enumerate(plan, start=1):
            question = MarksheetQuestion(
                organization_id=offering.organization_id,
                section_offering_id=offering.id,
                exam_type=exam_type,
                label=label,
                max_marks=max_marks,
                course_outcome_id=co_by_code[co_code].id,
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
                        marks_obtained=_question_mark(max_marks, student_index, co_code, section_index),
                        is_absent=False,
                        entered_by_user_id=teacher_id,
                    )
                )


async def seed_assessment_totals(
    session: AsyncSession,
    offering: SectionOffering,
    co_by_code: dict[str, CourseOutcome],
    enrollments: list[StudentEnrollment],
    teacher_id: UUID,
    section_index: int,
) -> None:
    assessment_types = {
        row.name: row
        for row in (
            await session.execute(
                select(AssessmentType).where(AssessmentType.organization_id == offering.organization_id)
            )
        ).scalars().all()
    }

    for name, total_marks, co_marks in ASSESSMENT_PLANS:
        assessment_type = assessment_types.get(name)
        if assessment_type is None:
            raise RuntimeError(f"Assessment type missing: {name}")

        assessment = Assessment(
            organization_id=offering.organization_id,
            section_offering_id=offering.id,
            assessment_type_id=assessment_type.id,
            name=name,
            total_marks=total_marks,
            weightage_percent=total_marks,
            status="CONFIGURED",
        )
        session.add(assessment)
        await session.flush()

        for co_code, marks in co_marks.items():
            contribution = (Decimal(str(marks)) / total_marks * Decimal("100")).quantize(Decimal("0.01"))
            session.add(
                AssessmentCOWeight(
                    assessment_id=assessment.id,
                    course_outcome_id=co_by_code[co_code].id,
                    contribution_percent=contribution,
                )
            )

        for student_index, enrollment in enumerate(enrollments, start=1):
            session.add(
                StudentMark(
                    organization_id=offering.organization_id,
                    assessment_id=assessment.id,
                    student_enrollment_id=enrollment.id,
                    marks_obtained=_assessment_mark(total_marks, co_marks, student_index, section_index),
                    is_absent=False,
                    entered_by_user_id=teacher_id,
                )
            )


async def submit_result(session: AsyncSession, offering: SectionOffering, teacher_id: UUID) -> None:
    pub = await _one(
        session,
        select(ResultPublication).where(ResultPublication.section_offering_id == offering.id),
    )
    if pub is None:
        pub = ResultPublication(
            organization_id=offering.organization_id,
            section_offering_id=offering.id,
            status="SUBMITTED",
            submitted_by_user_id=teacher_id,
            submitted_at=datetime.now(timezone.utc),
        )
        session.add(pub)
    else:
        pub.status = "SUBMITTED"
        pub.submitted_by_user_id = teacher_id
        pub.submitted_at = datetime.now(timezone.utc)


async def seed_marks() -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        course, offerings, co_by_code = await resolve_context(session)
        total_students = 0
        for section_index, offering in enumerate(offerings, start=1):
            teacher_id = await get_section_teacher_id(session, offering.id)
            await reset_offering_assessment_data(session, offering.id)
            enrollments = await ensure_students_and_enrollments(session, offering, section_index)
            await seed_questions_and_marks(
                session, offering, co_by_code, enrollments, teacher_id, section_index
            )
            await seed_assessment_totals(
                session, offering, co_by_code, enrollments, teacher_id, section_index
            )
            await submit_result(session, offering, teacher_id)
            total_students += len(enrollments)

        await session.commit()
        print("\nCSE102 marks seeded successfully.")
        print(f"Course: {course.code} - {course.title}")
        print(f"Sections submitted: {len(offerings)}")
        print(f"Students enrolled: {total_students}")
        print("MID questions: 25 marks total mapped to CO1-CO4")
        print("FINAL questions: 40 marks total mapped to CO1-CO4")
        print("Other tools: Attendance 7, Presentation 8, Quiz 15, Assignment 5")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_marks())
