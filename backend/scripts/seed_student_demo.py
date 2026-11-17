"""
Run: python -m scripts.seed_student_demo --org-id <uuid> [--password <pw>] [--student DEMO-0001]

Gives one synthetic demo student a login and published results, so the student
portal's "My Skills" page has something to show:
  - a Student account student@demo.example.edu linked to DEMO-0001
  - section offerings (Spring 2026, SKILLS-DEMO-A) of the courses the program's latest
    market analysis cites most, each with a FINAL marksheet of one question per CO
  - synthetic marks for the first ten demo students, with this student strong in some
    outcomes and weak in others, and the results published

Run after seed_demo_courses, seed_authoring_demo and seed_integrity_demo (which creates
the demo students), and after one workforce analysis. Everything is synthetic.
Safe to re-run: records are found by name/code and never duplicated; marks already
entered are not overwritten.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys
from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import hash_password
from app.modules.assessment.models import (
    MarksheetMark,
    MarksheetQuestion,
    ResultPublication,
    Student,
    StudentEnrollment,
)
from app.modules.curriculum.models import AcademicTerm, Batch, Course, Section, SectionOffering
from app.modules.iam.models import PasswordCredential, Role, User, UserRoleAssignment
from app.modules.obe.models import CourseOutcome
from app.modules.org.models import Organization, Program  # noqa: F401  (foreign-key targets)
from app.modules.ref_data.models import BloomLevel  # noqa: F401  (foreign-key target)
from app.modules.workforce.models import MarketAnalysis

SECTION_NAME = "SKILLS-DEMO-A"
STUDENT_EMAIL = "student@demo.example.edu"
COURSES = 4
CLASSMATES = 10
# How well the demo student does in each chosen course (share of marks, before noise):
# strong, strong, middling, weak, so the skills page shows every status.
PROFILE = [0.86, 0.78, 0.62, 0.38]


async def _one(session: AsyncSession, stmt):
    return (await session.execute(stmt)).scalar_one_or_none()


async def _pick_courses(session: AsyncSession, curriculum_id: UUID) -> list[Course]:
    analysis = await _one(session, select(MarketAnalysis).where(
        MarketAnalysis.curriculum_id == curriculum_id,
    ).order_by(MarketAnalysis.created_at.desc()).limit(1))
    cited: Counter = Counter()
    if analysis is not None:
        for skill in analysis.result.get("skills", []):
            if skill.get("coverage") in ("covered", "partial"):
                for ref in skill.get("outcomes") or []:
                    cited[ref.get("course_code")] += skill.get("postings", 1)
    else:
        print("[!] No market analysis yet: run one on the Workforce Readiness page, then re-run this script.")
    courses = (await session.execute(
        select(Course).join(CourseOutcome, CourseOutcome.course_id == Course.id)
        .where(CourseOutcome.curriculum_id == curriculum_id).distinct()
    )).scalars().all()
    courses = sorted(courses, key=lambda c: (-cited.get(c.code, 0), c.code))
    return courses[:COURSES]


async def seed(org_id: UUID, password: str, student_number: str) -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        student = await _one(session, select(Student).where(
            Student.organization_id == org_id, Student.student_id_number == student_number,
        ))
        if student is None or student.batch_id is None:
            sys.exit(f"Student {student_number} not found; run seed_integrity_demo first.")
        batch = await session.get(Batch, student.batch_id)
        curriculum_id = batch.curriculum_id

        courses = await _pick_courses(session, curriculum_id)
        print(f"[=] Courses: {', '.join(c.code for c in courses)}")

        term = await _one(session, select(AcademicTerm).where(
            AcademicTerm.organization_id == org_id, AcademicTerm.year == 2026, AcademicTerm.season == "SPRING",
        ))
        if term is None:
            term = AcademicTerm(organization_id=org_id, name="Spring 2026", year=2026, season="SPRING",
                                start_date=date(2026, 1, 10), end_date=date(2026, 4, 30), status="ACTIVE")
            session.add(term)
        section = await _one(session, select(Section).where(
            Section.organization_id == org_id, Section.name == SECTION_NAME,
        ))
        if section is None:
            section = Section(organization_id=org_id, name=SECTION_NAME, capacity=40)
            session.add(section)
        await session.flush()

        classmates = (await session.execute(
            select(Student).where(Student.organization_id == org_id, Student.batch_id == batch.id)
            .order_by(Student.student_id_number).limit(CLASSMATES)
        )).scalars().all()
        if student.id not in {s.id for s in classmates}:
            classmates = [student, *classmates[: CLASSMATES - 1]]

        rng = random.Random(2027)
        added = 0
        for index, course in enumerate(courses):
            offering = await _one(session, select(SectionOffering).where(
                SectionOffering.batch_id == batch.id, SectionOffering.course_id == course.id,
                SectionOffering.academic_term_id == term.id, SectionOffering.section_id == section.id,
            ))
            if offering is None:
                offering = SectionOffering(organization_id=org_id, curriculum_id=curriculum_id, batch_id=batch.id,
                                           course_id=course.id, academic_term_id=term.id, section_id=section.id,
                                           status="ACTIVE")
                session.add(offering)
                await session.flush()

            outcomes = (await session.execute(
                select(CourseOutcome).where(CourseOutcome.curriculum_id == curriculum_id,
                                            CourseOutcome.course_id == course.id)
                .order_by(CourseOutcome.code)
            )).scalars().all()
            existing = {q.label: q for q in (await session.execute(select(MarksheetQuestion).where(
                MarksheetQuestion.section_offering_id == offering.id, MarksheetQuestion.exam_type == "FINAL",
            ))).scalars()}
            questions = []
            for order, co in enumerate(outcomes):
                label = f"Q{order + 1}"
                question = existing.get(label) or MarksheetQuestion(
                    organization_id=org_id, section_offering_id=offering.id, exam_type="FINAL",
                    label=label, order_index=order, max_marks=Decimal("10"),
                )
                question.course_outcome_id = co.id
                session.add(question)
                questions.append(question)
            await session.flush()

            for mate in classmates:
                enrollment = await _one(session, select(StudentEnrollment).where(
                    StudentEnrollment.student_id == mate.id, StudentEnrollment.section_offering_id == offering.id,
                ))
                if enrollment is None:
                    enrollment = StudentEnrollment(organization_id=org_id, student_id=mate.id,
                                                   section_offering_id=offering.id)
                    session.add(enrollment)
                    await session.flush()
                base = PROFILE[index % len(PROFILE)] if mate.id == student.id else rng.gauss(0.62, 0.15)
                for question in questions:
                    share = min(max(base + rng.gauss(0, 0.1), 0.0), 1.0)
                    obtained = Decimal(str(round(share * float(question.max_marks) * 2) / 2))
                    exists = await _one(session, select(MarksheetMark.id).where(
                        MarksheetMark.question_id == question.id, MarksheetMark.student_enrollment_id == enrollment.id,
                    ))
                    if exists is None:
                        session.add(MarksheetMark(organization_id=org_id, question_id=question.id,
                                                  student_enrollment_id=enrollment.id, marks_obtained=obtained))
                        added += 1

            publication = await _one(session, select(ResultPublication).where(
                ResultPublication.section_offering_id == offering.id,
            ))
            if publication is None:
                publication = ResultPublication(organization_id=org_id, section_offering_id=offering.id)
                session.add(publication)
            publication.status = "PUBLISHED"
            publication.published_at = publication.published_at or datetime.now(UTC)
            print(f"[+] {course.code}: {len(questions)} questions, {len(classmates)} students, published")

        user = await _one(session, select(User).where(User.email == STUDENT_EMAIL))
        if user is None:
            role = await _one(session, select(Role).where(Role.organization_id == org_id, Role.name == "Student"))
            if role is None:
                sys.exit("The Student role is missing; run seed_superadmin first.")
            user = User(organization_id=org_id, email=STUDENT_EMAIL, full_name=student.full_name,
                        employee_id=student.student_id_number, status="ACTIVE", linked_student_id=student.id)
            session.add(user)
            await session.flush()
            session.add(PasswordCredential(user_id=user.id, hashed_password=hash_password(password),
                                           must_change_password=False))
            session.add(UserRoleAssignment(user_id=user.id, role_id=role.id, scope_type="PROGRAM",
                                           scope_id=student.program_id, assigned_by=user.id))
            print(f"[+] Student login: {STUDENT_EMAIL} → {student.student_id_number}")
        else:
            print(f"[=] Student login exists: {STUDENT_EMAIL}")
        await session.commit()
        print(f"[+] {added} marks added (synthetic)")
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--org-id", type=UUID, required=True)
    parser.add_argument("--password", default="Demo@2026", help="Password for the student login")
    parser.add_argument("--student", default="DEMO-0001", help="Student ID number to give a login")
    args = parser.parse_args()
    asyncio.run(seed(args.org_id, args.password, args.student))


if __name__ == "__main__":
    main()
