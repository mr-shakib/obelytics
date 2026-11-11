"""Integration tests for the assessment integrity data foundation (T11).

Covers the question wording / declared Bloom level on marksheet questions and
the database guarantees behind AI question audits.
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assessment.exceptions import DeclaredBloomLevelInvalidError
from app.modules.assessment.models import MarksheetQuestion
from app.modules.assessment.schemas import MarksheetQuestionInput
from app.modules.assessment.service import MarksheetService
from app.modules.curriculum.models import (
    AcademicTerm,
    Batch,
    Course,
    Curriculum,
    Section,
    SectionOffering,
)
from app.modules.integrity.models import QuestionAudit, QuestionPaper
from app.modules.obe.models import CourseOutcome
from app.modules.org.models import Department, Organization, Program
from app.modules.ref_data.models import BloomDomain, BloomLevel, CourseCategory

# ── Scenario builder ──────────────────────────────────────────────────────────

async def _build_scenario(db: AsyncSession) -> dict:
    """org → program → curriculum → course → offering, plus one CO and two Bloom levels."""
    suffix = uuid.uuid4().hex[:8]
    full = int(uuid.uuid4().hex, 16)

    org = Organization(name=f"Integrity Org {suffix}", short_name=f"IN{suffix}")
    db.add(org)
    await db.flush()

    dept = Department(organization_id=org.id, name=f"Integrity Dept {suffix}", short_name=f"ID{suffix}")
    db.add(dept)
    await db.flush()

    program = Program(
        organization_id=org.id,
        department_id=dept.id,
        title=f"Integrity Program {suffix}",
        acronym=f"IP{suffix}",
        program_type="UNDERGRADUATE",
        minimum_duration_semesters=8,
        total_credits=136,
        study_mode="FULL_TIME",
    )
    db.add(program)
    await db.flush()

    curriculum = Curriculum(
        organization_id=org.id,
        program_id=program.id,
        name=f"Integrity Curriculum {suffix}",
        code=f"IC{suffix}",
        effective_year=2026,
    )
    category = CourseCategory(organization_id=org.id, name=f"Integrity Theory {suffix}")
    domain = BloomDomain(organization_id=org.id, name=f"Cognitive {suffix}")
    db.add_all([curriculum, category, domain])
    await db.flush()

    course = Course(
        organization_id=org.id,
        course_category_id=category.id,
        course_type="THEORY",
        code=f"INT{suffix}",
        title=f"Integrity Course {suffix}",
        credits=3,
    )
    batch = Batch(organization_id=org.id, curriculum_id=curriculum.id, name=f"Batch {suffix}")
    term = AcademicTerm(
        organization_id=org.id,
        name=f"Term {suffix}",
        year=4000 + (full % 500),
        season=["FALL", "SPRING", "SUMMER", "WINTER"][(full >> 32) % 4],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
    )
    section = Section(organization_id=org.id, name=f"S{suffix}")
    remember = BloomLevel(organization_id=org.id, bloom_domain_id=domain.id,
                          code="C1", name="Remember", order_index=1)
    analyze = BloomLevel(organization_id=org.id, bloom_domain_id=domain.id,
                         code="C4", name="Analyze", order_index=4)
    db.add_all([course, batch, term, section, remember, analyze])
    await db.flush()

    offering = SectionOffering(
        organization_id=org.id,
        curriculum_id=curriculum.id,
        batch_id=batch.id,
        course_id=course.id,
        academic_term_id=term.id,
        section_id=section.id,
    )
    co = CourseOutcome(
        organization_id=org.id,
        curriculum_id=curriculum.id,
        course_id=course.id,
        code="CO1",
        statement="Analyze the time complexity of algorithms.",
    )
    db.add_all([offering, co])
    await db.flush()

    return {
        "org_id": org.id,
        "offering_id": offering.id,
        "co_id": co.id,
        "remember_id": remember.id,
        "analyze_id": analyze.id,
    }


def _question(s: dict, **overrides) -> MarksheetQuestionInput:
    fields = {
        "label": "Q1a",
        "max_marks": Decimal("5"),
        "course_outcome_id": s["co_id"],
        "order_index": 0,
    }
    fields.update(overrides)
    return MarksheetQuestionInput(**fields)


async def _create_question(db: AsyncSession, s: dict) -> MarksheetQuestion:
    question = MarksheetQuestion(
        organization_id=s["org_id"],
        section_offering_id=s["offering_id"],
        exam_type="MID",
        label="Q1a",
        max_marks=Decimal("5"),
        course_outcome_id=s["co_id"],
    )
    db.add(question)
    await db.flush()
    return question


def _audit(s: dict, question_id, **overrides) -> QuestionAudit:
    fields = {
        "organization_id": s["org_id"],
        "question_id": question_id,
        "alignment": "PARTIAL",
        "confidence": Decimal("0.810"),
        "model": "test-model",
        "prompt_version": "auditor-v1",
    }
    fields.update(overrides)
    return QuestionAudit(**fields)


# ── Question wording + declared Bloom level ───────────────────────────────────

async def test_question_text_and_declared_bloom_round_trip(db_session: AsyncSession):
    s = await _build_scenario(db_session)
    svc = MarksheetService(db_session)

    [saved] = await svc.replace_questions(
        s["offering_id"], "MID", s["org_id"],
        [_question(s, question_text="Define Big-O notation.", declared_bloom_level_id=s["analyze_id"])],
        acting_user_id=None,
    )

    assert saved.question_text == "Define Big-O notation."
    assert saved.declared_bloom_level_id == s["analyze_id"]


async def test_omitted_integrity_fields_are_preserved(db_session: AsyncSession):
    """A client that predates the integrity fields must not wipe them on save."""
    s = await _build_scenario(db_session)
    svc = MarksheetService(db_session)
    [saved] = await svc.replace_questions(
        s["offering_id"], "MID", s["org_id"],
        [_question(s, question_text="Define Big-O notation.", declared_bloom_level_id=s["analyze_id"])],
        acting_user_id=None,
    )

    [resaved] = await svc.replace_questions(
        s["offering_id"], "MID", s["org_id"],
        [_question(s, id=saved.id, max_marks=Decimal("6"))],
        acting_user_id=None,
    )

    assert resaved.max_marks == Decimal("6")
    assert resaved.question_text == "Define Big-O notation."
    assert resaved.declared_bloom_level_id == s["analyze_id"]


async def test_explicit_null_clears_integrity_fields(db_session: AsyncSession):
    s = await _build_scenario(db_session)
    svc = MarksheetService(db_session)
    [saved] = await svc.replace_questions(
        s["offering_id"], "MID", s["org_id"],
        [_question(s, question_text="Define Big-O notation.", declared_bloom_level_id=s["analyze_id"])],
        acting_user_id=None,
    )

    [cleared] = await svc.replace_questions(
        s["offering_id"], "MID", s["org_id"],
        [_question(s, id=saved.id, question_text=None, declared_bloom_level_id=None)],
        acting_user_id=None,
    )

    assert cleared.question_text is None
    assert cleared.declared_bloom_level_id is None


async def test_declared_bloom_level_from_another_org_is_rejected(db_session: AsyncSession):
    s = await _build_scenario(db_session)
    other = await _build_scenario(db_session)
    svc = MarksheetService(db_session)

    with pytest.raises(DeclaredBloomLevelInvalidError):
        await svc.replace_questions(
            s["offering_id"], "MID", s["org_id"],
            [_question(s, declared_bloom_level_id=other["analyze_id"])],
            acting_user_id=None,
        )


# ── Database guarantees behind AI audits ──────────────────────────────────────

async def test_only_one_current_audit_per_question(db_session: AsyncSession):
    s = await _build_scenario(db_session)
    question = await _create_question(db_session, s)
    db_session.add(_audit(s, question.id, is_current=False))
    db_session.add(_audit(s, question.id))
    await db_session.flush()

    db_session.add(_audit(s, question.id))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_override_requires_a_reason(db_session: AsyncSession):
    s = await _build_scenario(db_session)
    question = await _create_question(db_session, s)

    db_session.add(_audit(s, question.id, review_status="OVERRIDDEN"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_override_with_reason_is_stored(db_session: AsyncSession):
    s = await _build_scenario(db_session)
    question = await _create_question(db_session, s)

    audit = _audit(
        s, question.id,
        ai_bloom_level_id=s["remember_id"],
        review_status="OVERRIDDEN",
        override_reason="Part (ii) asks students to compare two algorithms.",
    )
    db_session.add(audit)
    await db_session.flush()

    assert audit.override_reason.startswith("Part (ii)")


async def test_confidence_must_be_a_probability(db_session: AsyncSession):
    s = await _build_scenario(db_session)
    question = await _create_question(db_session, s)

    db_session.add(_audit(s, question.id, confidence=Decimal("1.500")))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_one_question_paper_per_exam(db_session: AsyncSession):
    s = await _build_scenario(db_session)

    def paper() -> QuestionPaper:
        return QuestionPaper(
            organization_id=s["org_id"],
            section_offering_id=s["offering_id"],
            exam_type="MID",
            original_filename="midterm.pdf",
            content_type="application/pdf",
            file_size_bytes=1024,
            file_sha256="0" * 64,
        )

    db_session.add(paper())
    await db_session.flush()

    db_session.add(paper())
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()
