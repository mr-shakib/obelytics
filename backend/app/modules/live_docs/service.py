"""
Rules for the /docs page: who may see it and when, drafts and publishing, versions,
team photos and the Markdown export.
"""
import io
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.ai.models import FEATURES as AI_FEATURES
from app.modules.live_docs import defaults
from app.modules.live_docs.live import SIGNALS
from app.modules.live_docs.models import (
    DocsSection,
    DocsSectionVersion,
    DocsSettings,
    DocsTeamMember,
)
from app.modules.live_docs.schemas import (
    AdminSection,
    PublicSection,
    SettingsOut,
    SettingsUpdate,
    TeamMemberOut,
    Visibility,
)

PHOTO_SIDE = 480
UNPROCESSABLE = 422
MAX_PHOTO_BYTES = 8 * 1024 * 1024
FEATURE_STATUSES = ("live", "beta", "upcoming", "planned")
GROUP_ORDER = ("pitch", "product", "technical", "operations")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(value: datetime | None) -> str:
    if not value:
        return ""
    from zoneinfo import ZoneInfo

    local = value.astimezone(ZoneInfo(settings.DOCS_TIMEZONE))
    return local.strftime("%d %b %Y, %H:%M") + f" ({settings.DOCS_TIMEZONE})"


def public_url() -> str:
    origins = settings.ALLOWED_ORIGINS_LIST
    base = origins[0] if origins else "http://localhost:3000"
    return base.rstrip("/") + "/docs"


# ── Visibility ──────────────────────────────────────────────────────────────────


def window_end(row: DocsSettings) -> datetime | None:
    if row.schedule_mode == "window":
        return row.ends_at
    if row.schedule_mode == "duration" and row.starts_at and row.duration_minutes:
        return row.starts_at + timedelta(minutes=row.duration_minutes)
    return None


def visibility(row: DocsSettings, now: datetime | None = None) -> Visibility:
    now = now or _now()
    start = row.starts_at if row.schedule_mode != "always" else None
    end = window_end(row)
    if not row.is_enabled:
        return Visibility(state="disabled", is_visible=False, starts_at=start, ends_at=end,
                          message="This page is not available right now.")
    if start and now < start:
        return Visibility(state="not_started", is_visible=False, starts_at=start, ends_at=end,
                          message=f"This page opens on {_fmt(start)}.")
    if end and now > end:
        return Visibility(state="ended", is_visible=False, starts_at=start, ends_at=end,
                          message=f"This page closed on {_fmt(end)}.")
    return Visibility(state="live", is_visible=True, starts_at=start, ends_at=end,
                      message="Published.")


def settings_out(row: DocsSettings) -> SettingsOut:
    start, end = defaults.default_window(_now())
    return SettingsOut(
        is_enabled=row.is_enabled, schedule_mode=row.schedule_mode, starts_at=row.starts_at,
        ends_at=row.ends_at, duration_minutes=row.duration_minutes, team_name=row.team_name,
        timezone=settings.DOCS_TIMEZONE, default_starts_at=start, default_ends_at=end,
        updated_at=row.updated_at,
    )


# ── Section data, checked per kind ──────────────────────────────────────────────


def _text(value: Any, field: str, max_len: int, required: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise HTTPException(UNPROCESSABLE, f"{field} must be text")
    value = value.strip()
    if required and not value:
        raise HTTPException(UNPROCESSABLE, f"{field} is required")
    if len(value) > max_len:
        raise HTTPException(UNPROCESSABLE,
                            f"{field} is longer than {max_len} characters")
    return value


def _url(value: Any, field: str) -> str:
    value = _text(value, field, 500)
    if value and not re.match(r"^https?://", value):
        raise HTTPException(UNPROCESSABLE, f"{field} must start with https://")
    return value


def _items(data: dict, limit: int) -> list[dict]:
    items = data.get("items", [])
    if not isinstance(items, list) or len(items) > limit:
        raise HTTPException(UNPROCESSABLE, f"items must be a list of at most {limit}")
    if not all(isinstance(i, dict) for i in items):
        raise HTTPException(UNPROCESSABLE, "each item must be an object")
    return items


def clean_data(kind: str, data: dict | None) -> dict:
    data = data or {}
    if not isinstance(data, dict):
        raise HTTPException(UNPROCESSABLE, "data must be an object")
    if kind == "diagram":
        return {"mermaid": _text(data.get("mermaid"), "Diagram", 20_000)}
    if kind == "demo":
        return {"video_url": _url(data.get("video_url"), "Video link"),
                "demo_url": _url(data.get("demo_url"), "Demo link")}
    if kind == "features":
        rows = []
        for item in _items(data, 150):
            state = item.get("status") or "planned"
            if state not in FEATURE_STATUSES:
                raise HTTPException(UNPROCESSABLE, f"Unknown status {state!r}")
            signal = item.get("signal") or None
            if signal is not None and signal not in SIGNALS:
                raise HTTPException(UNPROCESSABLE, f"Unknown live signal {signal!r}")
            ai_feature = item.get("ai_feature") or None
            if ai_feature is not None and ai_feature not in AI_FEATURES:
                raise HTTPException(UNPROCESSABLE, f"Unknown AI feature {ai_feature!r}")
            rows.append({
                "name": _text(item.get("name"), "Feature name", 120, required=True),
                "area": _text(item.get("area"), "Area", 60),
                "status": state,
                "description": _text(item.get("description"), "Description", 400),
                "signal": signal,
                "ai_feature": ai_feature,
            })
        return {"items": rows}
    if kind == "changelog":
        return {"items": [
            {
                "version": _text(item.get("version"), "Version", 40, required=True),
                "date": _text(item.get("date"), "Date", 20),
                "title": _text(item.get("title"), "Title", 150, required=True),
                "notes": _text(item.get("notes"), "Notes", 1000),
            }
            for item in _items(data, 300)
        ]}
    return {}


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50]
    return slug or "section"


# ── Rows → schemas ──────────────────────────────────────────────────────────────


def team_out(member: DocsTeamMember) -> TeamMemberOut:
    photo_url = (
        f"{settings.API_V1_PREFIX}/docs/team/{member.id}/photo?v={member.photo_version}"
        if member.photo else None
    )
    return TeamMemberOut(id=member.id, full_name=member.full_name, role=member.role,
                         email=member.email, position=member.position, photo_url=photo_url)


def admin_section(row: DocsSection) -> AdminSection:
    has_changes = (
        row.published_version == 0
        or row.draft_title != row.published_title
        or row.draft_body != row.published_body
        or (row.draft_data or {}) != (row.published_data or {})
    )
    return AdminSection(
        id=row.id, key=row.key, group=row.group, kind=row.kind, position=row.position,
        is_visible=row.is_visible, is_builtin=row.is_builtin, draft_title=row.draft_title,
        draft_body=row.draft_body, draft_data=row.draft_data or {},
        published_title=row.published_title, published_body=row.published_body,
        published_data=row.published_data, published_version=row.published_version,
        published_at=row.published_at, has_changes=has_changes, updated_at=row.updated_at,
    )


def public_section(row: DocsSection) -> PublicSection:
    return PublicSection(
        key=row.key, group=row.group, kind=row.kind, title=row.published_title or row.draft_title,
        body=row.published_body or "", data=row.published_data or {},
        version=row.published_version, published_at=row.published_at,
    )


def _ordered(rows: list[DocsSection]) -> list[DocsSection]:
    return sorted(rows, key=lambda r: (GROUP_ORDER.index(r.group) if r.group in GROUP_ORDER else 9,
                                       r.position, r.key))


# ── Service ─────────────────────────────────────────────────────────────────────


class LiveDocsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_defaults(self) -> None:
        """Create the settings row and any missing built-in section. Safe to run concurrently."""
        has_settings = (await self.session.execute(select(DocsSettings.id))).scalar()
        keys = set((await self.session.execute(select(DocsSection.key))).scalars())
        missing = [d for d in defaults.SECTIONS if d["key"] not in keys]
        if has_settings and not missing:
            return
        now = _now()
        if not has_settings:
            start, end = defaults.default_window(now)
            await self.session.execute(
                pg_insert(DocsSettings)
                .values(id=1, is_enabled=True, schedule_mode="window", starts_at=start, ends_at=end)
                .on_conflict_do_nothing(index_elements=["id"])
            )
        if missing:
            order = {d["key"]: i for i, d in enumerate(defaults.SECTIONS)}
            rows = [
                {
                    "key": d["key"], "section_group": d["group"], "kind": d["kind"],
                    "position": order[d["key"]] * 10, "is_visible": True, "is_builtin": True,
                    "draft_title": d["title"], "draft_body": d["body"], "draft_data": d["data"],
                    "published_title": d["title"], "published_body": d["body"],
                    "published_data": d["data"], "published_version": 1, "published_at": now,
                }
                for d in missing
            ]
            inserted = (await self.session.execute(
                pg_insert(DocsSection.__table__).values(rows)
                .on_conflict_do_nothing(constraint="uq_docs_sections_key")
                .returning(DocsSection.__table__.c.id, DocsSection.__table__.c.key)
            )).all()
            by_key = {d["key"]: d for d in missing}
            if inserted:
                await self.session.execute(pg_insert(DocsSectionVersion.__table__).values([
                    {"section_id": sid, "version": 1, "title": by_key[key]["title"],
                     "body": by_key[key]["body"], "data": by_key[key]["data"], "published_at": now}
                    for sid, key in inserted
                ]))
        await self.session.commit()

    async def settings_row(self) -> DocsSettings:
        await self.ensure_defaults()
        return (await self.session.execute(select(DocsSettings).where(DocsSettings.id == 1))).scalar_one()

    async def sections(self) -> list[DocsSection]:
        await self.ensure_defaults()
        return _ordered(list((await self.session.execute(select(DocsSection))).scalars()))

    async def team(self) -> list[DocsTeamMember]:
        rows = (await self.session.execute(
            select(DocsTeamMember).order_by(DocsTeamMember.position, DocsTeamMember.created_at)
        )).scalars()
        return list(rows)

    async def require_visible(self) -> DocsSettings:
        row = await self.settings_row()
        state = visibility(row)
        if not state.is_visible:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=state.model_dump(mode="json"))
        return row

    # Settings

    async def update_settings(self, body: SettingsUpdate, user_id: UUID) -> DocsSettings:
        row = await self.settings_row()
        row.is_enabled = body.is_enabled
        row.schedule_mode = body.schedule_mode
        if body.schedule_mode != "always":
            row.starts_at = body.starts_at
        row.ends_at = body.ends_at if body.schedule_mode == "window" else None
        row.duration_minutes = body.duration_minutes if body.schedule_mode == "duration" else None
        row.team_name = (body.team_name or "").strip() or None
        row.updated_by_user_id = user_id
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def reset_window(self, user_id: UUID) -> DocsSettings:
        row = await self.settings_row()
        row.schedule_mode = "window"
        row.starts_at, row.ends_at = defaults.default_window(_now())
        row.duration_minutes = None
        row.updated_by_user_id = user_id
        await self.session.commit()
        await self.session.refresh(row)
        return row

    # Sections

    async def section(self, section_id: UUID) -> DocsSection:
        row = await self.session.get(DocsSection, section_id)
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Section not found")
        return row

    async def create_section(self, title: str, group: str, user_id: UUID) -> DocsSection:
        base = _slug(title)
        keys = set((await self.session.execute(select(DocsSection.key))).scalars())
        key, n = base, 2
        while key in keys:
            key, n = f"{base}-{n}", n + 1
        last = (await self.session.execute(
            select(func.max(DocsSection.position)).where(DocsSection.group == group)
        )).scalar() or 0
        row = DocsSection(key=key, group=group, kind="markdown", position=last + 10,
                          is_visible=True, is_builtin=False, draft_title=title.strip(),
                          draft_body="", draft_data={}, updated_by_user_id=user_id)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def save_draft(self, section_id: UUID, title: str, body: str, data: dict | None,
                         user_id: UUID) -> DocsSection:
        row = await self.section(section_id)
        row.draft_title = title.strip()
        row.draft_body = body
        if data is not None:
            row.draft_data = clean_data(row.kind, data)
        row.updated_by_user_id = user_id
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def set_visible(self, section_id: UUID, is_visible: bool) -> DocsSection:
        row = await self.section(section_id)
        row.is_visible = is_visible
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def _publish(self, row: DocsSection, user_id: UUID, now: datetime) -> None:
        version = row.published_version + 1
        row.published_title = row.draft_title
        row.published_body = row.draft_body
        row.published_data = row.draft_data or {}
        row.published_version = version
        row.published_at = now
        self.session.add(DocsSectionVersion(
            section_id=row.id, version=version, title=row.draft_title, body=row.draft_body,
            data=row.draft_data or {}, published_by_user_id=user_id, published_at=now,
        ))

    async def publish(self, section_id: UUID, user_id: UUID) -> DocsSection:
        row = await self.section(section_id)
        await self._publish(row, user_id, _now())
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def publish_all(self, user_id: UUID) -> int:
        now = _now()
        count = 0
        for row in await self.sections():
            if admin_section(row).has_changes:
                await self._publish(row, user_id, now)
                count += 1
        await self.session.commit()
        return count

    async def discard_draft(self, section_id: UUID) -> DocsSection:
        row = await self.section(section_id)
        if row.published_version == 0:
            raise HTTPException(status.HTTP_409_CONFLICT, "This section has never been published")
        row.draft_title = row.published_title or row.draft_title
        row.draft_body = row.published_body or ""
        row.draft_data = row.published_data or {}
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def versions(self, section_id: UUID) -> list[DocsSectionVersion]:
        await self.section(section_id)
        return list((await self.session.execute(
            select(DocsSectionVersion).where(DocsSectionVersion.section_id == section_id)
            .order_by(DocsSectionVersion.version.desc())
        )).scalars())

    async def restore(self, section_id: UUID, version: int, user_id: UUID) -> DocsSection:
        row = await self.section(section_id)
        old = (await self.session.execute(
            select(DocsSectionVersion).where(
                DocsSectionVersion.section_id == section_id, DocsSectionVersion.version == version,
            )
        )).scalar_one_or_none()
        if not old:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Version not found")
        row.draft_title, row.draft_body, row.draft_data = old.title, old.body, old.data
        row.updated_by_user_id = user_id
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete_section(self, section_id: UUID) -> None:
        row = await self.section(section_id)
        if row.is_builtin:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                "Built-in sections can be hidden but not deleted")
        await self.session.delete(row)
        await self.session.commit()

    async def reorder_sections(self, ids: list[UUID]) -> None:
        rows = {r.id: r for r in (await self.session.execute(
            select(DocsSection).where(DocsSection.id.in_(ids))
        )).scalars()}
        if len(rows) != len(set(ids)):
            raise HTTPException(UNPROCESSABLE, "Unknown section in the order")
        for i, section_id in enumerate(ids):
            rows[section_id].position = (i + 1) * 10
        await self.session.commit()

    # Team

    async def member(self, member_id: UUID) -> DocsTeamMember:
        row = await self.session.get(DocsTeamMember, member_id)
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Team member not found")
        return row

    async def add_member(self, full_name: str, role: str, email: str,
                         photo: bytes | None) -> DocsTeamMember:
        last = (await self.session.execute(select(func.max(DocsTeamMember.position)))).scalar() or 0
        row = DocsTeamMember(**_member_fields(full_name, role, email), position=last + 10)
        if photo:
            row.photo, row.photo_version = process_photo(photo), 1
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update_member(self, member_id: UUID, full_name: str, role: str,
                            email: str) -> DocsTeamMember:
        row = await self.member(member_id)
        for k, v in _member_fields(full_name, role, email).items():
            setattr(row, k, v)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def set_photo(self, member_id: UUID, photo: bytes | None) -> DocsTeamMember:
        row = await self.member(member_id)
        row.photo = process_photo(photo) if photo else None
        row.photo_version += 1
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete_member(self, member_id: UUID) -> None:
        await self.session.delete(await self.member(member_id))
        await self.session.commit()

    async def reorder_team(self, ids: list[UUID]) -> None:
        rows = {r.id: r for r in (await self.session.execute(
            select(DocsTeamMember).where(DocsTeamMember.id.in_(ids))
        )).scalars()}
        if len(rows) != len(set(ids)):
            raise HTTPException(UNPROCESSABLE, "Unknown team member in the order")
        for i, member_id in enumerate(ids):
            rows[member_id].position = (i + 1) * 10
        await self.session.commit()


def _member_fields(full_name: str, role: str, email: str) -> dict[str, str]:
    email = _text(email, "Email", 255, required=True)
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(UNPROCESSABLE, "Enter a valid email address")
    return {
        "full_name": _text(full_name, "Full name", 150, required=True),
        "role": _text(role, "Role", 150, required=True),
        "email": email,
    }


def process_photo(raw: bytes) -> bytes:
    """Any common image → a centred square, PHOTO_SIDE px, WebP. Same frame for everyone."""
    if len(raw) > MAX_PHOTO_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "The photo must be under 8 MB")
    try:
        image = Image.open(io.BytesIO(raw))
        image = ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(UNPROCESSABLE,
                            "Upload a JPEG, PNG or WebP image") from None
    image = ImageOps.fit(image, (PHOTO_SIDE, PHOTO_SIDE), Image.Resampling.LANCZOS,
                         centering=(0.5, 0.4))
    out = io.BytesIO()
    image.save(out, format="WEBP", quality=86, method=6)
    return out.getvalue()


# ── Markdown export ─────────────────────────────────────────────────────────────

GROUP_TITLES = {
    "pitch": "Pitch deck", "product": "Product", "technical": "Technical documentation",
    "operations": "Operations",
}


def _cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def export_markdown(sections: list[PublicSection], team: list[TeamMemberOut],
                    team_name: str | None, live: dict[str, Any] | None) -> str:
    usage = (live or {}).get("usage", {})
    lines = [
        "# Obelytics — documentation",
        "",
        f"_Exported {_fmt(_now())} from {public_url()}. Live figures are a snapshot at export time._",
        "",
    ]
    current_group = None
    for s in sections:
        if s.group != current_group:
            current_group = s.group
            lines += [f"## {GROUP_TITLES.get(s.group, s.group.title())}", ""]
        lines += [f"### {s.title}", ""]
        if s.body.strip():
            lines += [s.body.strip(), ""]
        if s.kind == "diagram" and s.data.get("mermaid"):
            lines += ["```mermaid", s.data["mermaid"].strip(), "```", ""]
        elif s.kind == "demo" and s.data.get("video_url"):
            lines += [f"Video: {s.data['video_url']}", ""]
        elif s.kind == "features":
            lines += ["| Feature | Area | Status | Live usage |", "|---|---|---|---|"]
            for item in s.data.get("items", []):
                sig = usage.get(item.get("signal") or "", {})
                count = (sig.get("real", 0) + sig.get("demo", 0)) if sig else ""
                lines.append(f"| {_cell(item['name'])} | {_cell(item.get('area'))} | "
                             f"{_cell(item['status'])} | {_cell(count)} |")
            lines.append("")
        elif s.kind == "changelog":
            for item in s.data.get("items", []):
                lines.append(f"- **{item['version']}** ({item.get('date', '')}) — "
                             f"{item['title']}. {item.get('notes', '')}".rstrip())
            lines.append("")
        elif s.kind == "team":
            if team_name:
                lines += [f"**{team_name}**", ""]
            lines += [f"- **{m.full_name}**, {m.role} — {m.email}" for m in team] or ["- (none yet)"]
            lines.append("")
        elif s.kind in ("traction", "analytics") and usage:
            lines += ["| Live figure | Real institutions | Demo (synthetic) |", "|---|---|---|"]
            for row in usage.values():
                lines.append(f"| {_cell(row['label'])} | {row['real']} | {row['demo']} |")
            lines.append("")
        elif s.kind == "api" and live:
            lines += [f"Live: {live['api']['endpoints']} endpoints in {live['api']['modules']} "
                      f"modules; MCP tools: {', '.join(t['name'] for t in live['api']['mcp_tools'])}.",
                      ""]
    return "\n".join(lines).rstrip() + "\n"
