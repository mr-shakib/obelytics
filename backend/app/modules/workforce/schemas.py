from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Skill(BaseModel):
    name: str
    category: Literal["technical", "professional"]
    required: bool


class PostingCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    employer: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=500)
    posted_on: date | None = None
    text: str = Field(min_length=40, max_length=20_000)


class PostingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    title: str
    employer: str | None
    source: str | None
    posted_on: date | None
    text: str
    # None until the AI has read the posting (it is retried at the next analysis).
    skills: list[Skill] | None
    skills_model: str | None
    skills_prompt_version: str | None
    created_at: datetime


class AnalysisRequest(BaseModel):
    curriculum_id: UUID


class CourseRef(BaseModel):
    id: UUID
    code: str
    title: str


class OutcomeRef(BaseModel):
    ref: str
    co_id: UUID
    co_code: str
    course_id: UUID
    course_code: str
    course_title: str
    statement: str


class SkillCoverage(BaseModel):
    skill: str
    # Other spellings from the postings merged into this skill.
    aliases: list[str] = []
    category: str
    # How many postings ask for it, and how many of those require it.
    postings: int
    required: int
    example_titles: list[str]
    coverage: Literal["covered", "partial", "gap", "unjudged"]
    outcomes: list[OutcomeRef]
    # POs reached through the CO-PO mapping of the covering COs.
    program_outcomes: list[str]
    reason: str
    suggested_course: CourseRef | None
    notes: list[str]


class POMarketDemand(BaseModel):
    code: str
    statement: str
    skills: list[str]
    demand: int


class AnalysisSummary(BaseModel):
    skills: int
    covered: int
    partial: int
    gap: int
    unjudged: int
    coverage_pct: float | None


class AnalysisResponse(BaseModel):
    id: UUID
    program_id: UUID
    curriculum_id: UUID
    posting_count: int
    skills: list[SkillCoverage]
    summary: AnalysisSummary
    program_outcomes: list[POMarketDemand]
    model: str
    prompt_version: str
    created_at: datetime


# ── Importing real postings ──────────────────────────────────────────────────

class ImportUrlsRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=20)


class ImportProblem(BaseModel):
    source: str
    error: str


class ImportResult(BaseModel):
    added: list[PostingResponse]
    errors: list[ImportProblem]


# ── A student's verified skills (no AI: their own results against the analysis) ──

class SkillEvidence(BaseModel):
    course_code: str
    course_title: str
    co_code: str
    statement: str
    attainment_pct: float
    attained: bool


class StudentSkill(BaseModel):
    skill: str
    category: str
    postings: int
    required: int
    # verified: the student attained a CO that develops it; developing: they took it
    # but did not attain it; not_yet: no completed course of theirs develops it.
    status: Literal["verified", "developing", "not_yet"]
    evidence: list[SkillEvidence]
    program_outcomes: list[str]


class StudentSkillsSummary(BaseModel):
    verified: int
    developing: int
    not_yet: int
    top_n: int
    top_verified: int


class StudentSkillsResponse(BaseModel):
    analysis_date: datetime | None
    posting_count: int
    skills: list[StudentSkill]
    summary: StudentSkillsSummary
