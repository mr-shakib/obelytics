"""Integration tests for the CQI module (Phase 1 — gap detection)."""
import uuid
from datetime import date
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attainment.models import COAttainmentResult, POAttainmentResult
from app.modules.cqi.detector import CQIGapDetector
from app.modules.cqi.models import COAttainmentGap, POAttainmentGap
from app.modules.curriculum.models import (
    AcademicTerm,
    Batch,
    Course,
    Curriculum,
    Section,
    SectionOffering,
)
from app.modules.obe.models import CourseOutcome, ProgramOutcome
from app.modules.org.models import Department, Organization, Program
from app.modules.ref_data.models import CourseCategory

# ── Scenario builder ──────────────────────────────────────────────────────────

async def _build_scenario(db: AsyncSession, threshold: Decimal = Decimal("50.00")) -> dict:
    """
    Create the minimum object graph the detector walks:
    org → department → program → curriculum → course → offering → CO / PO.

    Attainment results are inserted directly by each test, standing in for a
    completed engine run.
    """
    suffix = uuid.uuid4().hex[:8]
    full = int(uuid.uuid4().hex, 16)

    org = Organization(name=f"CQI Org {suffix}", short_name=f"CQ{suffix}")
    db.add(org)
    await db.flush()

    dept = Department(organization_id=org.id, name=f"CQI Dept {suffix}", short_name=f"CD{suffix}")
    db.add(dept)
    await db.flush()

    program = Program(
        organization_id=org.id,
        department_id=dept.id,
        title=f"CQI Program {suffix}",
        acronym=f"CP{suffix}",
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
        name=f"CQI Curriculum {suffix}",
        code=f"CC{suffix}",
        effective_year=2026,
        threshold_co_score_pct=threshold,
    )
    category = CourseCategory(organization_id=org.id, name=f"CQI Theory {suffix}")
    db.add_all([curriculum, category])
    await db.flush()

    course = Course(
        organization_id=org.id,
        course_category_id=category.id,
        course_type="THEORY",
        code=f"CQI{suffix}",
        title=f"CQI Course {suffix}",
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
    db.add_all([course, batch, term, section])
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
        statement="Apply CQI principles.",
    )
    po = ProgramOutcome(
        organization_id=org.id,
        program_id=program.id,
        code="PO1",
        statement="Engineering knowledge.",
        order_index=1,
    )
    db.add_all([offering, co, po])
    await db.flush()

    return {
        "org_id": org.id,
        "program_id": program.id,
        "curriculum_id": curriculum.id,
        "course_id": course.id,
        "term_id": term.id,
        "offering_id": offering.id,
        "co_id": co.id,
        "po_id": po.id,
        "batch_id": batch.id,
        "section_id": section.id,
    }


async def _add_co_result(
    db: AsyncSession, s: dict, *, above: int, total: int, avg: str, is_attained: bool
) -> None:
    db.add(
        COAttainmentResult(
            organization_id=s["org_id"],
            section_offering_id=s["offering_id"],
            course_outcome_id=s["co_id"],
            average_attainment_pct=Decimal(avg),
            students_above_threshold=above,
            total_students=total,
            is_attained=is_attained,
        )
    )
    await db.flush()


async def _co_gap(db: AsyncSession, s: dict) -> COAttainmentGap | None:
    result = await db.execute(
        select(COAttainmentGap).where(
            COAttainmentGap.section_offering_id == s["offering_id"]
        )
    )
    return result.scalar_one_or_none()


# ── CO gap detection ──────────────────────────────────────────────────────────

async def test_unattained_co_opens_a_gap(db_session: AsyncSession):
    """An unattained CO produces an OPEN gap snapshotting the measurement."""
    s = await _build_scenario(db_session)
    # 2 of 10 students cleared the CO threshold → 20% cohort attainment.
    await _add_co_result(db_session, s, above=2, total=10, avg="41.50", is_attained=False)

    await CQIGapDetector(db_session).sync_for_section_offering(s["offering_id"], s["org_id"])

    gap = await _co_gap(db_session, s)
    assert gap is not None
    assert gap.status == "OPEN"
    assert gap.course_outcome_id == s["co_id"]
    # attainment_pct is the gated figure (cohort share), not the mean score.
    assert gap.attainment_pct == Decimal("20.00")
    assert gap.average_score_pct == Decimal("41.50")
    assert gap.threshold_pct == Decimal("50.00")
    assert gap.students_above_threshold == 2
    assert gap.total_students == 10
    assert gap.resolved_at is None


async def test_attained_co_creates_no_gap(db_session: AsyncSession):
    """A CO that meets the threshold is not flagged."""
    s = await _build_scenario(db_session)
    await _add_co_result(db_session, s, above=8, total=10, avg="72.00", is_attained=True)

    await CQIGapDetector(db_session).sync_for_section_offering(s["offering_id"], s["org_id"])

    assert await _co_gap(db_session, s) is None


async def test_detection_is_idempotent(db_session: AsyncSession):
    """Re-running the detector updates the existing gap rather than duplicating it."""
    s = await _build_scenario(db_session)
    await _add_co_result(db_session, s, above=2, total=10, avg="41.50", is_attained=False)
    detector = CQIGapDetector(db_session)

    await detector.sync_for_section_offering(s["offering_id"], s["org_id"])
    await detector.sync_for_section_offering(s["offering_id"], s["org_id"])
    await detector.sync_for_section_offering(s["offering_id"], s["org_id"])

    gaps = (
        await db_session.execute(
            select(COAttainmentGap).where(
                COAttainmentGap.section_offering_id == s["offering_id"]
            )
        )
    ).scalars().all()
    assert len(gaps) == 1


async def test_gap_closes_when_recompute_shows_attainment(db_session: AsyncSession):
    """Marks corrected upward → the gap closes and records when."""
    s = await _build_scenario(db_session)
    await _add_co_result(db_session, s, above=2, total=10, avg="41.50", is_attained=False)
    detector = CQIGapDetector(db_session)
    await detector.sync_for_section_offering(s["offering_id"], s["org_id"])

    result = (
        await db_session.execute(
            select(COAttainmentResult).where(
                COAttainmentResult.section_offering_id == s["offering_id"]
            )
        )
    ).scalar_one()
    result.students_above_threshold = 9
    result.average_attainment_pct = Decimal("78.00")
    result.is_attained = True
    await db_session.flush()

    await detector.sync_for_section_offering(s["offering_id"], s["org_id"])

    gap = await _co_gap(db_session, s)
    assert gap.status == "CLOSED"
    assert gap.resolved_at is not None


async def test_closed_gap_reopens_if_attainment_regresses(db_session: AsyncSession):
    """A closed gap re-opens when a later recompute drops back below threshold."""
    s = await _build_scenario(db_session)
    await _add_co_result(db_session, s, above=9, total=10, avg="78.00", is_attained=True)
    detector = CQIGapDetector(db_session)
    await detector.sync_for_section_offering(s["offering_id"], s["org_id"])

    result = (
        await db_session.execute(
            select(COAttainmentResult).where(
                COAttainmentResult.section_offering_id == s["offering_id"]
            )
        )
    ).scalar_one()
    result.is_attained = False
    result.students_above_threshold = 3
    await db_session.flush()
    await detector.sync_for_section_offering(s["offering_id"], s["org_id"])
    gap = await _co_gap(db_session, s)
    assert gap.status == "OPEN"

    # Close it, then regress again.
    result.is_attained = True
    result.students_above_threshold = 9
    await db_session.flush()
    await detector.sync_for_section_offering(s["offering_id"], s["org_id"])
    assert (await _co_gap(db_session, s)).status == "CLOSED"

    result.is_attained = False
    result.students_above_threshold = 1
    await db_session.flush()
    await detector.sync_for_section_offering(s["offering_id"], s["org_id"])
    gap = await _co_gap(db_session, s)
    assert gap.status == "OPEN"
    assert gap.resolved_at is None


async def test_waived_gap_is_not_reopened_by_recompute(db_session: AsyncSession):
    """A documented waiver survives later recomputation."""
    s = await _build_scenario(db_session)
    await _add_co_result(db_session, s, above=2, total=10, avg="41.50", is_attained=False)
    detector = CQIGapDetector(db_session)
    await detector.sync_for_section_offering(s["offering_id"], s["org_id"])

    gap = await _co_gap(db_session, s)
    gap.status = "WAIVED"
    gap.waiver_reason = "Cohort sat a rescheduled exam; tracked outside the platform."
    await db_session.flush()

    await detector.sync_for_section_offering(s["offering_id"], s["org_id"])
    assert (await _co_gap(db_session, s)).status == "WAIVED"


async def test_custom_curriculum_threshold_is_recorded(db_session: AsyncSession):
    """The gap snapshots the curriculum's threshold, not a hardcoded 50."""
    s = await _build_scenario(db_session, threshold=Decimal("60.00"))
    await _add_co_result(db_session, s, above=5, total=10, avg="55.00", is_attained=False)

    await CQIGapDetector(db_session).sync_for_section_offering(s["offering_id"], s["org_id"])

    gap = await _co_gap(db_session, s)
    assert gap.threshold_pct == Decimal("60.00")
    assert gap.attainment_pct == Decimal("50.00")


async def test_zero_students_does_not_divide_by_zero(db_session: AsyncSession):
    """An empty cohort reports 0% rather than raising."""
    s = await _build_scenario(db_session)
    await _add_co_result(db_session, s, above=0, total=0, avg="0.00", is_attained=False)

    await CQIGapDetector(db_session).sync_for_section_offering(s["offering_id"], s["org_id"])

    gap = await _co_gap(db_session, s)
    assert gap.attainment_pct == Decimal("0.00")


# ── PO gap roll-up ────────────────────────────────────────────────────────────

async def test_po_gap_aggregates_across_offerings(db_session: AsyncSession):
    """
    PO gaps roll up to program + term: two offerings averaging 40% leave the PO
    unattained even though one of them individually cleared the bar.
    """
    s = await _build_scenario(db_session)

    second = SectionOffering(
        organization_id=s["org_id"],
        curriculum_id=s["curriculum_id"],
        batch_id=s["batch_id"],
        course_id=s["course_id"],
        academic_term_id=s["term_id"],
        section_id=s["section_id"],
    )
    # Same course/term but a distinct section keeps the offering unique.
    another_section = Section(organization_id=s["org_id"], name=f"S2{uuid.uuid4().hex[:6]}")
    db_session.add(another_section)
    await db_session.flush()
    second.section_id = another_section.id
    db_session.add(second)
    await db_session.flush()

    for offering_id, pct, attained in (
        (s["offering_id"], Decimal("20.00"), False),
        (second.id, Decimal("60.00"), True),
    ):
        db_session.add(
            POAttainmentResult(
                organization_id=s["org_id"],
                section_offering_id=offering_id,
                program_outcome_id=s["po_id"],
                attainment_pct=pct,
                contributing_co_count=1,
                students_above_threshold=1,
                total_students=10,
                is_attained=attained,
            )
        )
    await db_session.flush()

    await CQIGapDetector(db_session).sync_for_section_offering(s["offering_id"], s["org_id"])

    gap = (
        await db_session.execute(
            select(POAttainmentGap).where(POAttainmentGap.program_id == s["program_id"])
        )
    ).scalar_one()
    assert gap.status == "OPEN"
    assert gap.aggregate_attainment_pct == Decimal("40.00")  # mean of 20 and 60
    assert gap.contributing_offering_count == 2
    assert gap.attained_offering_count == 1
    assert gap.academic_term_id == s["term_id"]


async def test_po_above_threshold_creates_no_gap(db_session: AsyncSession):
    """A PO whose mean clears 50% is not flagged."""
    s = await _build_scenario(db_session)
    db_session.add(
        POAttainmentResult(
            organization_id=s["org_id"],
            section_offering_id=s["offering_id"],
            program_outcome_id=s["po_id"],
            attainment_pct=Decimal("75.00"),
            contributing_co_count=1,
            students_above_threshold=8,
            total_students=10,
            is_attained=True,
        )
    )
    await db_session.flush()

    await CQIGapDetector(db_session).sync_for_section_offering(s["offering_id"], s["org_id"])

    gaps = (
        await db_session.execute(
            select(POAttainmentGap).where(POAttainmentGap.program_id == s["program_id"])
        )
    ).scalars().all()
    assert gaps == []


# ── API surface ───────────────────────────────────────────────────────────────

async def test_summary_requires_permission(client: AsyncClient):
    resp = await client.get("/api/v1/cqi/summary")
    assert resp.status_code in (401, 403)


async def test_admin_can_read_gap_lists(client: AsyncClient, auth_headers: dict):
    for path in ("/api/v1/cqi/gaps/co", "/api/v1/cqi/gaps/po"):
        resp = await client.get(path, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json(), list)


async def test_summary_returns_status_counts(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/cqi/summary", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body["co_gaps"]) == {"open", "addressed", "closed", "waived"}
    assert set(body["po_gaps"]) == {"open", "addressed", "closed", "waived"}


async def test_teacher_can_read_but_not_waive(
    client: AsyncClient, teacher_auth_headers: dict
):
    """Section Teachers hold cqi.read but not cqi.gap.waive."""
    read = await client.get("/api/v1/cqi/gaps/co", headers=teacher_auth_headers)
    assert read.status_code == 200, read.text

    waive = await client.post(
        f"/api/v1/cqi/gaps/co/{uuid.uuid4()}/waive",
        headers=teacher_auth_headers,
        json={"reason": "Attempting to waive without the permission."},
    )
    assert waive.status_code == 403


async def test_waiving_unknown_gap_returns_404(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        f"/api/v1/cqi/gaps/co/{uuid.uuid4()}/waive",
        headers=auth_headers,
        json={"reason": "This gap does not exist in the database."},
    )
    assert resp.status_code == 404


async def test_waiver_reason_is_required(client: AsyncClient, auth_headers: dict):
    """A waiver without a substantive reason is rejected — it is the audit record."""
    resp = await client.post(
        f"/api/v1/cqi/gaps/co/{uuid.uuid4()}/waive",
        headers=auth_headers,
        json={"reason": "too short"},
    )
    assert resp.status_code == 422


async def test_invalid_status_filter_is_rejected(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/v1/cqi/gaps/co?gap_status=BOGUS", headers=auth_headers
    )
    assert resp.status_code == 422
