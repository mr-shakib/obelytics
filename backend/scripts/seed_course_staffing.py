"""
Run: python -m scripts.seed_course_staffing [--course-code CSE102]

Creates staffing data for one course offering:
  - one Module Leader user and assignment
  - 15 sections and section offerings
  - 15 Section Teacher users and assignments

Safe to re-run: reuses users, sections, batch, academic terms, and offerings;
replaces active module-leader and section-teacher assignments for the selected
course offering.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import hash_password
from app.modules.curriculum.models import (
    AcademicTerm,
    Batch,
    BatchTermCalendar,
    Course,
    Curriculum,
    CurriculumCourseSlot,
    CurriculumTermDefinition,
    FacultyAssignment,
    ModuleLeaderAssignment,
    Section,
    SectionOffering,
)
from app.modules.curriculum.schemas import FacultyAssignmentCreate, ModuleLeaderAssignmentCreate
from app.modules.curriculum.service import FacultyAssignmentService, ModuleLeaderAssignmentService
from app.modules.iam.models import PasswordCredential, Role, User, UserRoleAssignment
from app.modules.org.models import Department, Organization, Program

DEFAULT_PASSWORD = "Teacher@123"
DEFAULT_BATCH_NAME = "Demo Batch 2026"
SECTION_COUNT = 15


async def _one(session: AsyncSession, stmt):
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def resolve_org(session: AsyncSession, org_id: UUID | None) -> Organization:
    stmt = select(Organization)
    if org_id is not None:
        stmt = stmt.where(Organization.id == org_id)
    else:
        stmt = stmt.order_by(Organization.created_at).limit(1)
    org = await _one(session, stmt)
    if org is None:
        raise RuntimeError("No organization found. Seed organization/superadmin first.")
    return org


async def resolve_course_context(
    session: AsyncSession,
    org_id: UUID,
    course_code: str,
    curriculum_id: UUID | None,
) -> tuple[Course, Curriculum, CurriculumTermDefinition]:
    course = await _one(
        session,
        select(Course).where(
            Course.organization_id == org_id,
            Course.code == course_code,
            Course.status == "ACTIVE",
        ),
    )
    if course is None:
        raise RuntimeError(f"Active course not found: {course_code}")

    stmt = (
        select(CurriculumCourseSlot, Curriculum, CurriculumTermDefinition)
        .join(Curriculum, Curriculum.id == CurriculumCourseSlot.curriculum_id)
        .join(
            CurriculumTermDefinition,
            CurriculumTermDefinition.id == CurriculumCourseSlot.curriculum_term_definition_id,
        )
        .where(
            Curriculum.organization_id == org_id,
            CurriculumCourseSlot.course_id == course.id,
            Curriculum.status.in_(["DRAFT", "ACTIVE"]),
        )
        .order_by(Curriculum.created_at.desc())
    )
    if curriculum_id is not None:
        stmt = stmt.where(Curriculum.id == curriculum_id)

    result = await session.execute(stmt.limit(1))
    row = result.one_or_none()
    if row is None:
        raise RuntimeError(f"No curriculum slot found for {course_code}. Seed demo courses first.")
    _slot, curriculum, term_def = row
    return course, curriculum, term_def


async def ensure_batch_and_term(
    session: AsyncSession,
    org_id: UUID,
    curriculum: Curriculum,
    term_number: int,
) -> tuple[Batch, AcademicTerm]:
    batch = await _one(
        session,
        select(Batch).where(Batch.curriculum_id == curriculum.id, Batch.name == DEFAULT_BATCH_NAME),
    )
    if batch is None:
        batch = Batch(
            organization_id=org_id,
            curriculum_id=curriculum.id,
            name=DEFAULT_BATCH_NAME,
            intake_year=2026,
            start_date=date(2026, 1, 1),
            term_system="SEMESTER",
            num_semesters=8,
            status="ACTIVE",
        )
        session.add(batch)
        await session.flush()
        await session.refresh(batch)

    calendar = await _one(
        session,
        select(BatchTermCalendar).where(
            BatchTermCalendar.batch_id == batch.id,
            BatchTermCalendar.term_number == term_number,
        ),
    )
    if calendar is not None:
        term = await _one(session, select(AcademicTerm).where(AcademicTerm.id == calendar.academic_term_id))
        if term is None:
            raise RuntimeError("Batch calendar references a missing academic term.")
        return batch, term

    season = "SPRING" if term_number % 2 == 1 else "FALL"
    year = 2026 + ((term_number - 1) // 2)
    start = date(year, 1, 1) if season == "SPRING" else date(year, 7, 1)
    end = date(year, 6, 30) if season == "SPRING" else date(year, 12, 31)
    term = await _one(
        session,
        select(AcademicTerm).where(
            AcademicTerm.organization_id == org_id,
            AcademicTerm.year == year,
            AcademicTerm.season == season,
        ),
    )
    if term is None:
        term = AcademicTerm(
            organization_id=org_id,
            name=f"{season.capitalize()} {year}",
            year=year,
            season=season,
            start_date=start,
            end_date=end,
            status="UPCOMING",
        )
        session.add(term)
        await session.flush()

    session.add(
        BatchTermCalendar(
            batch_id=batch.id,
            term_number=term_number,
            academic_term_id=term.id,
        )
    )
    await session.flush()
    return batch, term


async def get_department_id(session: AsyncSession, org_id: UUID, curriculum: Curriculum) -> UUID | None:
    row = (await session.execute(select(Program.department_id).where(Program.id == curriculum.program_id))).first()
    if row:
        return row[0]

    dept = await _one(
        session,
        select(Department).where(Department.organization_id == org_id, Department.status == "ACTIVE").limit(1),
    )
    return dept.id if dept else None


async def ensure_user(
    session: AsyncSession,
    org_id: UUID,
    email: str,
    full_name: str,
    employee_id: str,
    department_id: UUID | None,
    designation: str,
) -> User:
    email = email.lower()
    user = await _one(session, select(User).where(User.email == email))
    if user is None:
        user = User(
            organization_id=org_id,
            email=email,
            full_name=full_name,
            first_name=full_name.split()[0],
            last_name=full_name.split()[-1],
            employee_id=employee_id,
            faculty_type="FULL_TIME",
            department_id=department_id,
            designation=designation,
            qualification="MSc in Computer Science",
            experience_years=5,
            status="ACTIVE",
        )
        session.add(user)
        await session.flush()
    else:
        user.organization_id = org_id
        user.full_name = full_name
        user.employee_id = user.employee_id or employee_id
        user.department_id = user.department_id or department_id
        user.designation = designation
        user.status = "ACTIVE"

    credential = await _one(
        session,
        select(PasswordCredential).where(PasswordCredential.user_id == user.id),
    )
    if credential is None:
        session.add(
            PasswordCredential(
                user_id=user.id,
                hashed_password=hash_password(DEFAULT_PASSWORD),
                must_change_password=False,
            )
        )
    return user


async def ensure_global_role(session: AsyncSession, user: User, org_id: UUID, role_name: str) -> None:
    role = await _one(
        session,
        select(Role).where(Role.organization_id == org_id, Role.name == role_name),
    )
    if role is None:
        raise RuntimeError(f"Role not found: {role_name}. Run seed_superadmin first.")

    existing = await _one(
        session,
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user.id,
            UserRoleAssignment.role_id == role.id,
            UserRoleAssignment.scope_type == "GLOBAL",
            UserRoleAssignment.scope_id.is_(None),
            UserRoleAssignment.removed_at.is_(None),
        ),
    )
    if existing is None:
        session.add(
            UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                scope_type="GLOBAL",
                scope_id=None,
                assigned_by=None,
            )
        )


async def ensure_sections_and_offerings(
    session: AsyncSession,
    org_id: UUID,
    curriculum: Curriculum,
    batch: Batch,
    term: AcademicTerm,
    course: Course,
) -> list[tuple[Section, SectionOffering]]:
    pairs: list[tuple[Section, SectionOffering]] = []
    for index in range(1, SECTION_COUNT + 1):
        section_name = f"{course.code}-S{index:02d}"
        section = await _one(
            session,
            select(Section).where(Section.organization_id == org_id, Section.name == section_name),
        )
        if section is None:
            section = Section(organization_id=org_id, name=section_name, capacity=40)
            session.add(section)
            await session.flush()

        offering = await _one(
            session,
            select(SectionOffering).where(
                SectionOffering.batch_id == batch.id,
                SectionOffering.course_id == course.id,
                SectionOffering.academic_term_id == term.id,
                SectionOffering.section_id == section.id,
            ),
        )
        if offering is None:
            offering = SectionOffering(
                organization_id=org_id,
                curriculum_id=curriculum.id,
                batch_id=batch.id,
                course_id=course.id,
                academic_term_id=term.id,
                section_id=section.id,
                status="UPCOMING",
            )
            session.add(offering)
            await session.flush()
        pairs.append((section, offering))
    return pairs


async def replace_module_leader(
    session: AsyncSession,
    org_id: UUID,
    batch: Batch,
    term: AcademicTerm,
    course: Course,
    user: User,
) -> ModuleLeaderAssignment:
    service = ModuleLeaderAssignmentService(session)
    return await service.assign(
        ModuleLeaderAssignmentCreate(
            batch_id=batch.id,
            academic_term_id=term.id,
            course_id=course.id,
            user_id=user.id,
        ),
        org_id,
    )


async def replace_section_teacher(
    session: AsyncSession,
    org_id: UUID,
    offering: SectionOffering,
    user: User,
) -> FacultyAssignment:
    service = FacultyAssignmentService(session)
    active_assignments = (
        await session.execute(
            select(FacultyAssignment).where(
                FacultyAssignment.section_offering_id == offering.id,
                FacultyAssignment.role_in_course == "SECTION_TEACHER",
                FacultyAssignment.removed_at.is_(None),
            )
        )
    ).scalars().all()
    for assignment in active_assignments:
        if assignment.user_id != user.id:
            await service.remove(assignment.id, org_id)

    existing = await _one(
        session,
        select(FacultyAssignment).where(
            FacultyAssignment.section_offering_id == offering.id,
            FacultyAssignment.user_id == user.id,
            FacultyAssignment.role_in_course == "SECTION_TEACHER",
            FacultyAssignment.removed_at.is_(None),
        ),
    )
    if existing is not None:
        return existing

    return await service.assign(
        FacultyAssignmentCreate(
            section_offering_id=offering.id,
            user_id=user.id,
            role_in_course="SECTION_TEACHER",
        ),
        org_id,
    )


async def seed_staffing(
    course_code: str,
    org_id: UUID | None = None,
    curriculum_id: UUID | None = None,
) -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        org = await resolve_org(session, org_id)
        course, curriculum, term_def = await resolve_course_context(
            session,
            org.id,
            course_code.upper(),
            curriculum_id,
        )
        batch, term = await ensure_batch_and_term(session, org.id, curriculum, term_def.term_number)
        department_id = await get_department_id(session, org.id, curriculum)

        module_leader = await ensure_user(
            session,
            org.id,
            f"ml.{course.code.lower()}@obelytics.local",
            f"{course.code} Module Leader",
            f"ML-{course.code}",
            department_id,
            "Module Leader",
        )
        await ensure_global_role(session, module_leader, org.id, "Module Leader")

        teachers: list[User] = []
        for index in range(1, SECTION_COUNT + 1):
            teacher = await ensure_user(
                session,
                org.id,
                f"teacher.{course.code.lower()}.s{index:02d}@obelytics.local",
                f"{course.code} Section Teacher {index:02d}",
                f"ST-{course.code}-{index:02d}",
                department_id,
                "Section Teacher",
            )
            await ensure_global_role(session, teacher, org.id, "Section Teacher")
            teachers.append(teacher)

        await session.commit()

        ml_assignment = await replace_module_leader(
            session,
            org.id,
            batch,
            term,
            course,
            module_leader,
        )
        section_pairs = await ensure_sections_and_offerings(session, org.id, curriculum, batch, term, course)
        await session.commit()

        teacher_assignments: list[FacultyAssignment] = []
        for (_section, offering), teacher in zip(section_pairs, teachers, strict=True):
            assignment = await replace_section_teacher(session, org.id, offering, teacher)
            teacher_assignments.append(assignment)

        await session.commit()

        print("\nCourse staffing seeded successfully.")
        print(f"Organization: {org.name} ({org.id})")
        print(f"Course: {course.code} - {course.title} ({course.id})")
        print(f"Curriculum: {curriculum.name} ({curriculum.id})")
        print(f"Batch: {batch.name} ({batch.id})")
        print(f"Academic term: {term.name} ({term.id})")
        print(f"Module leader: {module_leader.full_name} <{module_leader.email}>")
        print(f"Module leader assignment: {ml_assignment.id}")
        print(f"Sections/offering count: {len(section_pairs)}")
        print(f"Section teacher assignments: {len(teacher_assignments)}")
        print(f"Default password for created staff: {DEFAULT_PASSWORD}")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed module leader and 15 section teachers")
    parser.add_argument("--course-code", default="CSE102", help="Course code to staff")
    parser.add_argument("--org-id", default=None, help="Organization UUID")
    parser.add_argument("--curriculum-id", default=None, help="Curriculum UUID")
    args = parser.parse_args()

    asyncio.run(
        seed_staffing(
            course_code=args.course_code,
            org_id=UUID(args.org_id) if args.org_id else None,
            curriculum_id=UUID(args.curriculum_id) if args.curriculum_id else None,
        )
    )
