"""
Run: python -m scripts.finish_cse101_remaining_sections

Finishes CSE101's remaining sections (S11-S15) that seed_5_courses_10_sections
didn't touch: assigns the existing section teachers (already staffed from
original seeding), enrolls the matching CSE102-11..15 student groups, seeds
marks, and submits the result + end report for each, one section at a time.
"""

from __future__ import annotations

import asyncio
import os
import sys
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.modules.assessment.models import Student
from app.modules.curriculum.models import Course, Section, SectionOffering
from app.modules.obe.models import CourseOutcome
from scripts.seed_15_more_course_results import (
    ensure_enrollments,
    get_section_teacher_id,
    load_course_mark_plan,
    seed_marks_for_offering,
    submit_result_and_end_report,
)

ORG_ID = UUID("5b7006ed-03d0-4d19-86b9-34d63b0e298a")
REMAINING_SECTIONS = [11, 12, 13, 14, 15]


async def _one(session: AsyncSession, stmt):
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_student_group(session: AsyncSession, index: int) -> list[Student]:
    prefix = f"CSE102-{index:02d}-"
    students = (
        await session.execute(
            select(Student).where(
                Student.organization_id == ORG_ID,
                Student.student_id_number.like(f"{prefix}%"),
                Student.status == "ACTIVE",
            ).order_by(Student.student_id_number)
        )
    ).scalars().all()
    if len(students) != 20:
        raise RuntimeError(f"Expected 20 students for group {prefix}, got {len(students)}")
    return list(students)


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        course = await _one(session, select(Course).where(Course.organization_id == ORG_ID, Course.code == "CSE101", Course.status == "ACTIVE"))
        if course is None:
            raise RuntimeError("CSE101 not found")

        curriculum_id = await _one(session, select(CourseOutcome.curriculum_id).where(CourseOutcome.course_id == course.id).limit(1))
        mark_plan = await load_course_mark_plan(session, curriculum_id, course.id)
        co_code_by_id = {
            co.id: co.code
            for co in (await session.execute(select(CourseOutcome).where(CourseOutcome.course_id == course.id))).scalars().all()
        }

        for section_index in REMAINING_SECTIONS:
            section_name = f"CSE101-S{section_index:02d}"
            section = await _one(session, select(Section).where(Section.organization_id == ORG_ID, Section.name == section_name))
            if section is None:
                raise RuntimeError(f"Section not found: {section_name}")
            offering = await _one(session, select(SectionOffering).where(SectionOffering.course_id == course.id, SectionOffering.section_id == section.id))
            if offering is None:
                raise RuntimeError(f"Offering not found for {section_name}")

            teacher_id = await get_section_teacher_id(session, offering.id)
            students = await get_student_group(session, section_index)
            enrollments = await ensure_enrollments(session, offering, students)

            await seed_marks_for_offering(
                session, offering, course_index=1, section_index=section_index,
                enrollments=enrollments, teacher_id=teacher_id, co_code_by_id=co_code_by_id, mark_plan=mark_plan,
            )
            await submit_result_and_end_report(session, offering, course, section_name, teacher_id)
            await session.commit()
            print(f"{section_name}: submitted ({len(enrollments)} students)")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
