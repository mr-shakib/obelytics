"""
Run: python -m scripts.seed_integrity_demo [--org-id <uuid>] [--course-code CSE226]
                                          [--course-title "Numerical Methods"]

Creates a small synthetic setup for demonstrating the assessment integrity auditor:
  - academic term Summer 2026, a demo batch and a demo section
  - a section offering of Numerical Methods
  - course outcomes CO1–CO3 with Bloom levels
  - a FINAL marksheet of six questions with declared CO and Bloom level
  - 40 synthetic students (DEMO-0001…, @student.example.edu) with random FINAL marks,
    so attainment and evidence-weighted attainment have numbers to show

The declared Bloom levels follow a typical action-verb list ("identify" → Remember,
"develop" → Create), which is the habit the auditor is designed to catch. No
question wording is seeded: upload a question paper on the Assessment Integrity
page to fill it in.

Safe to re-run: records are found by name/code and updated in place.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys
from datetime import date
from decimal import Decimal
from uuid import UUID

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.modules.assessment.models import (
    MarksheetMark,
    MarksheetQuestion,
    Student,
    StudentEnrollment,
)
from app.modules.curriculum.models import (
    AcademicTerm,
    Batch,
    Course,
    Curriculum,
    CurriculumCourseSlot,
    Section,
    SectionOffering,
)
from app.modules.obe.models import CourseOutcome, CourseOutcomeBloomLevel
from app.modules.org.models import Organization
from app.modules.ref_data.models import BloomDomain, BloomLevel

BATCH_NAME = "Integrity Demo Batch"
SECTION_NAME = "INTEGRITY-DEMO-A"

OUTCOMES = [
    ("CO1", "Explain the sources of numerical error and the convergence of iterative methods.",
     ["C2"]),
    ("CO2", "Apply iterative and step-by-step methods to solve systems of linear equations and "
            "ordinary differential equations.", ["C3"]),
    ("CO3", "Apply interpolation, numerical integration and least-squares curve fitting to data, "
            "and compare the accuracy of these methods.", ["C3", "C4"]),
]

# (label, max marks, declared CO, declared Bloom) — declared by action verb.
FINAL_QUESTIONS = [
    ("Q1a", "6", "CO2", "C3"),   # "Apply Gauss-Seidel …"
    ("Q1b", "4", "CO2", "C1"),   # "Identify the local maximum …"
    ("Q2", "10", "CO2", "C3"),   # "Apply Runge-Kutta …"
    ("Q3", "10", "CO2", "C1"),   # "Identify the best method …"
    ("Q4a", "5", "CO3", "C6"),   # "Develop the second degree polynomial …"
    ("Q4b", "5", "CO3", "C3"),   # "… by applying least squares"
]


STUDENTS = 40
# Small per-question differences in how hard the question is (0 = average), so the
# synthetic marks are not uniform. Marks are random, seeded so re-runs match.
DIFFICULTY = {"Q1a": 0.0, "Q1b": -0.12, "Q2": 0.05, "Q3": -0.08, "Q4a": 0.08, "Q4b": 0.1}


async def _one(session: AsyncSession, stmt):
    return (await session.execute(stmt)).scalar_one_or_none()


async def seed(org_id: UUID | None, course_code: str, course_title: str) -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        if org_id is None:
            orgs = (await session.execute(select(Organization.id))).scalars().all()
            if len(orgs) != 1:
                sys.exit("More than one organization exists; pass --org-id.")
            org_id = orgs[0]

        row = (await session.execute(
            select(Course, CurriculumCourseSlot.curriculum_id)
            .join(CurriculumCourseSlot, CurriculumCourseSlot.course_id == Course.id)
            .where(Course.organization_id == org_id, Course.code == course_code,
                   Course.title.ilike(course_title))
            .limit(1)
        )).first()
        if row is None:
            sys.exit(f"Course {course_code} {course_title} is not in any curriculum of this organization.")
        course, curriculum_id = row
        print(f"[=] Course: {course.code} {course.title}")

        levels = {
            level.code: level.id
            for level in (await session.execute(
                select(BloomLevel)
                .join(BloomDomain, BloomDomain.id == BloomLevel.bloom_domain_id)
                .where(BloomLevel.organization_id == org_id, BloomDomain.name.ilike("cognitive%"))
            )).scalars()
        }
        missing = {"C1", "C2", "C3", "C4", "C5", "C6"} - levels.keys()
        if missing:
            sys.exit(f"Cognitive Bloom levels missing ({sorted(missing)}); run seed_reference_data first.")

        term = await _one(session, select(AcademicTerm).where(
            AcademicTerm.organization_id == org_id, AcademicTerm.year == 2026,
            AcademicTerm.season == "SUMMER",
        ))
        if term is None:
            term = AcademicTerm(organization_id=org_id, name="Summer 2026", year=2026, season="SUMMER",
                                start_date=date(2026, 5, 1), end_date=date(2026, 8, 31), status="ACTIVE")
            session.add(term)
        batch = await _one(session, select(Batch).where(
            Batch.curriculum_id == curriculum_id, Batch.name == BATCH_NAME,
        ))
        if batch is None:
            batch = Batch(organization_id=org_id, curriculum_id=curriculum_id, name=BATCH_NAME,
                          intake_year=2024, start_date=date(2024, 5, 1), term_system="TRIMESTER",
                          num_semesters=12)
            session.add(batch)
        section = await _one(session, select(Section).where(
            Section.organization_id == org_id, Section.name == SECTION_NAME,
        ))
        if section is None:
            section = Section(organization_id=org_id, name=SECTION_NAME, capacity=40)
            session.add(section)
        await session.flush()

        offering = await _one(session, select(SectionOffering).where(
            SectionOffering.batch_id == batch.id, SectionOffering.course_id == course.id,
            SectionOffering.academic_term_id == term.id, SectionOffering.section_id == section.id,
        ))
        if offering is None:
            offering = SectionOffering(organization_id=org_id, curriculum_id=curriculum_id,
                                       batch_id=batch.id, course_id=course.id,
                                       academic_term_id=term.id, section_id=section.id,
                                       status="ACTIVE")
            session.add(offering)
            await session.flush()
        print(f"[+] Section offering: {offering.id} ({SECTION_NAME}, {term.name})")

        outcome_ids = {}
        for code, statement, bloom_codes in OUTCOMES:
            co = await _one(session, select(CourseOutcome).where(
                CourseOutcome.curriculum_id == curriculum_id, CourseOutcome.course_id == course.id,
                CourseOutcome.code == code,
            ))
            if co is None:
                co = CourseOutcome(organization_id=org_id, curriculum_id=curriculum_id,
                                   course_id=course.id, code=code, statement=statement)
                session.add(co)
                await session.flush()
                for bloom in bloom_codes:
                    session.add(CourseOutcomeBloomLevel(course_outcome_id=co.id,
                                                        bloom_level_id=levels[bloom]))
            outcome_ids[code] = co.id
        print(f"[+] Course outcomes: {', '.join(outcome_ids)}")

        existing = {
            q.label: q for q in (await session.execute(select(MarksheetQuestion).where(
                MarksheetQuestion.section_offering_id == offering.id,
                MarksheetQuestion.exam_type == "FINAL",
            ))).scalars()
        }
        for order, (label, marks, co_code, bloom) in enumerate(FINAL_QUESTIONS):
            question = existing.get(label) or MarksheetQuestion(
                organization_id=org_id, section_offering_id=offering.id, exam_type="FINAL",
                label=label, order_index=order,
            )
            question.max_marks = Decimal(marks)
            question.course_outcome_id = outcome_ids[co_code]
            question.declared_bloom_level_id = levels[bloom]
            session.add(question)
        await session.flush()
        print(f"[+] FINAL marksheet: {len(FINAL_QUESTIONS)} questions with declared CO and Bloom level")

        curriculum = await session.get(Curriculum, curriculum_id)
        questions = {
            q.label: q for q in (await session.execute(select(MarksheetQuestion).where(
                MarksheetQuestion.section_offering_id == offering.id,
                MarksheetQuestion.exam_type == "FINAL",
            ))).scalars()
        }
        rng = random.Random(2026)
        added = 0
        for n in range(1, STUDENTS + 1):
            number = f"DEMO-{n:04d}"
            student = await _one(session, select(Student).where(
                Student.organization_id == org_id, Student.student_id_number == number,
            ))
            if student is None:
                student = Student(organization_id=org_id, student_id_number=number,
                                  full_name=f"Demo Student {n:02d}", email=f"demo{n:02d}@student.example.edu",
                                  program_id=curriculum.program_id, batch_id=batch.id)
                session.add(student)
                await session.flush()
            enrollment = await _one(session, select(StudentEnrollment).where(
                StudentEnrollment.student_id == student.id,
                StudentEnrollment.section_offering_id == offering.id,
            ))
            if enrollment is None:
                enrollment = StudentEnrollment(organization_id=org_id, student_id=student.id,
                                               section_offering_id=offering.id)
                session.add(enrollment)
                await session.flush()
            ability = min(max(rng.gauss(0.6, 0.16), 0.05), 0.98)
            for label, question in questions.items():
                share = min(max(ability - DIFFICULTY.get(label, 0.0) + rng.gauss(0, 0.12), 0.0), 1.0)
                obtained = Decimal(str(round(share * float(question.max_marks) * 2) / 2))
                exists = await _one(session, select(MarksheetMark.id).where(
                    MarksheetMark.question_id == question.id,
                    MarksheetMark.student_enrollment_id == enrollment.id,
                ))
                if exists is None:  # never overwrite marks someone entered
                    session.add(MarksheetMark(organization_id=org_id, question_id=question.id,
                                              student_enrollment_id=enrollment.id, marks_obtained=obtained))
                    added += 1
        await session.commit()
        print(f"[+] Students: {STUDENTS} enrolled; {added} FINAL marks added (synthetic)")
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--org-id", type=UUID, default=None)
    parser.add_argument("--course-code", default="CSE226")
    # Course codes repeat across curricula, so the title picks the right course.
    parser.add_argument("--course-title", default="Numerical Methods")
    args = parser.parse_args()
    asyncio.run(seed(args.org_id, args.course_code, args.course_title))


if __name__ == "__main__":
    main()
