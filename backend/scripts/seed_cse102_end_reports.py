"""
Run: python -m scripts.seed_cse102_end_reports

Submits course end reports for all CSE102 sections using the already-seeded
marksheet data, grade distribution, and CO attainment previews.
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.modules.assessment.models import CourseEndReport
from app.modules.assessment.schemas import CourseEndReportSubmit
from app.modules.assessment.service import CourseEndReportService, MarksheetService
from app.modules.curriculum.models import Course, FacultyAssignment, Section, SectionOffering

COURSE_CODE = "CSE102"


async def _one(session, stmt):
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def seed_end_reports() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        course = await _one(
            session,
            select(Course).where(Course.code == COURSE_CODE, Course.status == "ACTIVE"),
        )
        if course is None:
            raise RuntimeError(f"{COURSE_CODE} not found.")

        offering_rows = (
            await session.execute(
                select(SectionOffering, Section.name)
                .join(Section, Section.id == SectionOffering.section_id)
                .where(SectionOffering.course_id == course.id, Section.name.like(f"{COURSE_CODE}-S%"))
                .order_by(Section.name)
            )
        ).all()
        if len(offering_rows) != 15:
            raise RuntimeError(f"Expected 15 {COURSE_CODE} section offerings.")

        marksheet_service = MarksheetService(session)
        report_service = CourseEndReportService(session)
        submitted = 0

        for offering, section_name in offering_rows:
            teacher_id = await _one(
                session,
                select(FacultyAssignment.user_id).where(
                    FacultyAssignment.section_offering_id == offering.id,
                    FacultyAssignment.role_in_course == "SECTION_TEACHER",
                    FacultyAssignment.removed_at.is_(None),
                ),
            )
            if teacher_id is None:
                raise RuntimeError(f"No section teacher for {section_name}")

            existing = await _one(
                session,
                select(CourseEndReport).where(CourseEndReport.section_offering_id == offering.id),
            )
            if existing is not None and existing.status == "SUBMITTED":
                existing.status = "DRAFT"
                existing.submitted_at = None
                await session.flush()

            grade_distribution = await marksheet_service.get_grade_distribution(
                offering.id,
                offering.organization_id,
            )
            attainment = await marksheet_service.get_attainment(
                offering.id,
                offering.organization_id,
            )

            co_attainment = {
                co.co_code: float(co.average_attainment_pct)
                for co in attainment.cos
            }
            unattained = [
                {
                    "co_code": co.co_code,
                    "reason": (
                        f"{co.students_above_threshold}/{co.total_students} students met the "
                        f"{attainment.threshold_co_score_pct}% threshold."
                    ),
                    "suggestion": (
                        "Add targeted revision, extra worked examples, and a formative recovery "
                        "task before the next assessment cycle."
                    ),
                }
                for co in attainment.cos
                if not co.is_attained
            ]

            body = CourseEndReportSubmit(
                grade_distribution=grade_distribution,
                co_attainment=co_attainment,
                unattained_co_explanations=unattained,
                teacher_feedback=(
                    f"{section_name}: End report submitted with varied attainment outcomes. "
                    "Students performing below threshold need additional tutorial support."
                ),
                course_drive_link=f"https://drive.google.com/drive/folders/{COURSE_CODE.lower()}-{section_name.lower()}",
            )
            await report_service.submit(offering.id, body, offering.organization_id, teacher_id)
            submitted += 1

        print("\nCSE102 end reports submitted successfully.")
        print(f"Course: {course.code} - {course.title}")
        print(f"Submitted end reports: {submitted}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_end_reports())
