"""
Judge one exam question: which Bloom level it demands and which CO it exercises.

The question is judged several times independently — once greedily, the rest with
sampling — and the answers are combined by majority vote. Confidence is the share
of judgments that agree with the result, scaled by how sure those judgments said
they were; it is then calibrated (calibration.py). Agreement between independent
judgments is a better signal than a small model's stated confidence alone.

Shared by the background job and the gold-set script.
"""
import asyncio
from collections import Counter
from dataclasses import dataclass, field

from app.core.config import settings
from app.modules.ai.gateway import AIGateway
from app.modules.ai.providers import AIError
from app.modules.integrity.calibration import calibrate
from app.modules.integrity.prompts import AUDIT_PROMPT, AUDIT_PROMPT_VERSION, AUDIT_SCHEMA

SAMPLE_TEMPERATURE = 0.7
BLOOM_CODES = ("C1", "C2", "C3", "C4", "C5", "C6")


@dataclass
class Vote:
    bloom: str | None
    co: str | None
    confidence: float
    abstain: bool
    evidence: str | None
    rationale: str | None


@dataclass
class Judgment:
    bloom: str | None  # None when abstaining
    co: str | None
    raw_confidence: float
    confidence: float
    consistency: float
    abstain: bool
    evidence: str | None
    rationale: str | None
    votes: list[Vote] = field(default_factory=list)
    failed_samples: int = 0
    model: str | None = None
    calibration: str = "none"

    def details(self) -> dict:
        return {
            "method": "self-consistency",
            "samples": len(self.votes),
            "failed_samples": self.failed_samples,
            "consistency": round(self.consistency, 3),
            "calibration": self.calibration,
            "votes": [
                {"bloom": v.bloom, "co": v.co, "confidence": round(v.confidence, 3), "abstain": v.abstain}
                for v in self.votes
            ],
        }


def co_key(code: str | None) -> str:
    return (code or "").replace(" ", "").upper()


def _text(value, max_length: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:max_length] or None


def parse_vote(data) -> Vote:
    data = data if isinstance(data, dict) else {}
    bloom = str(data.get("bloom") or "").strip().upper()
    confidence = data.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        confidence = 0.0
    return Vote(
        bloom=bloom if bloom in BLOOM_CODES else None,
        co=co_key(data.get("co")) or None,
        confidence=min(max(float(confidence), 0.0), 1.0),
        abstain=bool(data.get("abstain")),
        evidence=_text(data.get("evidence"), 1000),
        rationale=_text(data.get("rationale"), 2000),
    )


def _majority(values: list, first) -> object:
    """Most common value; ties go to the greedy (first) judgment's value."""
    counts = Counter(values)
    best = max(counts.values())
    leaders = [value for value, count in counts.items() if count == best]
    return first if first in leaders else leaders[0]


def aggregate(votes: list[Vote]) -> Judgment:
    """Combine independent judgments. votes[0] is the greedy (temperature 0) one."""
    valid = [v for v in votes if not v.abstain and v.bloom]
    if not votes or len(valid) * 2 < len(votes) or not valid:
        return Judgment(
            bloom=None, co=None, raw_confidence=0.0, confidence=0.0,
            consistency=len(valid) / len(votes) if votes else 0.0, abstain=True,
            evidence=votes[0].evidence if votes else None,
            rationale=votes[0].rationale if votes else None, votes=votes,
        )
    first = valid[0]
    bloom = _majority([v.bloom for v in valid], first.bloom)
    co = _majority([v.co for v in valid], first.co)
    agreeing = [v for v in valid if v.bloom == bloom and v.co == co]
    consistency = len(agreeing) / len(votes)
    stated = sum(v.confidence for v in agreeing) / len(agreeing) if agreeing else 0.0
    raw = stated if len(votes) == 1 else consistency * stated
    # Explain with a judgment that matches the result, preferring the greedy one.
    explainer = agreeing[0] if agreeing else first
    return Judgment(
        bloom=bloom, co=co, raw_confidence=round(raw, 3), confidence=round(raw, 3),
        consistency=consistency, abstain=False,
        evidence=explainer.evidence, rationale=explainer.rationale, votes=votes,
    )


def build_audit_prompt(
    *,
    course: str,
    outcomes: str,
    label: str,
    marks: str,
    question: str,
    context: str | None = None,
    figure: str | None = None,
) -> str:
    parts = [context, question]
    if figure:
        parts.append(f"[Figure: {figure}]")
    return AUDIT_PROMPT.format(
        course=course,
        outcomes=outcomes or "(none recorded)",
        label=label,
        marks=marks,
        question="\n\n".join(part for part in parts if part),
    )


async def judge(gateway: AIGateway, prompt: str, samples: int | None = None) -> Judgment:
    samples = max(1, samples or settings.INTEGRITY_AUDIT_SAMPLES)
    calls = [
        gateway.complete_json(
            purpose="audit_question",
            prompt=prompt,
            schema=AUDIT_SCHEMA,
            prompt_version=AUDIT_PROMPT_VERSION,
            temperature=0.0 if i == 0 else SAMPLE_TEMPERATURE,
            seed=None if i == 0 else i,
        )
        for i in range(samples)
    ]
    results = await asyncio.gather(*calls, return_exceptions=True)
    completions = [r for r in results if not isinstance(r, BaseException)]
    errors = [r for r in results if isinstance(r, BaseException)]
    if not completions:
        error = errors[0]
        raise error if isinstance(error, AIError) else AIError(str(error))
    for error in errors:
        if not isinstance(error, AIError):
            raise error
    judgment = aggregate([parse_vote(c.data) for c in completions])
    judgment.failed_samples = len(errors)
    judgment.model = completions[0].model
    if not judgment.abstain:
        judgment.confidence, judgment.calibration = calibrate(judgment.raw_confidence, AUDIT_PROMPT_VERSION)
    return judgment


def judge_alignment(
    *,
    abstain: bool,
    confidence: float,
    ai_bloom_code: str | None,
    declared_bloom_code: str | None,
    ai_co_id,
    declared_co_id,
    min_confidence: float | None = None,
) -> str:
    """Compare the model's independent judgment with what the teacher declared."""
    threshold = settings.INTEGRITY_MIN_CONFIDENCE if min_confidence is None else min_confidence
    if abstain or ai_bloom_code is None or confidence < threshold:
        return "ABSTAINED"
    if declared_co_id is not None and ai_co_id != declared_co_id:
        return "MISALIGNED"
    if declared_bloom_code is not None and ai_bloom_code != declared_bloom_code:
        return "PARTIAL"
    return "ALIGNED"
