from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.ai.gateway import default_provider, load_settings
from app.modules.ai.models import FEATURES, AICall, OrganizationAISettings
from app.modules.ai.providers import OllamaBackend, OpenAICompatibleBackend
from app.modules.ai.schemas import (
    AISettingsResponse,
    AISettingsUpdate,
    AIUsageResponse,
    FeatureSetting,
    ProviderStatus,
    UsageRow,
)
from app.modules.audit.writer import write_audit_log
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse

router = APIRouter(prefix="/ai", tags=["AI gateway"])

_configure = require_permission("system.organization.configure")

async def _settings_response(db: AsyncSession, user: User) -> AISettingsResponse:
    row = await load_settings(db, user.organization_id)
    features = []
    for feature in FEATURES:
        chosen = getattr(row, f"{feature}_provider", None) if row else None
        default = default_provider(feature)
        features.append(FeatureSetting(
            feature=feature, chosen=chosen, default=default, effective=chosen or default,
        ))

    local = OllamaBackend()
    installed = await local.installed_models()
    hosted = OpenAICompatibleBackend()
    providers = [
        ProviderStatus(
            name="local", configured=bool(settings.AI_LOCAL_BASE_URL), external=False,
            models={k: v or None for k, v in local.info.models.items()},
            reachable=installed is not None, installed_models=installed,
        ),
        ProviderStatus(
            name="hosted", configured=hosted.configured, external=hosted.info.is_external,
            models={k: v or None for k, v in hosted.info.models.items()},
        ),
    ]
    return AISettingsResponse(features=features, providers=providers)


@router.get("/settings", response_model=AISettingsResponse)
async def get_ai_settings(
    _: Annotated[PermissionManifestResponse, Depends(_configure)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _settings_response(db, current_user)


@router.put("/settings", response_model=AISettingsResponse)
async def update_ai_settings(
    body: AISettingsUpdate,
    _: Annotated[PermissionManifestResponse, Depends(_configure)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row = await load_settings(db, current_user.organization_id)
    if row is None:
        row = OrganizationAISettings(organization_id=current_user.organization_id)
        db.add(row)
    changes = body.model_dump(exclude_unset=True)
    before = {key: getattr(row, key, None) for key in changes}
    for key, value in changes.items():
        setattr(row, key, value)
    row.updated_by_user_id = current_user.id
    await db.flush()
    write_audit_log(
        db,
        entity_type="ai_settings",
        entity_id=current_user.organization_id,
        action="AI_SETTINGS_UPDATED",
        org_id=current_user.organization_id,
        actor_user_id=current_user.id,
        extra={"before": before, "after": changes},
    )
    await db.commit()
    return await _settings_response(db, current_user)


@router.get("/usage", response_model=AIUsageResponse)
async def get_ai_usage(
    _: Annotated[PermissionManifestResponse, Depends(_configure)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    errors = func.sum(case((AICall.status == "ERROR", 1), else_=0))
    result = await db.execute(
        select(
            AICall.feature,
            AICall.provider,
            AICall.model,
            func.count(),
            errors,
            func.coalesce(func.sum(AICall.input_tokens), 0),
            func.coalesce(func.sum(AICall.output_tokens), 0),
            func.coalesce(func.sum(AICall.image_count), 0),
            func.coalesce(func.sum(AICall.redactions), 0),
            func.coalesce(func.sum(AICall.cost_usd), 0),
            func.coalesce(func.avg(AICall.latency_ms), 0),
        )
        .where(AICall.organization_id == current_user.organization_id, AICall.created_at >= since)
        .group_by(AICall.feature, AICall.provider, AICall.model)
        .order_by(AICall.feature, func.count().desc())
    )
    rows = [
        UsageRow(
            feature=r[0], provider=r[1], model=r[2], calls=r[3], errors=int(r[4] or 0),
            input_tokens=int(r[5]), output_tokens=int(r[6]), images=int(r[7]),
            redactions=int(r[8]), cost_usd=float(r[9]), avg_latency_ms=int(r[10]),
        )
        for r in result.all()
    ]
    return AIUsageResponse(
        days=days,
        calls=sum(r.calls for r in rows),
        errors=sum(r.errors for r in rows),
        input_tokens=sum(r.input_tokens for r in rows),
        output_tokens=sum(r.output_tokens for r in rows),
        redactions=sum(r.redactions for r in rows),
        cost_usd=round(sum(r.cost_usd for r in rows), 6),
        rows=rows,
    )
