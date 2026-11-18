from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

ScheduleMode = Literal["always", "window", "duration"]
Group = Literal["pitch", "product", "technical", "operations"]
VisibilityState = Literal["live", "disabled", "not_started", "ended"]


class Visibility(BaseModel):
    state: VisibilityState
    is_visible: bool
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    message: str


class SettingsOut(BaseModel):
    is_enabled: bool
    schedule_mode: ScheduleMode
    starts_at: datetime | None
    ends_at: datetime | None
    duration_minutes: int | None
    team_name: str | None
    timezone: str
    default_starts_at: datetime
    default_ends_at: datetime
    updated_at: datetime | None


class SettingsUpdate(BaseModel):
    is_enabled: bool
    schedule_mode: ScheduleMode
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=60 * 24 * 366)
    team_name: str | None = Field(default=None, max_length=150)

    @model_validator(mode="after")
    def _check_schedule(self) -> "SettingsUpdate":
        if self.schedule_mode == "window":
            if not self.starts_at or not self.ends_at:
                raise ValueError("A date window needs a start and an end")
            if self.ends_at <= self.starts_at:
                raise ValueError("The window must end after it starts")
        if self.schedule_mode == "duration" and (not self.starts_at or not self.duration_minutes):
            raise ValueError("Duration-based publishing needs a start and a duration")
        return self


class TeamMemberOut(BaseModel):
    id: UUID
    full_name: str
    role: str
    email: str
    position: int
    photo_url: str | None


class PublicSection(BaseModel):
    key: str
    group: Group
    kind: str
    title: str
    body: str
    data: dict[str, Any]
    version: int
    published_at: datetime | None


class PublicDocs(BaseModel):
    product: str
    team_name: str | None
    visibility: Visibility
    sections: list[PublicSection]
    team: list[TeamMemberOut]
    generated_at: datetime


class AdminSection(BaseModel):
    id: UUID
    key: str
    group: Group
    kind: str
    position: int
    is_visible: bool
    is_builtin: bool
    draft_title: str
    draft_body: str
    draft_data: dict[str, Any]
    published_title: str | None
    published_body: str | None
    published_data: dict[str, Any] | None
    published_version: int
    published_at: datetime | None
    has_changes: bool
    updated_at: datetime | None


class AdminDocs(BaseModel):
    settings: SettingsOut
    visibility: Visibility
    sections: list[AdminSection]
    team: list[TeamMemberOut]
    public_url: str


class SectionDraftUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=60_000)
    data: dict[str, Any] | None = None


class SectionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    group: Group


class SectionVisibilityUpdate(BaseModel):
    is_visible: bool


class OrderUpdate(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=500)


class MemberUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    role: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=3, max_length=255)


class SectionVersionOut(BaseModel):
    version: int
    title: str
    body: str
    data: dict[str, Any]
    published_at: datetime
    published_by_user_id: UUID | None


class PublishResult(BaseModel):
    published: int
