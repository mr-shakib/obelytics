"""
Run: python -m scripts.seed_5_courses_10_sections

Seeds 10 sections each for 5 under-staffed courses (CSE101, CSE103, CSE401,
CSE402, "CSE 311"), reusing each course's existing module leader and an
existing student cohort appropriate to its batch:

  - CSE101 / CSE103 run on "Demo Batch 2026" -> reuses 10 of the existing
    CSE102-0X-* student groups (20 students/section).
  - CSE401 / CSE402 / "CSE 311" run on the "CSE 71" batch -> splits its 100
    students into 10 groups of 10, reused identically across all three so the
    same students' PO attainment is comparable across courses.

For every section: creates/reuses the Section + SectionOffering, creates a
dedicated Section Teacher, enrolls the cohort, seeds MID/FINAL marks with a
deliberate spread (some students/COs clear the attainment threshold, some
don't), then submits the result publication and the course end report (with
justifications for any unattained COs) ONE SECTION AT A TIME.
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
from app.core.security import hash_password
from app.modules.assessment.models import Student
from app.modules.curriculum.models import (
    Course,
    FacultyAssignment,
    Section,
    SectionOffering,
)
from app.modules.curriculum.schemas import FacultyAssignmentCreate
from app.modules.curriculum.service import FacultyAssignmentService
from app.modules.iam.models import PasswordCredential, Role, User, UserRoleAssignment
from app.modules.obe.models import CourseOutcome
from app.modules.org.models import Department, Program
from scripts.seed_15_more_course_results import (
    co_index_for,  # noqa: F401 (re-exported for clarity)
    ensure_enrollments,
    get_section_teacher_id,
    load_course_mark_plan,
    seed_marks_for_offering,
    submit_result_and_end_report,
)

DEFAULT_PASSWORD = "Teacher@123"
SECTION_COUNT = 10
ORG_ID = UUID("5b7006ed-03d0-4d19-86b9-34d63b0e298a")

DEMO_BATCH_ID = UUID("230a20e1-d266-4127-ad97-a8b775b7cc3c")
CSE71_BATCH_ID = UUID("f3ac22e7-0efe-40f8-b6a4-8cb9c5c8d374")
SPRING_2026 = UUID("731925f1-d681-42f5-850d-bdab29328657")
SPRING_2029 = UUID("a93c121d-9e0d-490e-b63b-d21a12aa2c29")
FALL_2029 = UUID("0b02e28e-39d4-4bbe-9146-2fe339b1cd11")

# course_code -> (batch_id, academic_term_id, student_pool) ; matches each
# course's EXISTING module leader assignment scope exactly.
COURSE_PLAN = {
    "CSE101": (DEMO_BATCH_ID, SPRING_2026, "demo"),
    "CSE103": (DEMO_BATCH_ID, SPRING_2026, "demo"),
    "CSE401": (CSE71_BATCH_ID, SPRING_2029, "cse71"),
    "CSE402": (CSE71_BATCH_ID, FALL_2029, "cse71"),
    "CSE 311": (CSE71_BATCH_ID, SPRING_2026, "cse71"),
}


async def _one(session: AsyncSession, stmt):
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_demo_batch_student_groups(session: AsyncSession) -> dict[int, list[Student]]:
    groups: dict[int, list[Student]] = {}
    for i in range(1, SECTION_COUNT + 1):
        prefix = f"CSE102-{i:02d}-"
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
        groups[i] = list(students)
    return groups


async def get_cse71_student_groups(session: AsyncSession) -> dict[int, list[Student]]:
    all_students = (
        await session.execute(
            select(Student)
            .where(Student.organization_id == ORG_ID, Student.batch_id == CSE71_BATCH_ID, Student.status == "ACTIVE")
            .order_by(Student.student_id_number)
        )
    ).scalars().all()
    if len(all_students) != 100:
        raise RuntimeError(f"Expected 100 CSE 71 students, got {len(all_students)}")
    groups: dict[int, list[Student]] = {}
    for i in range(SECTION_COUNT):
        groups[i + 1] = list(all_students[i * 10:(i + 1) * 10])
    return groups


async def ensure_department_id(session: AsyncSession) -> UUID | None:
    dept = await _one(session, select(Department).where(Department.organization_id == ORG_ID, Department.status == "ACTIVE").limit(1))
    return dept.id if dept else None


async def ensure_teacher(session: AsyncSession, org_id: UUID, department_id: UUID | None, course_code: str, index: int) -> User:
    safe_code = course_code.replace(" ", "")
    email = f"teacher.{safe_code.lower()}.s{index:02d}@obelytics.local"
    full_name = f"{course_code} Section Teacher {index:02d}"
    user = await _one(session, select(User).where(User.email == email))
    if user is None:
        user = User(
            organization_id=org_id,
            email=email,
            full_name=full_name,
            first_name=full_name.split()[0],
            last_name="Teacher",
            employee_id=f"ST-{safe_code}-{index:02d}",
            faculty_type="FULL_TIME",
            department_id=department_id,
            designation="Section Teacher",
            qualification="MSc in Computer Science",
            experience_years=4,
            status="ACTIVE",
        )
        session.add(user)
        await session.flush()

        session.add(PasswordCredential(user_id=user.id, hashed_password=hash_password(DEFAULT_PASSWORD), must_change_password=False))

        role = await _one(session, select(Role).where(Role.organization_id == org_id, Role.name == "Section Teacher"))
        if role is not None:
            session.add(UserRoleAssignment(user_id=user.id, role_id=role.id, scope_type="GLOBAL", scope_id=None, assigned_by=None))
    return user


async def ensure_section_and_offering(
    session: AsyncSession, org_id: UUID, curriculum_id: UUID, batch_id: UUID, term_id: UUID, course: Course, index: int
) -> tuple[Section, SectionOffering]:
    section_name = f"{course.code}-S{index:02d}"
    section = await _one(session, select(Section).where(Section.organization_id == org_id, Section.name == section_name))
    if section is None:
        section = Section(organization_id=org_id, name=section_name, capacity=40)
        session.add(section)
        await session.flush()

    offering = await _one(
        session,
        select(SectionOffering).where(
            SectionOffering.batch_id == batch_id,
            SectionOffering.course_id == course.id,
            SectionOffering.academic_term_id == term_id,
            SectionOffering.section_id == section.id,
        ),
    )
    if offering is None:
        offering = SectionOffering(
            organization_id=org_id,
            curriculum_id=curriculum_id,
            batch_id=batch_id,
            course_id=course.id,
            academic_term_id=term_id,
            section_id=section.id,
            status="UPCOMING",
        )
        session.add(offering)
        await session.flush()
    return section, offering


async def ensure_section_teacher_assignment(session: AsyncSession, org_id: UUID, offering: SectionOffering, teacher: User) -> None:
    existing = await _one(
        session,
        select(FacultyAssignment).where(
            FacultyAssignment.section_offering_id == offering.id,
            FacultyAssignment.user_id == teacher.id,
            FacultyAssignment.role_in_course == "SECTION_TEACHER",
            FacultyAssignment.removed_at.is_(None),
        ),
    )
    if existing is not None:
        return
    service = FacultyAssignmentService(session)
    await service.assign(
        FacultyAssignmentCreate(section_offering_id=offering.id, user_id=teacher.id, role_in_course="SECTION_TEACHER"),
        org_id,
    )


async def seed_all() -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        department_id = await ensure_department_id(session)
        demo_groups = await get_demo_batch_student_groups(session)
        cse71_groups = await get_cse71_student_groups(session)
        await session.commit()

        total_sections = 0
        total_enrollments = 0

        for course_code, (batch_id, term_id, pool) in COURSE_PLAN.items():
            course = await _one(session, select(Course).where(Course.organization_id == ORG_ID, Course.code == course_code, Course.status == "ACTIVE"))
            if course is None:
                raise RuntimeError(f"Course not found: {course_code}")

            # curriculum_id: reuse whatever curriculum the course's existing course_outcomes/mapping already use
            curriculum_row = await _one(session, select(CourseOutcome.curriculum_id).where(CourseOutcome.course_id == course.id).limit(1))
            if curriculum_row is None:
                raise RuntimeError(f"No curriculum found via course_outcomes for {course_code}")
            crs_curriculum_id = curriculum_row

            mark_plan = await load_course_mark_plan(session, crs_curriculum_id, course.id)
            student_groups = demo_groups if pool == "demo" else cse71_groups

            print(f"\n=== {course_code} ===")
            for section_index in range(1, SECTION_COUNT + 1):
                section, offering = await ensure_section_and_offering(
                    session, ORG_ID, crs_curriculum_id, batch_id, term_id, course, section_index
                )
                teacher = await ensure_teacher(session, ORG_ID, department_id, course_code, section_index)
                await session.flush()
                await ensure_section_teacher_assignment(session, ORG_ID, offering, teacher)
                await session.commit()

                teacher_id = await get_section_teacher_id(session, offering.id)
                enrollments = await ensure_enrollments(session, offering, student_groups[section_index])

                co_code_by_id = {
                    co.id: co.code
                    for co in (
                        await session.execute(select(CourseOutcome).where(CourseOutcome.course_id == course.id))
                    ).scalars().all()
                }

                await seed_marks_for_offering(
                    session, offering, course_index=hash(course_code) % 97, section_index=section_index,
                    enrollments=enrollments, teacher_id=teacher_id, co_code_by_id=co_code_by_id, mark_plan=mark_plan,
                )
                await submit_result_and_end_report(session, offering, course, section.name, teacher_id)
                await session.commit()

                total_sections += 1
                total_enrollments += len(enrollments)
                print(f"  {section.name}: submitted ({len(enrollments)} students)")

        print("\nDone.")
        print(f"Sections submitted: {total_sections}")
        print(f"Enrollments: {total_enrollments}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_all())
