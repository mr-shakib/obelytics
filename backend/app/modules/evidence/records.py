"""
Evidence records for one curriculum, gathered by walking the outcome graph in code:
program outcomes → the course outcomes mapped to them → sections with marks → CO
attainment (reported and supported by the audit) → integrity audits → improvement plans,
plus the latest job-market analysis. Each record is a short, self-contained statement of
fact with its numbers, so a drafted sentence can be checked against what it cites.

Only class-level figures appear; no record names or describes an individual student.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assessment.models import MarksheetQuestion
from app.modules.authoring.context import program_outcomes_for
from app.modules.curriculum.models import AcademicTerm, Course, SectionOffering
from app.modules.improvement.models import ImprovementPlan
from app.modules.integrity.service import IntegrityService
from app.modules.obe.mapping_rules import natural_key
from app.modules.obe.models import COPOMappingEntry, COPOMappingSet, CourseOutcome
from app.modules.workforce.models import MarketAnalysis

MAX_SECTIONS = 8
MAX_RECORDS = 60


@dataclass
class Record:
    kind: str
    label: str
    text: str


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{round(float(value))}%"


async def gather_records(session: AsyncSession, organization_id: UUID, program_id: UUID,
                         curriculum_id: UUID) -> list[Record]:
    records: list[Record] = []

    # Program outcomes and the course outcomes mapped to them.
    pos = await program_outcomes_for(session, organization_id, program_id)
    links = (await session.execute(
        select(COPOMappingEntry.program_outcome_id, COPOMappingEntry.weight, CourseOutcome.code, Course.code)
        .join(COPOMappingSet, COPOMappingSet.id == COPOMappingEntry.mapping_set_id)
        .join(CourseOutcome, CourseOutcome.id == COPOMappingEntry.course_outcome_id)
        .join(Course, Course.id == CourseOutcome.course_id)
        .where(COPOMappingSet.curriculum_id == curriculum_id)
    )).all()
    by_po: dict[UUID, list[str]] = defaultdict(list)
    for po_id, weight, co_code, course_code in links:
        by_po[po_id].append(f"{course_code}/{co_code} (weight {weight})")
    for po in sorted(pos, key=lambda p: natural_key(p.code)):
        mapped = sorted(by_po.get(po.id, []), key=natural_key)
        courses = {m.split("/")[0] for m in mapped}
        text = (f"{po.statement.strip()} Mapped from {len(mapped)} course outcomes in {len(courses)} courses"
                + (f": {', '.join(mapped[:12])}{' …' if len(mapped) > 12 else ''}." if mapped else "."))
        records.append(Record("program_outcome", po.code, text))

    # Sections of this curriculum that have marksheet questions, newest term first.
    rows = (await session.execute(
        select(SectionOffering)
        .join(AcademicTerm, AcademicTerm.id == SectionOffering.academic_term_id)
        .where(SectionOffering.organization_id == organization_id, SectionOffering.curriculum_id == curriculum_id,
               SectionOffering.id.in_(select(distinct(MarksheetQuestion.section_offering_id))))
        .order_by(AcademicTerm.year.desc(), AcademicTerm.start_date.desc().nulls_last())
        .limit(MAX_SECTIONS)
    )).scalars().all()
    integrity = IntegrityService(session)
    for offering in rows:
        evidence = await integrity.evidence_attainment(offering)
        if evidence.total_students == 0:
            continue
        s = evidence.section
        where = f"{s.course_code} {s.course_title}, section {s.section_name}, {s.term_name}"
        for outcome in evidence.outcomes:
            reported = outcome.reported
            supported = outcome.evidence
            contradicted = sum(1 for q in outcome.questions if q.status == "CONTRADICTED")
            text = (
                f"{reported.students_above} of {reported.total_students} students reached the "
                f"{round(evidence.threshold_pct)}% threshold on {outcome.course_outcome.code} "
                f"({_pct(reported.attained_share_pct)}; {'attained' if reported.is_attained else 'not attained'}; "
                f"average {_pct(reported.average_pct)}). Counting only questions the audit supports: "
                + (f"{_pct(supported.attained_share_pct)} "
                   f"({'attained' if supported.is_attained else 'not attained'})" if supported else "no evidence left")
                + f"; {contradicted} of {len(outcome.questions)} questions test another outcome."
            )
            records.append(Record("co_attainment", f"{where}: {outcome.course_outcome.code}", text))
        for exam in ("MID", "FINAL"):
            summary = (await integrity.overview(offering, exam)).summary
            if summary.audited:
                records.append(Record("integrity_audit", f"{where}: {exam} paper audit", (
                    f"The AI auditor judged {summary.audited} of {summary.questions} questions: "
                    f"{summary.aligned} match their mapping, {summary.partial} test a different Bloom level, "
                    f"{summary.misaligned} test a different course outcome, {summary.abstained} not sure; "
                    f"{summary.audited - summary.pending_review} reviewed by the teacher."
                )))
        plan = (await session.execute(
            select(ImprovementPlan).where(ImprovementPlan.section_offering_id == offering.id)
            .order_by(ImprovementPlan.created_at.desc()).limit(1)
        )).scalar_one_or_none()
        if plan is not None:
            decisions = plan.decisions or {}
            accepted = [
                i["action"] for d in plan.diagnoses or [] for i in d.get("interventions", [])
                if decisions.get(i["id"], {}).get("decision") == "ACCEPTED"
            ]
            records.append(Record("improvement_plan", f"{where}: improvement plan", (
                f"Improvement plan of {plan.created_at.date().isoformat()}: {plan.summary.strip()} "
                + (f"Changes the teacher accepted: {'; '.join(accepted)}." if accepted
                   else "No proposed change has been accepted yet.")
            )))

    # The latest job-market analysis of this curriculum.
    market = (await session.execute(
        select(MarketAnalysis).where(and_(
            MarketAnalysis.organization_id == organization_id, MarketAnalysis.curriculum_id == curriculum_id,
        )).order_by(MarketAnalysis.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    if market is not None:
        summary = market.result.get("summary", {})
        skills = market.result.get("skills", [])
        gaps = [s["skill"] for s in skills if s.get("coverage") == "gap"][:6]
        covered = [s["skill"] for s in skills if s.get("coverage") == "covered"][:6]
        records.append(Record("market_analysis", f"Job-market analysis of {market.created_at.date().isoformat()}", (
            f"{market.posting_count} job postings compared with the curriculum's course outcomes: "
            f"{summary.get('coverage_pct', 'n/a')}% of skill demand covered "
            f"({summary.get('covered', 0)} skills covered, {summary.get('partial', 0)} partly, "
            f"{summary.get('gap', 0)} gaps). Covered: {', '.join(covered) or 'none'}. "
            f"Gaps: {', '.join(gaps) or 'none'}."
        )))
    return records[:MAX_RECORDS]
