"""
Evidence-weighted CO attainment: the official figure next to the same figure
computed only from questions the audit does not contradict.

A parallel, explained view — it never changes marks or the official attainment.
The arithmetic is the marksheet's own (assessment MarksheetService.get_attainment):
a student's CO score is marks obtained on that CO's questions over their maximum;
the CO is attained when the share of students at or above the threshold reaches
the threshold.

Each question's evidence status comes from its current audit:
- SUPPORTED    — aligned, or the right CO at another Bloom level, or the teacher
                 disagreed with a "different CO" verdict and gave a reason
- CONTRADICTED — the audit found it tests a different CO (pending review or accepted)
- UNVERIFIED   — no audit yet, or the AI was not sure; counted (benefit of the doubt)
"""
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

SUPPORTED, CONTRADICTED, UNVERIFIED = "SUPPORTED", "CONTRADICTED", "UNVERIFIED"


def evidence_status(alignment: str | None, review_status: str | None) -> str:
    if alignment is None or alignment == "ABSTAINED":
        return UNVERIFIED
    if alignment == "MISALIGNED":
        return SUPPORTED if review_status == "OVERRIDDEN" else CONTRADICTED
    return SUPPORTED


@dataclass(frozen=True)
class QuestionInput:
    id: UUID
    co_id: UUID
    max_marks: Decimal
    status: str


@dataclass
class COStats:
    max_marks: Decimal
    average_pct: Decimal
    students_above: int
    total_students: int
    is_attained: bool

    @property
    def attained_share_pct(self) -> Decimal:
        if self.total_students == 0:
            return Decimal("0")
        return Decimal(self.students_above) / Decimal(self.total_students) * Decimal("100")


def co_attainment(
    questions: list[QuestionInput],
    marks: dict[tuple[UUID, UUID], Decimal | None],
    enrollment_ids: list[UUID],
    threshold: Decimal,
    *,
    evidence_only: bool = False,
) -> dict[UUID, COStats]:
    """
    marks: (question_id, enrollment_id) → marks obtained, or None when absent or blank.
    evidence_only: leave out CONTRADICTED questions. A CO whose questions are all
    contradicted has no evidence and is missing from the result.
    """
    used = [q for q in questions if not (evidence_only and q.status == CONTRADICTED)]
    co_max: dict[UUID, Decimal] = defaultdict(Decimal)
    for q in used:
        co_max[q.co_id] += q.max_marks

    total = len(enrollment_ids)
    result: dict[UUID, COStats] = {}
    for co_id, max_marks in co_max.items():
        co_questions = [q for q in used if q.co_id == co_id]
        scores = []
        for enrollment_id in enrollment_ids:
            obtained = sum(
                (marks.get((q.id, enrollment_id)) or Decimal("0") for q in co_questions), Decimal("0")
            )
            scores.append(obtained / max_marks * Decimal("100") if max_marks > 0 else Decimal("0"))
        above = sum(1 for s in scores if s >= threshold)
        result[co_id] = COStats(
            max_marks=max_marks,
            average_pct=round(sum(scores, Decimal("0")) / total, 2) if total else Decimal("0"),
            students_above=above,
            total_students=total,
            is_attained=(Decimal(above) / Decimal(total) * Decimal("100") >= threshold) if total else False,
        )
    return result
