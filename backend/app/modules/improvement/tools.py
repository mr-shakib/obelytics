"""
The improvement agent's tools: fixed, read-only and scoped to one section the user may see.

Each tool computes its numbers in code from the database and returns aggregates only —
averages, shares and indices over the class, never a student's identity or own marks.
No tool runs model-written queries. Every result lists the `refs` it contains (CO codes,
question labels, weeks), so the plan's citations can be checked afterwards.
"""
import json
import re
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assessment.models import MarksheetMark, MarksheetQuestion, StudentEnrollment
from app.modules.curriculum.models import (
    CourseLessonPlanItem,
    CourseLessonPlanItemCO,
    SectionOffering,
)
from app.modules.integrity.models import QuestionAudit
from app.modules.integrity.schemas import EvidenceAttainment
from app.modules.obe.mapping_rules import natural_key
from app.modules.obe.models import CourseOutcome
from app.modules.ref_data.models import BloomLevel

TOOL_DESCRIPTIONS = {
    "outcome_attainment": (
        "Every CO's attainment in this section: the official (reported) figure, the figure "
        "supported by the integrity audit, and how many of its questions the audit contradicts."
    ),
    "question_stats": (
        "For one CO (give \"co\"): each question mapped to it — marks, class average, share of "
        "students scoring at least half, share scoring zero, discrimination (top 27% vs bottom "
        "27% of the class), the declared Bloom level and the auditor's judgment."
    ),
    "lesson_plan": (
        "For one CO (give \"co\"): the weeks, topics, teaching activities and assessment strategy "
        "linked to it in the lesson plan."
    ),
    "previous_plan": (
        "The improvement plan made for this course in an earlier section, which interventions "
        "the teacher accepted, and how each CO's attainment then compares with now."
    ),
}
TOOLS_NEEDING_CO = {"question_stats", "lesson_plan"}
MAX_RESULT_CHARS = 3500


@dataclass
class ToolResult:
    tool: str
    co: str | None
    data: dict
    refs: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        text = json.dumps(self.data, ensure_ascii=False, default=str)
        return text if len(text) <= MAX_RESULT_CHARS else text[: MAX_RESULT_CHARS - 20] + " …(truncated)"


_REF = re.compile(r"[^a-z0-9]+")


def ref_key(ref: str | None) -> str:
    return _REF.sub("", (ref or "").lower())


def _pct(part: float, whole: float) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


class SectionTools:
    def __init__(
        self,
        session: AsyncSession,
        offering: SectionOffering,
        evidence: EvidenceAttainment,
        previous: "PreviousPlan | None",
    ) -> None:
        self.session = session
        self.offering = offering
        self.evidence = evidence
        self.previous = previous
        self._outcomes: dict[str, CourseOutcome] = {}
        self._loaded = False

    async def _load(self) -> None:
        if self._loaded:
            return
        rows = (await self.session.execute(select(CourseOutcome).where(and_(
            CourseOutcome.course_id == self.offering.course_id,
            CourseOutcome.curriculum_id == self.offering.curriculum_id,
        )))).scalars().all()
        self._outcomes = {co.code.upper(): co for co in rows}
        self._loaded = True

    async def co_codes(self) -> list[str]:
        await self._load()
        return sorted((co.code for co in self._outcomes.values()), key=natural_key)

    async def run(self, tool: str, co: str | None = None) -> ToolResult:
        await self._load()
        if tool == "outcome_attainment":
            return self._outcome_attainment()
        if tool == "previous_plan":
            return self._previous_plan()
        outcome = self._outcomes.get((co or "").strip().upper())
        if outcome is None:
            return ToolResult(tool, co, {"error": f"Unknown CO {co!r}. Use one of {await self.co_codes()}."})
        if tool == "question_stats":
            return await self._question_stats(outcome)
        if tool == "lesson_plan":
            return await self._lesson_plan(outcome)
        return ToolResult(tool, co, {"error": f"Unknown tool {tool!r}"})

    # ── outcome_attainment ────────────────────────────────────────────────────

    def _outcome_attainment(self) -> ToolResult:
        ev = self.evidence
        outcomes = []
        for o in ev.outcomes:
            outcomes.append({
                "co": o.course_outcome.code,
                "reported_attained_share_pct": o.reported.attained_share_pct,
                "reported_average_pct": o.reported.average_pct,
                "reported_attained": o.reported.is_attained,
                "supported_attained_share_pct": o.evidence.attained_share_pct if o.evidence else None,
                "audit_verdict": o.verdict,
                "questions": len(o.questions),
                "contradicted_questions": sum(q.status == "CONTRADICTED" for q in o.questions),
            })
        return ToolResult(
            "outcome_attainment", None,
            {"threshold_pct": ev.threshold_pct, "students": ev.total_students, "outcomes": outcomes},
            refs=[o["co"] for o in outcomes],
        )

    # ── question_stats ────────────────────────────────────────────────────────

    async def _question_stats(self, outcome: CourseOutcome) -> ToolResult:
        session = self.session
        questions = (await session.execute(select(MarksheetQuestion).where(
            MarksheetQuestion.section_offering_id == self.offering.id
        ).order_by(MarksheetQuestion.exam_type, MarksheetQuestion.order_index))).scalars().all()
        enrolled = set((await session.execute(select(StudentEnrollment.id).where(and_(
            StudentEnrollment.section_offering_id == self.offering.id,
            StudentEnrollment.status == "ACTIVE",
        )))).scalars().all())
        marks = (await session.execute(select(
            MarksheetMark.question_id, MarksheetMark.student_enrollment_id, MarksheetMark.marks_obtained,
        ).where(
            MarksheetMark.question_id.in_([q.id for q in questions]),
            MarksheetMark.is_absent.is_(False),
            MarksheetMark.marks_obtained.is_not(None),
        ))).all()
        by_question: dict[UUID, dict[UUID, float]] = {}
        totals: dict[UUID, float] = {}
        for question_id, enrollment_id, value in marks:
            if enrollment_id not in enrolled:
                continue
            by_question.setdefault(question_id, {})[enrollment_id] = float(value)
            totals[enrollment_id] = totals.get(enrollment_id, 0.0) + float(value)

        # Top and bottom 27% of the class by total marks, for the discrimination index.
        ranked = sorted(totals, key=totals.get)
        group = max(1, round(len(ranked) * 0.27)) if ranked else 0
        bottom, top = set(ranked[:group]), set(ranked[-group:])

        audits = {a.question_id: a for a in (await session.execute(select(QuestionAudit).where(
            QuestionAudit.question_id.in_([q.id for q in questions]), QuestionAudit.is_current.is_(True),
        ))).scalars().all()}
        level_ids = {q.declared_bloom_level_id for q in questions} | {a.ai_bloom_level_id for a in audits.values()}
        level_ids.discard(None)
        codes = dict((await session.execute(
            select(BloomLevel.id, BloomLevel.code).where(BloomLevel.id.in_(level_ids))
        )).all()) if level_ids else {}
        co_codes = {co.id: co.code for co in self._outcomes.values()}

        rows, refs = [], []
        for q in questions:
            if q.course_outcome_id != outcome.id:
                continue
            maximum = float(q.max_marks)
            scores = by_question.get(q.id, {})
            values = list(scores.values())

            def mean_pct(ids, scores=scores, maximum=maximum):
                picked = [scores[i] for i in ids if i in scores]
                return _pct(sum(picked) / len(picked), maximum) if picked else None

            top_pct, bottom_pct = mean_pct(top), mean_pct(bottom)
            audit = audits.get(q.id)
            rows.append({
                "question": q.label,
                "exam": q.exam_type,
                "max_marks": maximum,
                "answered": len(values),
                "average_pct": _pct(sum(values) / len(values), maximum) if values else None,
                "at_least_half_pct": _pct(sum(v >= maximum / 2 for v in values), len(values)),
                "zero_pct": _pct(sum(v == 0 for v in values), len(values)),
                "discrimination": (
                    round((top_pct - bottom_pct) / 100, 2)
                    if top_pct is not None and bottom_pct is not None else None
                ),
                "declared_bloom": codes.get(q.declared_bloom_level_id),
                "audit": None if audit is None else {
                    "alignment": audit.alignment,
                    "ai_bloom": codes.get(audit.ai_bloom_level_id),
                    "ai_co": co_codes.get(audit.ai_course_outcome_id),
                    "review": audit.review_status,
                },
                "wording": (q.question_text or "")[:300] or None,
            })
            refs += [q.label, f"{q.exam_type} {q.label}"]
        return ToolResult(
            "question_stats", outcome.code,
            {"co": outcome.code, "statement": outcome.statement, "questions": rows,
             "note": "Discrimination below 0.2 means strong and weak students scored alike."},
            refs=refs + [outcome.code],
        )

    # ── lesson_plan ───────────────────────────────────────────────────────────

    async def _lesson_plan(self, outcome: CourseOutcome) -> ToolResult:
        items = (await self.session.execute(select(CourseLessonPlanItem).where(and_(
            CourseLessonPlanItem.curriculum_id == self.offering.curriculum_id,
            CourseLessonPlanItem.course_id == self.offering.course_id,
        )).order_by(CourseLessonPlanItem.week_number, CourseLessonPlanItem.order_index))).scalars().all()
        linked = set((await self.session.execute(
            select(CourseLessonPlanItemCO.item_id).where(CourseLessonPlanItemCO.course_outcome_id == outcome.id)
        )).scalars().all())
        weeks = [
            {"week": i.week_number, "topic": i.topic[:200], "teaching": (i.tla or "")[:200] or None,
             "assessment": (i.assessment_strategy or "")[:200] or None}
            for i in items if i.id in linked
        ]
        return ToolResult(
            "lesson_plan", outcome.code,
            {"co": outcome.code, "linked_weeks": weeks, "total_weeks": len({i.week_number for i in items}),
             "note": None if weeks else "No lesson-plan week is linked to this CO."},
            refs=[f"Week {w['week']}" for w in weeks] + [outcome.code],
        )

    # ── previous_plan ─────────────────────────────────────────────────────────

    def _previous_plan(self) -> ToolResult:
        if self.previous is None:
            return ToolResult("previous_plan", None, {"found": False})
        return ToolResult("previous_plan", None, {"found": True, **self.previous.data},
                          refs=["previous plan", *self.previous.co_codes])


@dataclass
class PreviousPlan:
    data: dict
    co_codes: list[str]
