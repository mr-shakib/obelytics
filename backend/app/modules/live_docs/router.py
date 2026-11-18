"""
/docs API. Public reads (`/docs/public`, `/live`, `/api-reference`, `/export.md`) answer
only while the page is published and inside its schedule; otherwise 403 with the reason.
Everything under `/docs/admin` is for Super Admins (optionally limited by DOCS_EDITOR_EMAILS).
"""
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_permission_manifest
from app.modules.audit.writer import write_audit_log
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.live_docs import live
from app.modules.live_docs.schemas import (
    AdminDocs,
    MemberUpdate,
    OrderUpdate,
    PublicDocs,
    SectionCreate,
    SectionDraftUpdate,
    SectionVersionOut,
    SectionVisibilityUpdate,
    SettingsUpdate,
)
from app.modules.live_docs.service import (
    LiveDocsService,
    admin_section,
    export_markdown,
    public_section,
    public_url,
    settings_out,
    team_out,
    visibility,
)

router = APIRouter(prefix="/docs", tags=["Docs page"])

Db = Annotated[AsyncSession, Depends(get_db)]


def _editor_emails() -> set[str]:
    return {e.strip().lower() for e in settings.DOCS_EDITOR_EMAILS.split(",") if e.strip()}


async def require_editor(
    manifest: Annotated[PermissionManifestResponse, Depends(get_permission_manifest)],
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    allowed = _editor_emails()
    if not manifest.is_super_admin or (allowed and user.email.lower() not in allowed):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only Super Admins can edit the docs page")
    return user


Editor = Annotated[User, Depends(require_editor)]


async def _admin_docs(svc: LiveDocsService) -> AdminDocs:
    row = await svc.settings_row()
    return AdminDocs(
        settings=settings_out(row), visibility=visibility(row),
        sections=[admin_section(s) for s in await svc.sections()],
        team=[team_out(m) for m in await svc.team()],
        public_url=public_url(),
    )


async def _public_docs(svc: LiveDocsService) -> PublicDocs:
    row = await svc.require_visible()
    return PublicDocs(
        product=settings.APP_NAME, team_name=row.team_name, visibility=visibility(row),
        sections=[public_section(s) for s in await svc.sections()
                  if s.is_visible and s.published_version > 0],
        team=[team_out(m) for m in await svc.team()],
        generated_at=datetime.now(timezone.utc),
    )


def _log(db: AsyncSession, user: User, action: str, entity_id: UUID, extra: dict | None = None):
    write_audit_log(db, entity_type="docs_page", entity_id=entity_id, action=action,
                    org_id=user.organization_id, actor_user_id=user.id, extra=extra)


# ── Public ──────────────────────────────────────────────────────────────────────


@router.get("/public", response_model=PublicDocs, summary="Published docs page")
async def get_public_docs(db: Db) -> PublicDocs:
    return await _public_docs(LiveDocsService(db))


@router.get("/live", summary="Live system, AI and usage figures")
async def get_live(db: Db, request: Request) -> dict:
    await LiveDocsService(db).require_visible()
    return await live.snapshot(db, request.app)


@router.get("/api-reference", summary="Every REST endpoint, grouped by module")
async def get_api_reference(db: Db, request: Request) -> dict:
    await LiveDocsService(db).require_visible()
    return live.api_reference(request.app)


@router.get("/export.md", response_class=PlainTextResponse, summary="The page as Markdown")
async def export_docs(db: Db, request: Request) -> PlainTextResponse:
    svc = LiveDocsService(db)
    docs = await _public_docs(svc)
    snapshot = await live.snapshot(db, request.app)
    body = export_markdown(docs.sections, docs.team, docs.team_name, snapshot)
    return PlainTextResponse(body, media_type="text/markdown; charset=utf-8", headers={
        "Content-Disposition": 'attachment; filename="obelytics-docs.md"',
    })


@router.get("/team/{member_id}/photo", summary="Team member photo (square WebP)")
async def get_team_photo(member_id: UUID, db: Db) -> Response:
    member = await LiveDocsService(db).member(member_id)
    if not member.photo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No photo")
    return Response(member.photo, media_type="image/webp",
                    headers={"Cache-Control": "public, max-age=31536000, immutable"})


# ── Admin ───────────────────────────────────────────────────────────────────────


@router.get("/admin", response_model=AdminDocs, summary="Docs page for editors (drafts included)")
async def get_admin_docs(db: Db, _: Editor) -> AdminDocs:
    return await _admin_docs(LiveDocsService(db))


@router.get("/admin/live", summary="Live figures for the editor's preview")
async def get_admin_live(db: Db, request: Request, _: Editor) -> dict:
    return await live.snapshot(db, request.app)


@router.get("/admin/api-reference", summary="Endpoint list for the editor's preview")
async def get_admin_api_reference(request: Request, _: Editor) -> dict:
    return live.api_reference(request.app)


@router.put("/admin/settings", response_model=AdminDocs, summary="Visibility and schedule")
async def update_settings(body: SettingsUpdate, db: Db, user: Editor) -> AdminDocs:
    svc = LiveDocsService(db)
    _log(db, user, "DOCS_SETTINGS_UPDATED", user.id, body.model_dump(mode="json"))
    await svc.update_settings(body, user.id)
    return await _admin_docs(svc)


@router.post("/admin/settings/reset-window", response_model=AdminDocs,
             summary="Back to the default June 10–14 window")
async def reset_window(db: Db, user: Editor) -> AdminDocs:
    svc = LiveDocsService(db)
    _log(db, user, "DOCS_SETTINGS_UPDATED", user.id, {"reset_window": True})
    await svc.reset_window(user.id)
    return await _admin_docs(svc)


@router.post("/admin/sections", response_model=AdminDocs, status_code=201,
             summary="Add a custom section")
async def create_section(body: SectionCreate, db: Db, user: Editor) -> AdminDocs:
    svc = LiveDocsService(db)
    await svc.ensure_defaults()
    await svc.create_section(body.title, body.group, user.id)
    return await _admin_docs(svc)


@router.put("/admin/sections-order", response_model=AdminDocs, summary="Reorder sections")
async def reorder_sections(body: OrderUpdate, db: Db, _: Editor) -> AdminDocs:
    svc = LiveDocsService(db)
    await svc.reorder_sections(body.ids)
    return await _admin_docs(svc)


@router.post("/admin/publish-all", response_model=AdminDocs, summary="Publish every changed draft")
async def publish_all(db: Db, user: Editor) -> AdminDocs:
    svc = LiveDocsService(db)
    _log(db, user, "DOCS_PUBLISHED", user.id, {"all": True})
    await svc.publish_all(user.id)
    return await _admin_docs(svc)


@router.put("/admin/sections/{section_id}", response_model=AdminDocs, summary="Save a draft")
async def save_draft(section_id: UUID, body: SectionDraftUpdate, db: Db, user: Editor) -> AdminDocs:
    svc = LiveDocsService(db)
    await svc.save_draft(section_id, body.title, body.body, body.data, user.id)
    return await _admin_docs(svc)


@router.put("/admin/sections/{section_id}/visibility", response_model=AdminDocs,
            summary="Show or hide a section")
async def set_section_visibility(section_id: UUID, body: SectionVisibilityUpdate, db: Db,
                                 _: Editor) -> AdminDocs:
    svc = LiveDocsService(db)
    await svc.set_visible(section_id, body.is_visible)
    return await _admin_docs(svc)


@router.post("/admin/sections/{section_id}/publish", response_model=AdminDocs,
             summary="Publish a section's draft")
async def publish_section(section_id: UUID, db: Db, user: Editor) -> AdminDocs:
    svc = LiveDocsService(db)
    _log(db, user, "DOCS_PUBLISHED", section_id)
    await svc.publish(section_id, user.id)
    return await _admin_docs(svc)


@router.post("/admin/sections/{section_id}/discard", response_model=AdminDocs,
             summary="Throw away a draft")
async def discard_draft(section_id: UUID, db: Db, _: Editor) -> AdminDocs:
    svc = LiveDocsService(db)
    await svc.discard_draft(section_id)
    return await _admin_docs(svc)


@router.get("/admin/sections/{section_id}/versions", response_model=list[SectionVersionOut],
            summary="Published versions of a section")
async def list_versions(section_id: UUID, db: Db, _: Editor) -> list[SectionVersionOut]:
    rows = await LiveDocsService(db).versions(section_id)
    return [SectionVersionOut(version=v.version, title=v.title, body=v.body, data=v.data,
                              published_at=v.published_at,
                              published_by_user_id=v.published_by_user_id) for v in rows]


@router.post("/admin/sections/{section_id}/versions/{version}/restore", response_model=AdminDocs,
             summary="Copy an old version into the draft")
async def restore_version(section_id: UUID, version: int, db: Db, user: Editor) -> AdminDocs:
    svc = LiveDocsService(db)
    await svc.restore(section_id, version, user.id)
    return await _admin_docs(svc)


@router.delete("/admin/sections/{section_id}", response_model=AdminDocs,
               summary="Delete a custom section")
async def delete_section(section_id: UUID, db: Db, _: Editor) -> AdminDocs:
    svc = LiveDocsService(db)
    await svc.delete_section(section_id)
    return await _admin_docs(svc)


@router.post("/admin/team", response_model=AdminDocs, status_code=201, summary="Add a team member")
async def add_member(
    db: Db,
    _: Editor,
    full_name: Annotated[str, Form()],
    role: Annotated[str, Form()],
    email: Annotated[str, Form()],
    photo: Annotated[UploadFile | None, File()] = None,
) -> AdminDocs:
    svc = LiveDocsService(db)
    raw = await photo.read() if photo else None
    await svc.add_member(full_name, role, email, raw or None)
    return await _admin_docs(svc)


@router.put("/admin/team-order", response_model=AdminDocs, summary="Reorder the team")
async def reorder_team(body: OrderUpdate, db: Db, _: Editor) -> AdminDocs:
    svc = LiveDocsService(db)
    await svc.reorder_team(body.ids)
    return await _admin_docs(svc)


@router.put("/admin/team/{member_id}", response_model=AdminDocs, summary="Edit a team member")
async def update_member(member_id: UUID, body: MemberUpdate, db: Db, _: Editor) -> AdminDocs:
    svc = LiveDocsService(db)
    await svc.update_member(member_id, body.full_name, body.role, body.email)
    return await _admin_docs(svc)


@router.put("/admin/team/{member_id}/photo", response_model=AdminDocs,
            summary="Replace a team member's photo")
async def set_photo(member_id: UUID, db: Db, _: Editor,
                    photo: Annotated[UploadFile, File()]) -> AdminDocs:
    svc = LiveDocsService(db)
    await svc.set_photo(member_id, await photo.read())
    return await _admin_docs(svc)


@router.delete("/admin/team/{member_id}/photo", response_model=AdminDocs,
               summary="Remove a team member's photo")
async def delete_photo(member_id: UUID, db: Db, _: Editor) -> AdminDocs:
    svc = LiveDocsService(db)
    await svc.set_photo(member_id, None)
    return await _admin_docs(svc)


@router.delete("/admin/team/{member_id}", response_model=AdminDocs, summary="Remove a team member")
async def delete_member(member_id: UUID, db: Db, _: Editor) -> AdminDocs:
    svc = LiveDocsService(db)
    await svc.delete_member(member_id)
    return await _admin_docs(svc)
