"""
Run: python -m scripts.seed_18_courses_10_sections

Seeds 10 sections (reusing the shared 71_A..71_J Section rows) for each of the
18 new courses (terms 4-12), each placed in its correct academic term. Uses a
fresh pool of 10 section teachers (distinct from the first 9 courses' 10
teachers), enrolls the same 50 students (same 10 groups of 5), seeds marks
with the 5-student-calibrated band distribution, and submits results + end
reports with justifications for any unattained CO.
"""

from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from uuid import UUID

sys.path.insert(0, "/home/mr-nacht/Workspace/University/obelytics/backend")

import app.main  # noqa: F401
from app.core.database import AsyncSessionLocal
from sqlalchemy import select

from app.modules.assessment.models import Assessment, Student, StudentMark
from app.modules.curriculum.models import Course, FacultyAssignment, Section, SectionOffering
from app.modules.curriculum.schemas import FacultyAssignmentCreate
from app.modules.curriculum.service import FacultyAssignmentService
from app.modules.iam.models import Role, User, UserRoleAssignment
from app.modules.obe.models import CourseOutcome
from app.modules.ref_data.models import AssessmentType
from scripts.seed_15_more_course_results import (
    _d,
    co_index_for,
    ensure_enrollments,
    get_section_teacher_id,
    load_course_mark_plan,
    seed_marks_for_offering,
    submit_result_and_end_report,
)
from scripts.fix_marks_distribution import ratio_5
import scripts.seed_15_more_course_results as base
from scripts.seed_9_courses_10_sections import FLAT_TOOLS, TOOL_TOTALS, seed_flat_assessment

SECTION_COUNT = 10
ORG_ID = UUID("5b7006ed-03d0-4d19-86b9-34d63b0e298a")
CURRICULUM_ID = UUID("a8c8f7aa-cbfa-4492-8719-01ab5f4de8d4")
BATCH_ID = UUID("90b35363-9d3d-4e24-8bba-ce0263a21841")

TERM_BY_NUM = {
    4: UUID("4d1e9fae-3d28-4128-843e-ad89bb310ecb"), 5: UUID("5403bf20-3c7e-4e8d-bb38-cce35b395e26"),
    6: UUID("d8d1d7b6-9430-4d14-bec0-56b59d46f2ea"), 7: UUID("0d910b12-d339-4a53-b515-942677a4a05b"),
    8: UUID("72a0fc08-a77c-46b7-a63b-72b0a2ed6f88"), 9: UUID("9e4f5d7d-8389-4dd4-897e-e59d5d17966a"),
    10: UUID("2458ea2c-96fb-4dd3-b2d3-ca149abe2d04"), 11: UUID("543f88a9-142e-4d1a-8eea-e18dacd85e78"),
    12: UUID("21bc97e6-92aa-4446-98b6-25d6b99407ac"),
}
COURSE_TERM = {
    "CSE302": 4, "CSE304": 4, "CSE401": 5, "CSE401L": 5, "CSE402": 6, "CSE404": 6, "CSE405": 7, "CSE405L": 7,
    "CSE407": 8, "CSE409": 8, "CSE411": 9, "CSE413": 9, "CSE415": 10, "CSE415L": 10, "CSE491": 11, "CSE419": 11,
    "CSE492": 12, "CSE498": 12,
}
COURSE_CODES = list(COURSE_TERM.keys())

NEW_TEACHER_IDS = [
    "9e0188d0-7d9e-45ed-9337-f02698de9b8a", "638ef531-a37d-48e2-b521-657e36f329c5",
    "35fd1671-731b-4a5e-82fb-7bdc022e495e", "0ea75c75-5512-4ff1-a25f-5af4819931cd",
    "24b91bf0-ffad-4a58-a420-8e4583bb31be", "5c038021-ae13-4d94-a264-def5479ef45b",
    "d32ae33f-43c4-439f-b422-743b7d0228ab", "2fcb1eb4-3720-4bc1-8194-cda1fbc0274f",
    "68bd449a-34a9-4236-ac02-71c7282f99a6", "27008f7b-010a-45c6-8007-749bfbfc7c37",
]


async def _one(session, stmt):
    return (await session.execute(stmt)).scalar_one_or_none()


async def ensure_teacher_roles(session) -> list[UUID]:
    role = await _one(session, select(Role).where(Role.organization_id == ORG_ID, Role.name == "Section Teacher"))
    ids = [UUID(t) for t in NEW_TEACHER_IDS]
    for user_id in ids:
        existing = await _one(session, select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id, UserRoleAssignment.role_id == role.id, UserRoleAssignment.removed_at.is_(None)
        ))
        if existing is None:
            session.add(UserRoleAssignment(user_id=user_id, role_id=role.id, scope_type="GLOBAL", scope_id=None, assigned_by=None))
    await session.flush()
    return ids


async def get_student_groups(session) -> dict[int, list[Student]]:
    students = (
        await session.execute(
            select(Student).where(Student.organization_id == ORG_ID, Student.batch_id == BATCH_ID, Student.status == "ACTIVE")
            .order_by(Student.student_id_number)
        )
    ).scalars().all()
    if len(students) != 50:
        raise RuntimeError(f"Expected 50 students, got {len(students)}")
    return {i + 1: list(students[i * 5:(i + 1) * 5]) for i in range(SECTION_COUNT)}


async def ensure_canonical_sections(session) -> dict[int, UUID]:
    sections = (await session.execute(select(Section).where(Section.organization_id == ORG_ID, Section.name.like("71_%")))).scalars().all()
    by_letter = {s.name: s.id for s in sections}
    letters = "ABCDEFGHIJ"
    return {i + 1: by_letter[f"71_{letters[i]}"] for i in range(SECTION_COUNT)}


async def ensure_offering(session, course: Course, term_id: UUID, section_id: UUID) -> SectionOffering:
    offering = await _one(session, select(SectionOffering).where(
        SectionOffering.batch_id == BATCH_ID, SectionOffering.course_id == course.id,
        SectionOffering.academic_term_id == term_id, SectionOffering.section_id == section_id,
    ))
    if offering is None:
        offering = SectionOffering(
            organization_id=ORG_ID, curriculum_id=CURRICULUM_ID, batch_id=BATCH_ID, course_id=course.id,
            academic_term_id=term_id, section_id=section_id, status="UPCOMING",
        )
        session.add(offering)
        await session.flush()
    return offering


async def ensure_teacher_assignment(session, offering: SectionOffering, teacher_id: UUID) -> None:
    existing = await _one(session, select(FacultyAssignment).where(
        FacultyAssignment.section_offering_id == offering.id, FacultyAssignment.user_id == teacher_id,
        FacultyAssignment.role_in_course == "SECTION_TEACHER", FacultyAssignment.removed_at.is_(None),
    ))
    if existing is not None:
        return
    svc = FacultyAssignmentService(session)
    await svc.assign(FacultyAssignmentCreate(section_offering_id=offering.id, user_id=teacher_id, role_in_course="SECTION_TEACHER"), ORG_ID)


async def seed_all() -> None:
    base._ratio = ratio_5  # calibrated for 5-student sections

    async with AsyncSessionLocal() as session:
        teacher_ids = await ensure_teacher_roles(session)
        student_groups = await get_student_groups(session)
        canonical_sections = await ensure_canonical_sections(session)
        await session.commit()
        print(f"Teachers: {len(teacher_ids)}, sections: {len(canonical_sections)}")

        total = 0
        for course_index, course_code in enumerate(COURSE_CODES, start=1):
            course = await _one(session, select(Course).where(Course.organization_id == ORG_ID, Course.code == course_code, Course.status == "ACTIVE"))
            term_id = TERM_BY_NUM[COURSE_TERM[course_code]]
            mark_plan = await load_course_mark_plan(session, CURRICULUM_ID, course.id)
            co_code_by_id = {co.id: co.code for co in (await session.execute(select(CourseOutcome).where(CourseOutcome.course_id == course.id))).scalars().all()}

            print(f"\n=== {course_code} (term {COURSE_TERM[course_code]}) ===")
            for slot in range(1, SECTION_COUNT + 1):
                section_id = canonical_sections[slot]
                offering = await ensure_offering(session, course, term_id, section_id)
                teacher_id = teacher_ids[slot - 1]
                await ensure_teacher_assignment(session, offering, teacher_id)
                await session.commit()

                enrollments = await ensure_enrollments(session, offering, student_groups[slot])

                await seed_marks_for_offering(
                    session, offering, course_index=course_index, section_index=slot,
                    enrollments=enrollments, teacher_id=teacher_id, co_code_by_id=co_code_by_id, mark_plan=mark_plan,
                )
                for tool_name in FLAT_TOOLS:
                    await seed_flat_assessment(session, offering, tool_name, _d(TOOL_TOTALS[tool_name]), enrollments, teacher_id, course_index, slot)

                section = await _one(session, select(Section).where(Section.id == section_id))
                await submit_result_and_end_report(session, offering, course, section.name, teacher_id)
                await session.commit()
                total += 1
                print(f"  {section.name}: submitted ({len(enrollments)} students, teacher {teacher_id})")

        print(f"\nDone. Sections submitted: {total}")


if __name__ == "__main__":
    asyncio.run(seed_all())
