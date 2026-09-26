from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cqi.exceptions import GapNotFoundError, GapNotWaivableError
from app.modules.cqi.models import COAttainmentGap, POAttainmentGap
from app.modules.cqi.repository import COGapRepository, POGapRepository
from app.modules.cqi.schemas import CQISummary, GapStatusCounts

_WAIVABLE_STATUSES = ("OPEN", "ADDRESSED")


class CQIGapService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._co_repo = COGapRepository(session)
        self._po_repo = POGapRepository(session)

    # ── reads ─────────────────────────────────────────────────────────────────

    async def list_co_gaps(
        self,
        org_id: UUID,
        program_id: UUID | None = None,
        academic_term_id: UUID | None = None,
        status: str | None = None,
    ) -> list[COAttainmentGap]:
        return await self._co_repo.list_gaps(org_id, program_id, academic_term_id, status)

    async def list_co_gaps_for_offering(
        self, org_id: UUID, section_offering_id: UUID
    ) -> list[COAttainmentGap]:
        return await self._co_repo.list_by_offering(org_id, section_offering_id)

    async def list_po_gaps(
        self,
        org_id: UUID,
        program_id: UUID | None = None,
        academic_term_id: UUID | None = None,
        status: str | None = None,
    ) -> list[POAttainmentGap]:
        return await self._po_repo.list_gaps(org_id, program_id, academic_term_id, status)

    async def get_summary(
        self,
        org_id: UUID,
        program_id: UUID | None = None,
        academic_term_id: UUID | None = None,
    ) -> CQISummary:
        co_counts = await self._co_repo.count_by_status(org_id, program_id, academic_term_id)
        po_counts = await self._po_repo.count_by_status(org_id, program_id, academic_term_id)
        return CQISummary(
            program_id=program_id,
            academic_term_id=academic_term_id,
            co_gaps=_to_counts(co_counts),
            po_gaps=_to_counts(po_counts),
        )

    # ── writes ────────────────────────────────────────────────────────────────

    async def waive_co_gap(
        self, org_id: UUID, gap_id: UUID, user_id: UUID, reason: str
    ) -> COAttainmentGap:
        gap = await self._co_repo.get(org_id, gap_id)
        if gap is None:
            raise GapNotFoundError(f"No CO attainment gap {gap_id}")
        return await self._waive(gap, user_id, reason)

    async def waive_po_gap(
        self, org_id: UUID, gap_id: UUID, user_id: UUID, reason: str
    ) -> POAttainmentGap:
        gap = await self._po_repo.get(org_id, gap_id)
        if gap is None:
            raise GapNotFoundError(f"No PO attainment gap {gap_id}")
        return await self._waive(gap, user_id, reason)

    async def _waive(self, gap, user_id: UUID, reason: str):
        if gap.status not in _WAIVABLE_STATUSES:
            raise GapNotWaivableError(
                f"Gap is {gap.status}; only OPEN or ADDRESSED gaps can be waived"
            )
        gap.status = "WAIVED"
        gap.waived_by_user_id = user_id
        gap.waiver_reason = reason
        gap.resolved_at = datetime.now(timezone.utc)
        self._session.add(gap)
        await self._session.commit()
        await self._session.refresh(gap)
        return gap


def _to_counts(counts: dict[str, int]) -> GapStatusCounts:
    return GapStatusCounts(
        open=counts.get("OPEN", 0),
        addressed=counts.get("ADDRESSED", 0),
        closed=counts.get("CLOSED", 0),
        waived=counts.get("WAIVED", 0),
    )
