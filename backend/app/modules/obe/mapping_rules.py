"""
The rules every CO-PO link must follow, in one place.

The mapping validator and the AI mapping suggestions both use these checks, so a
suggestion is judged exactly like a mapping a teacher made by hand.

- K rule:   when a PO lists required knowledge profiles (obe.po_knowledge_profiles),
            a CO mapped to it must be mapped to at least one of them. A PO with no
            knowledge profiles listed is not checked.
- CEP rule: a CO mapped to PO1–PO7 must be mapped to a complex engineering problem.
- CEA rule: a CO mapped to PO10 must be mapped to a complex engineering activity.
"""
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.obe.models import (
    COCAMapping,
    COCPMapping,
    COKPMapping,
    POKnowledgeProfile,
    ProgramOutcome,
)
from app.modules.ref_data.models import KnowledgeProfile

_PO_CODE = re.compile(r"PO(\d+)")


def po_number(code: str) -> int | None:
    match = _PO_CODE.fullmatch(code or "")
    return int(match.group(1)) if match else None


def needs_cep(po_code: str) -> bool:
    number = po_number(po_code)
    return number is not None and 1 <= number <= 7


def needs_cea(po_code: str) -> bool:
    return po_number(po_code) == 10


@dataclass(frozen=True)
class LinkCheck:
    missing_kp: bool
    missing_cep: bool
    missing_cea: bool
    # The PO's required knowledge profiles; empty when the PO lists none.
    required_kp_ids: frozenset[UUID] = frozenset()

    @property
    def ok(self) -> bool:
        return not (self.missing_kp or self.missing_cep or self.missing_cea)


def check_link(
    po_code: str,
    *,
    po_kp_ids: Iterable[UUID],
    co_kp_ids: Iterable[UUID],
    co_has_cep: bool,
    co_has_cea: bool,
) -> LinkCheck:
    required = frozenset(po_kp_ids)
    return LinkCheck(
        missing_kp=bool(required) and not (required & set(co_kp_ids)),
        missing_cep=needs_cep(po_code) and not co_has_cep,
        missing_cea=needs_cea(po_code) and not co_has_cea,
        required_kp_ids=required,
    )


@dataclass
class MappingFacts:
    """What the rules need to know about a set of COs and POs, loaded in a few queries."""

    po_codes: dict[UUID, str] = field(default_factory=dict)
    po_kp_ids: dict[UUID, set[UUID]] = field(default_factory=dict)
    co_kp_ids: dict[UUID, set[UUID]] = field(default_factory=dict)
    cos_with_cep: set[UUID] = field(default_factory=set)
    cos_with_cea: set[UUID] = field(default_factory=set)
    kp_codes: dict[UUID, str] = field(default_factory=dict)

    def check(
        self,
        co_id: UUID,
        po_id: UUID,
        *,
        added_kp_ids: Iterable[UUID] = (),
        adds_cep: bool = False,
        adds_cea: bool = False,
    ) -> LinkCheck:
        """Check one link, optionally as if the given CO mappings were added first."""
        return check_link(
            self.po_codes.get(po_id, ""),
            po_kp_ids=self.po_kp_ids.get(po_id, set()),
            co_kp_ids=self.co_kp_ids.get(co_id, set()) | set(added_kp_ids),
            co_has_cep=adds_cep or co_id in self.cos_with_cep,
            co_has_cea=adds_cea or co_id in self.cos_with_cea,
        )

    def required_kp_codes(self, po_id: UUID) -> list[str]:
        return sorted(
            (self.kp_codes.get(kp_id, "?") for kp_id in self.po_kp_ids.get(po_id, set())),
            key=natural_key,
        )


def natural_key(code: str) -> list:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", code)]


async def load_facts(
    session: AsyncSession, co_ids: Iterable[UUID], po_ids: Iterable[UUID]
) -> MappingFacts:
    co_ids, po_ids = set(co_ids), set(po_ids)
    facts = MappingFacts()
    if po_ids:
        rows = await session.execute(
            select(ProgramOutcome.id, ProgramOutcome.code).where(ProgramOutcome.id.in_(po_ids))
        )
        facts.po_codes = {po_id: code for po_id, code in rows.all()}
        rows = await session.execute(
            select(POKnowledgeProfile.program_outcome_id, POKnowledgeProfile.knowledge_profile_id)
            .where(POKnowledgeProfile.program_outcome_id.in_(po_ids))
        )
        for po_id, kp_id in rows.all():
            facts.po_kp_ids.setdefault(po_id, set()).add(kp_id)
    if co_ids:
        rows = await session.execute(
            select(COKPMapping.course_outcome_id, COKPMapping.knowledge_profile_id)
            .where(COKPMapping.course_outcome_id.in_(co_ids))
        )
        for co_id, kp_id in rows.all():
            facts.co_kp_ids.setdefault(co_id, set()).add(kp_id)
        rows = await session.execute(
            select(COCPMapping.course_outcome_id).where(COCPMapping.course_outcome_id.in_(co_ids))
        )
        facts.cos_with_cep = {row[0] for row in rows.all()}
        rows = await session.execute(
            select(COCAMapping.course_outcome_id).where(COCAMapping.course_outcome_id.in_(co_ids))
        )
        facts.cos_with_cea = {row[0] for row in rows.all()}

    kp_ids = set().union(*facts.po_kp_ids.values(), *facts.co_kp_ids.values())
    if kp_ids:
        rows = await session.execute(
            select(KnowledgeProfile.id, KnowledgeProfile.code).where(KnowledgeProfile.id.in_(kp_ids))
        )
        facts.kp_codes = {kp_id: code for kp_id, code in rows.all()}
    return facts
