"""
Run: python -m scripts.resubmit_5_courses_after_mapping_change

Re-submits every section result + end report for CSE101, CSE103, CSE401,
CSE402, and "CSE 311" (56 sections total), one at a time, so the stored
grade distribution / CO attainment snapshot reflects the current state after
the CO-PO mapping change (CO2 added as a secondary contributor to PO1).
Marks are untouched -- this only re-runs the submit step.
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
from app.modules.curriculum.models import Course, Section, SectionOffering
from scripts.seed_15_more_course_results import get_section_teacher_id, submit_result_and_end_report

ORG_ID = UUID("5b7006ed-03d0-4d19-86b9-34d63b0e298a")
TARGET_COURSES = ["CSE101", "CSE103", "CSE401", "CSE402", "CSE 311"]


async def _one(session: AsyncSession, stmt):
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        total = 0
        for course_code in TARGET_COURSES:
            course = await _one(session, select(Course).where(Course.organization_id == ORG_ID, Course.code == course_code, Course.status == "ACTIVE"))
            if course is None:
                raise RuntimeError(f"Course not found: {course_code}")

            offerings = (
                await session.execute(
                    select(SectionOffering, Section)
                    .join(Section, Section.id == SectionOffering.section_id)
                    .where(SectionOffering.course_id == course.id)
                    .order_by(Section.name)
                )
            ).all()

            print(f"=== {course_code} ({len(offerings)} sections) ===")
            for offering, section in offerings:
                teacher_id = await get_section_teacher_id(session, offering.id)
                await submit_result_and_end_report(session, offering, course, section.name, teacher_id)
                await session.commit()
                total += 1
                print(f"  {section.name}: resubmitted")

        print(f"\nDone. Resubmitted {total} sections.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
