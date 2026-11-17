from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# ── Shared ────────────────────────────────────────────────────────────────────


class BloomRef(BaseModel):
    id: UUID
    code: str
    name: str


class SuggestionMeta(BaseModel):
    suggestion_id: UUID
    model: str
    prompt_version: str


# ── Draft COs ─────────────────────────────────────────────────────────────────


class DraftRequest(BaseModel):
    curriculum_id: UUID
    course_id: UUID
    count: int = Field(default=5, ge=1, le=8)
    instruction: str | None = Field(default=None, max_length=500)


class DraftedOutcome(BaseModel):
    statement: str
    bloom_levels: list[BloomRef]
    rationale: str
    # Found by code, not by the model: vague verb, two outcomes in one, repeats a CO…
    warnings: list[str]


class DraftResponse(SuggestionMeta):
    outcomes: list[DraftedOutcome]


# ── Refine a CO ───────────────────────────────────────────────────────────────


class RefineRequest(BaseModel):
    curriculum_id: UUID
    course_id: UUID
    statement: str = Field(min_length=3, max_length=2000)
    bloom_level_ids: list[UUID] = Field(default_factory=list)
    instruction: str | None = Field(default=None, max_length=500)
    # The CO being edited, if any: left out of the "repeats another CO" check.
    course_outcome_id: UUID | None = None

    @field_validator("statement")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Statement is empty")
        return value


class RefineResponse(SuggestionMeta):
    statement: str
    bloom_levels: list[BloomRef]
    changes: list[str]
    warnings: list[str]
    # The same checks on the teacher's own statement, to show what improved.
    original_warnings: list[str]


# ── CO-PO mapping suggestions ─────────────────────────────────────────────────


class MappingSuggestRequest(BaseModel):
    curriculum_id: UUID
    course_id: UUID
    # Map only these COs (e.g. one just added); omit to map every CO of the course.
    course_outcome_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=50)


class SuggestedAttribute(BaseModel):
    id: UUID
    code: str
    justification: str
    # True: the CO is already mapped to it. False: applying the link adds it.
    already_mapped: bool


class SuggestedLink(BaseModel):
    index: int
    course_outcome_id: UUID
    co_code: str
    program_outcome_id: UUID
    po_code: str
    weight: int
    justification: str
    confidence: float | None
    knowledge_profiles: list[SuggestedAttribute]
    complex_problems: list[SuggestedAttribute]
    complex_activities: list[SuggestedAttribute]
    # Mapping rules the link breaks; such a link cannot be applied.
    issues: list[str]
    # Worth a look, but not blocking.
    warnings: list[str]
    already_mapped: bool
    can_apply: bool


class ExistingLink(BaseModel):
    co_code: str
    po_code: str


class MappingSuggestResponse(SuggestionMeta):
    # The COs this suggestion covers (all of the course's COs unless the request named some).
    course_outcome_codes: list[str]
    links: list[SuggestedLink]
    # POs with no required knowledge profiles set, so the K rule cannot check them.
    pos_without_knowledge_profiles: list[str]
    # Links the course already has that the AI did not suggest.
    existing_not_suggested: list[ExistingLink]


class ApplyItem(BaseModel):
    index: int = Field(ge=0)
    # The teacher may change the weight or wording before applying.
    weight: int | None = Field(default=None, ge=1, le=3)
    justification: str | None = Field(default=None, max_length=2000)


class ApplyRequest(BaseModel):
    items: list[ApplyItem] = Field(min_length=1, max_length=200)


class ApplyResponse(BaseModel):
    mapping_set_id: UUID
    applied: list[int]
    already_mapped: list[int]
    added_knowledge_profiles: int
    added_complex_problems: int
    added_complex_activities: int


# ── Teacher's decision ────────────────────────────────────────────────────────


class DecisionRequest(BaseModel):
    decision: Literal["ACCEPTED", "EDITED", "PARTIAL", "REJECTED"]
    # e.g. {"accepted": [0, 2], "edited": [2]} for drafts
    detail: dict | None = None

    @field_validator("detail")
    @classmethod
    def _small(cls, value: dict | None) -> dict | None:
        if value is not None and len(str(value)) > 20_000:
            raise ValueError("detail is too large")
        return value


class DecisionResponse(BaseModel):
    suggestion_id: UUID
    decision: str


# ── Course outline import ─────────────────────────────────────────────────────


class OutlineOutcome(BaseModel):
    code: str
    statement: str
    bloom_levels: list[BloomRef]
    # False: the outline gives no level, so the AI chose one from the task.
    bloom_stated: bool
    # Already a CO of this course: importing leaves the existing one unchanged.
    exists: bool
    warnings: list[str]


class OutlineTopic(BaseModel):
    week: int | None = Field(default=None, ge=1, le=52)
    topic: str = Field(min_length=1, max_length=500)


class OutlineCurrent(BaseModel):
    """What the course has now, so the teacher sees what an import would replace."""

    has_description: bool
    objectives: int
    outcome_codes: list[str]
    lesson_items: int


class OutlinePreview(SuggestionMeta):
    filename: str
    course_code: str | None
    course_title: str | None
    description: str | None
    objectives: list[str]
    outcomes: list[OutlineOutcome]
    topics: list[OutlineTopic]
    warnings: list[str]
    current: OutlineCurrent


class OutlineOutcomeIn(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    statement: str = Field(min_length=3, max_length=2000)
    bloom_level_ids: list[UUID] = Field(default_factory=list)


class OutlineApplyRequest(BaseModel):
    """Each part is applied only when present (the teacher may have edited it)."""

    description: str | None = Field(default=None, max_length=5000)
    objectives: list[str] | None = Field(default=None, max_length=30)
    outcomes: list[OutlineOutcomeIn] | None = Field(default=None, max_length=30)
    topics: list[OutlineTopic] | None = Field(default=None, max_length=60)


class OutlineApplyResponse(BaseModel):
    description: bool
    objectives: int
    outcomes_added: list[str]
    outcomes_skipped: list[str]
    syllabus: bool
    lesson_items: int
    lesson_plan_kept: bool
