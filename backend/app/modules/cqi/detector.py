"""
CQI Gap Detector — turns attainment results into tracked gap records.

Runs after every attainment computation. Reads the persisted attainment rows
rather than taking values from the engine, so it produces the same result
whether it follows a fresh computation or a recompute.

Does NOT call session.commit() — the caller owns the transaction, matching the
contract of AttainmentEngine.
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attainment.models import COAttainmentResult, POAttainmentResult
from app.modules.cqi.models import COAttainmentGap, POAttainmentGap
from app.modules.curriculum.models import Curriculum, SectionOffering

# The engine treats a program outcome as attained when its offering-level
# attainment exceeds 50% (see AttainmentEngine, PO computation step). Program
# level roll-up applies the same bar to the mean across offerings.
PO_THRESHOLD_PCT = Decimal("50.00")


class CQIGapDetector:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def sync_for_section_offering(
        self, section_offering_id: UUID, org_id: UUID
    ) -> None:
        """
        Refresh CO gaps for this offering and PO gaps for its program + term.
        Safe to call when nothing was computed — it simply finds no results.
        """
        offering = await self._session.get(SectionOffering, section_offering_id)
        if offering is None:
            return

        curriculum = await self._session.get(Curriculum, offering.curriculum_id)
        if curriculum is None:
            return

        await self._sync_co_gaps(
            section_offering_id, org_id, Decimal(str(curriculum.threshold_co_score_pct))
        )
        await self._sync_po_gaps(
            org_id, curriculum.program_id, offering.academic_term_id
        )

    # ── CO gaps (scoped to the section offering) ──────────────────────────────

    async def _sync_co_gaps(
        self, section_offering_id: UUID, org_id: UUID, threshold_pct: Decimal
    ) -> None:
        results = list(
            (
                await self._session.execute(
                    select(COAttainmentResult).where(
                        COAttainmentResult.section_offering_id == section_offering_id
                    )
                )
            ).scalars().all()
        )
        if not results:
            return

        existing = {
            gap.course_outcome_id: gap
            for gap in (
                await self._session.execute(
                    select(COAttainmentGap).where(
                        COAttainmentGap.section_offering_id == section_offering_id
                    )
                )
            ).scalars().all()
        }

        for result in results:
            gap = existing.get(result.course_outcome_id)
            cohort_pct = self._cohort_pct(
                result.students_above_threshold, result.total_students
            )

            if result.is_attained:
                if gap is not None:
                    self._close_if_open(gap)
                continue

            if gap is None:
                self._session.add(
                    COAttainmentGap(
                        organization_id=org_id,
                        section_offering_id=section_offering_id,
                        course_outcome_id=result.course_outcome_id,
                        attainment_pct=cohort_pct,
                        average_score_pct=result.average_attainment_pct,
                        threshold_pct=threshold_pct,
                        students_above_threshold=result.students_above_threshold,
                        total_students=result.total_students,
                        status="OPEN",
                    )
                )
                continue

            # Still unattained — refresh the measurement. A gap that was closed
            # by an earlier recompute re-opens; a waived one keeps its waiver.
            gap.attainment_pct = cohort_pct
            gap.average_score_pct = result.average_attainment_pct
            gap.threshold_pct = threshold_pct
            gap.students_above_threshold = result.students_above_threshold
            gap.total_students = result.total_students
            if gap.status == "CLOSED":
                gap.status = "OPEN"
                gap.resolved_at = None

        await self._session.flush()

    # ── PO gaps (rolled up to program + academic term) ────────────────────────

    async def _sync_po_gaps(
        self, org_id: UUID, program_id: UUID, academic_term_id: UUID
    ) -> None:
        """
        Aggregate every offering in this program + term that measured each PO,
        then flag the POs whose mean attainment sits at or below the threshold.
        """
        rows = list(
            (
                await self._session.execute(
                    select(POAttainmentResult)
                    .join(
                        SectionOffering,
                        SectionOffering.id == POAttainmentResult.section_offering_id,
                    )
                    .join(Curriculum, Curriculum.id == SectionOffering.curriculum_id)
                    .where(
                        and_(
                            Curriculum.program_id == program_id,
                            SectionOffering.academic_term_id == academic_term_id,
                            POAttainmentResult.organization_id == org_id,
                        )
                    )
                )
            ).scalars().all()
        )
        if not rows:
            return

        totals: dict[UUID, list[POAttainmentResult]] = {}
        for row in rows:
            totals.setdefault(row.program_outcome_id, []).append(row)

        existing = {
            gap.program_outcome_id: gap
            for gap in (
                await self._session.execute(
                    select(POAttainmentGap).where(
                        and_(
                            POAttainmentGap.program_id == program_id,
                            POAttainmentGap.academic_term_id == academic_term_id,
                        )
                    )
                )
            ).scalars().all()
        }

        for po_id, po_rows in totals.items():
            offering_count = len(po_rows)
            mean_pct = round(
                sum(Decimal(str(r.attainment_pct)) for r in po_rows)
                / Decimal(str(offering_count)),
                2,
            )
            attained_count = sum(1 for r in po_rows if r.is_attained)
            is_attained = mean_pct > PO_THRESHOLD_PCT
            gap = existing.get(po_id)

            if is_attained:
                if gap is not None:
                    self._close_if_open(gap)
                continue

            if gap is None:
                self._session.add(
                    POAttainmentGap(
                        organization_id=org_id,
                        program_id=program_id,
                        academic_term_id=academic_term_id,
                        program_outcome_id=po_id,
                        aggregate_attainment_pct=mean_pct,
                        threshold_pct=PO_THRESHOLD_PCT,
                        contributing_offering_count=offering_count,
                        attained_offering_count=attained_count,
                        status="OPEN",
                    )
                )
                continue

            gap.aggregate_attainment_pct = mean_pct
            gap.threshold_pct = PO_THRESHOLD_PCT
            gap.contributing_offering_count = offering_count
            gap.attained_offering_count = attained_count
            if gap.status == "CLOSED":
                gap.status = "OPEN"
                gap.resolved_at = None

        await self._session.flush()

    # ── shared ────────────────────────────────────────────────────────────────

    @staticmethod
    def _cohort_pct(students_above_threshold: int, total_students: int) -> Decimal:
        """Share of the cohort at or above the CO threshold — the gated figure."""
        if total_students <= 0:
            return Decimal("0.00")
        return round(
            Decimal(str(students_above_threshold))
            / Decimal(str(total_students))
            * Decimal("100"),
            2,
        )

    @staticmethod
    def _close_if_open(gap: COAttainmentGap | POAttainmentGap) -> None:
        """
        The outcome is now attained. Close an outstanding gap; leave a waived
        one alone so the documented waiver stays the record of what happened.
        """
        if gap.status in ("OPEN", "ADDRESSED"):
            gap.status = "CLOSED"
            gap.resolved_at = datetime.now(timezone.utc)
