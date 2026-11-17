from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    tool: str | None
    ref: str
    detail: str
    # True only when the cited tool really returned this ref (checked in code).
    verified: bool


class Intervention(BaseModel):
    id: str
    action: str
    kind: str
    effort: str
    success_measure: str
    decision: Literal["ACCEPTED", "REJECTED"] | None = None
    note: str | None = None


class Diagnosis(BaseModel):
    id: str
    co: str
    problem: str
    likely_cause: str
    confidence: float | None
    evidence: list[EvidenceItem]
    # False when none of its evidence could be found in the tool results.
    supported: bool
    interventions: list[Intervention]


class AgentStep(BaseModel):
    thought: str | None = None
    tool: str | None = None
    co: str | None = None
    action: str | None = None
    # fixed: always run; model: chosen by the AI; code: stopped by a guard.
    chosen_by: str
    result: dict | None = None


class PlanResponse(BaseModel):
    id: UUID
    section_offering_id: UUID
    summary: str
    follow_up: str | None
    diagnoses: list[Diagnosis]
    steps: list[AgentStep]
    model: str
    prompt_version: str
    created_at: datetime


class InterventionDecision(BaseModel):
    decision: Literal["ACCEPTED", "REJECTED"]
    note: str | None = Field(default=None, max_length=1000)
