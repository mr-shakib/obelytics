from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReferenceDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    filename: str
    passage_count: int
    created_at: datetime


class DraftRequest(BaseModel):
    curriculum_id: UUID
    criterion_title: str = Field(min_length=3, max_length=255)
    criterion_guidance: str | None = Field(default=None, max_length=4000)


class DraftSentence(BaseModel):
    text: str
    cites: list[str]
    gap: bool
    status: Literal["supported", "check"]
    issues: list[str]


class DraftSource(BaseModel):
    kind: str
    label: str
    text: str
    document_id: str | None = None


class DraftResponse(BaseModel):
    id: UUID
    program_id: UUID
    curriculum_id: UUID
    criterion_title: str
    criterion_guidance: str | None
    sentences: list[DraftSentence]
    missing: list[str]
    sources: dict[str, DraftSource]
    status: Literal["DRAFT", "ACCEPTED", "REJECTED"]
    edited_text: str | None
    model: str
    prompt_version: str
    created_at: datetime
    decided_at: datetime | None


class DraftDecision(BaseModel):
    decision: Literal["ACCEPTED", "REJECTED"]
    edited_text: str | None = Field(default=None, max_length=20_000)
