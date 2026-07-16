from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=255)
    context: dict[str, Any] = Field(default_factory=dict)


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: Literal["ACTIVE", "ARCHIVED"] | None = None
    context: dict[str, Any] | None = None


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    status: str
    context: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    status: str
    model: str | None
    token_usage: dict[str, Any] | None
    tool_calls: list[dict[str, Any]] | dict[str, Any] | None
    citations: list[dict[str, Any]] | dict[str, Any] | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
