"""
Run: python -m scripts.fix_marks_distribution

The 5-student-per-section marks seeded by seed_9_courses_10_sections used a
band function tuned for 20-student sections, so every student landed in the
"top band" and nothing ever missed a CO threshold. This resets and reseeds
marks for the same 90 sections with a band function calibrated for 5 students
(one strong, one good, one borderline, two weak) so some COs attain and some
don't per section, and re-submits results + end reports.
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
from app.modules.curriculum.models import Course, FacultyAssignment, Section, SectionOffering
from app.modules.obe.models import CourseOutcome
import scripts.seed_15_more_course_results as base
from scripts.seed_15_more_course_results import (
    _d,
    get_section_teacher_id,
    load_course_mark_plan,
    reset_offering,
    seed_marks_for_offering,
    submit_result_and_end_report,
)
from scripts.seed_9_courses_10_sections import COURSE_CODES, FLAT_TOOLS, TOOL_TOTALS, seed_flat_assessment

ORG_ID = UUID("5b7006ed-03d0-4d19-86b9-34d63b0e298a")
CURRICULUM_ID = UUID("a8c8f7aa-cbfa-4492-8719-01ab5f4de8d4")


def ratio_5(student_index: int, co_index: int, section_index: int, course_index: int) -> Decimal:
    """Calibrated for 5-student sections: one strong, one good, one borderline,
    two weak performer. Later COs (higher co_index) drift down for everyone
    but the top student, so some COs clear the 50%-of-students bar and some
    don't — varies a bit by section/course via the wobble term."""
    wobble = Decimal(((section_index + course_index + student_index + co_index) % 7) - 3) / Decimal("100")
    co_drop = Decimal(co_index - 1)
    if student_index == 1:
        base_val = Decimal("0.90") - co_drop * Decimal("0.03")
    elif student_index == 2:
        base_val = Decimal("0.75") - co_drop * Decimal("0.08")
    elif student_index == 3:
        base_val = Decimal("0.58") - co_drop * Decimal("0.10")
    elif student_index == 4:
        base_val = Decimal("0.42") - co_drop * Decimal("0.08")
    else:
        base_val = Decimal("0.30") - co_drop * Decimal("0.05")
    return max(Decimal("0.05"), min(Decimal("0.98"), base_val + wobble))


async def _one(session: AsyncSession, stmt):
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def fix_all() -> None:
    # Patch the shared ratio function used internally by seed_marks_for_offering.
    base._ratio = ratio_5

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        total = 0
        for course_index, course_code in enumerate(COURSE_CODES, start=1):
            course = await _one(session, select(Course).where(Course.organization_id == ORG_ID, Course.code == course_code, Course.status == "ACTIVE"))
            mark_plan = await load_course_mark_plan(session, CURRICULUM_ID, course.id)
            co_code_by_id = {
                co.id: co.code
                for co in (await session.execute(select(CourseOutcome).where(CourseOutcome.course_id == course.id))).scalars().all()
            }

            offerings = (
                await session.execute(
                    select(SectionOffering)
                    .join(Section, Section.id == SectionOffering.section_id)
                    .where(SectionOffering.course_id == course.id, Section.name.like(f"{course_code}-S%"))
                    .order_by(Section.name)
                )
            ).scalars().all()

            print(f"\n=== {course_code} ({len(offerings)} sections) ===")
            for section_index, offering in enumerate(offerings, start=1):
                teacher_id = await get_section_teacher_id(session, offering.id)
                await reset_offering(session, offering.id)
                await session.flush()

                from app.modules.assessment.models import StudentEnrollment
                enrollments = (
                    await session.execute(
                        select(StudentEnrollment).where(StudentEnrollment.section_offering_id == offering.id, StudentEnrollment.status == "ACTIVE")
                    )
                ).scalars().all()

                await seed_marks_for_offering(
                    session, offering, course_index=course_index, section_index=section_index,
                    enrollments=enrollments, teacher_id=teacher_id, co_code_by_id=co_code_by_id, mark_plan=mark_plan,
                )
                for tool_name in FLAT_TOOLS:
                    await seed_flat_assessment(
                        session, offering, tool_name, _d(TOOL_TOTALS[tool_name]),
                        enrollments, teacher_id, course_index, section_index,
                    )

                section = await _one(session, select(Section).where(Section.id == offering.section_id))
                await submit_result_and_end_report(session, offering, course, section.name, teacher_id)
                await session.commit()
                total += 1
                print(f"  {section.name}: resubmitted ({len(enrollments)} students)")

        print(f"\nDone. Sections resubmitted: {total}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix_all())
