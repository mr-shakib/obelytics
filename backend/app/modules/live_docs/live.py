"""
The live part of /docs: system health, AI usage, platform usage and recent events,
read straight from the database and the running app.

Usage is split into real institutions and demo organizations (org.organizations.is_demo),
so synthetic demo data is never presented as real use. Only counts and timestamps leave
this module — no names, ids or student data. Results are cached for a few seconds.
"""
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.modules.ai.gateway import default_provider
from app.modules.ai.models import FEATURES
from app.modules.ai.providers import OllamaBackend, OpenAICompatibleBackend
from app.modules.mcp.tools import TOOLS

STARTED_AT = datetime.now(timezone.utc)
CACHE_SECONDS = 15
_cache: dict[str, tuple[float, dict]] = {}

AI_FEATURE_TITLES = {
    "integrity": "Paper reading, integrity audits and rewrites",
    "authoring": "Outcome writing, mapping, workforce analysis and evidence writing",
    "improvement": "Improvement agent",
    "copilot": "OBE Copilot",
}

# key → (label, table, extra condition on alias t). Every table has organization_id
# and created_at. Tables and conditions are constants, never user input.
USAGE: dict[str, tuple[str, str, str | None]] = {
    "users": ("User accounts", "iam.users", None),
    "programs": ("Degree programs", "org.programs", None),
    "curricula": ("Curricula", "curriculum.curricula", None),
    "courses": ("Courses", "curriculum.courses", None),
    "course_outcomes": ("Course outcomes", "obe.course_outcomes", None),
    "mapping_sets": ("Courses with CO–PO mappings", "obe.co_po_mapping_sets", None),
    "sections": ("Section offerings", "curriculum.section_offerings", None),
    "students": ("Students", "assessment.students", None),
    "marks": ("Marks recorded", "assessment.marksheet_marks", None),
    "result_publications": ("Result submissions", "assessment.result_publications", None),
    "published_results": ("Published results", "assessment.result_publications",
                          "t.status = 'PUBLISHED'"),
    "papers": ("Exam papers read", "integrity.question_papers", None),
    "question_audits": ("Questions audited", "integrity.question_audits", "t.is_current"),
    "reviews": ("AI flags reviewed by teachers", "integrity.question_audits",
                "t.is_current AND t.review_status <> 'PENDING'"),
    "rewrites": ("Question rewrites", "integrity.question_rewrites", None),
    "outcome_suggestions": ("AI outcome suggestions", "obe.outcome_suggestions", None),
    "improvement_plans": ("Improvement plans", "cqi.improvement_plans", None),
    "market_analyses": ("Job-market analyses", "obe.market_analyses", None),
    "job_postings": ("Job postings analysed", "obe.market_postings", None),
    "evidence_drafts": ("Accreditation evidence drafts", "accreditation.evidence_drafts", None),
    "copilot_conversations": ("Copilot conversations", "copilot.conversations", None),
    "mcp_calls": ("MCP tool calls", "audit.audit_logs", "t.action = 'MCP_TOOL_CALL'"),
    "ai_calls": ("AI model calls", "ai.calls", None),
}
SIGNALS = ("organizations", *USAGE)


def _usage_sql() -> str:
    parts = [
        "SELECT 'organizations' AS k, is_demo, count(*) AS n, max(created_at) AS last_at "
        "FROM org.organizations GROUP BY is_demo"
    ]
    for key, (_, table, cond) in USAGE.items():
        where = f"WHERE {cond}" if cond else ""
        parts.append(
            f"SELECT '{key}' AS k, o.is_demo, count(*) AS n, max(t.created_at) AS last_at "
            f"FROM {table} t JOIN org.organizations o ON o.id = t.organization_id {where} "
            "GROUP BY o.is_demo"
        )
    return " UNION ALL ".join(parts)


_USAGE_SQL = text(_usage_sql())


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _needs_auth(dependant: Dependant) -> bool:
    for dep in dependant.dependencies:
        if dep.call is get_current_user or _needs_auth(dep):
            return True
    return False


def _routes(app: FastAPI) -> list[tuple[str, set[str], APIRoute]]:
    """(full path, methods, route) for every API route, through included routers."""
    try:  # FastAPI ≥ 0.13x keeps included routers as wrappers
        from fastapi.routing import iter_route_contexts
    except ImportError:  # older FastAPI: routes are already flat
        return [(r.path, set(r.methods), r) for r in app.routes if isinstance(r, APIRoute)]
    out = []
    for ctx in iter_route_contexts(app.routes):
        route = ctx.original_route
        if isinstance(route, APIRoute) and ctx.path:
            out.append((ctx.path, set(ctx.methods or route.methods), route))
    return out


def api_reference(app: FastAPI) -> dict[str, Any]:
    """Every REST endpoint the running app exposes, grouped by module."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for path, methods, route in _routes(app):
        if not path.startswith(settings.API_V1_PREFIX):
            continue
        tag = str(route.tags[0]) if route.tags else "Other"
        for method in sorted(methods - {"HEAD", "OPTIONS"}):
            groups.setdefault(tag, []).append({
                "method": method,
                "path": path,
                "summary": route.summary or route.name.replace("_", " ").capitalize(),
                "auth": "bearer" if _needs_auth(route.dependant) else "public",
            })
    out = [
        {"module": tag, "endpoints": sorted(rows, key=lambda r: (r["path"], r["method"]))}
        for tag, rows in sorted(groups.items())
    ]
    return {"endpoints": sum(len(g["endpoints"]) for g in out), "modules": len(out), "groups": out}


def _ai_features() -> list[dict[str, Any]]:
    hosted = OpenAICompatibleBackend()
    local = OllamaBackend()
    rows = []
    for feature in FEATURES:
        provider = default_provider(feature)
        backend = hosted if provider == "hosted" else local if provider == "local" else None
        kind = "chat" if feature == "copilot" else "text"
        model = (backend.info.models.get(kind) or None) if backend else None
        configured = provider != "off" and (
            hosted.configured if provider == "hosted" else bool(settings.AI_LOCAL_BASE_URL)
        )
        rows.append({
            "feature": feature,
            "title": AI_FEATURE_TITLES.get(feature, feature),
            "provider": provider if configured else "off",
            "model": model if configured else None,
            "external": bool(backend and backend.info.is_external) if configured else False,
        })
    return rows


async def _redis_ok() -> bool:
    try:
        from app.core.redis_client import get_redis

        redis = await get_redis()
        return bool(await redis.ping())
    except Exception:  # noqa: BLE001 — health probe: any failure means "not reachable"
        return False


async def snapshot(session: AsyncSession, app: FastAPI) -> dict[str, Any]:
    cached = _cache.get("live")
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]

    now = datetime.now(timezone.utc)
    since_30 = now - timedelta(days=30)
    since_14 = (now - timedelta(days=13)).replace(hour=0, minute=0, second=0, microsecond=0)

    usage: dict[str, dict[str, Any]] = {
        k: {"label": (USAGE[k][0] if k in USAGE else "Institutions"), "real": 0, "demo": 0,
            "last_at": None}
        for k in SIGNALS
    }
    for k, is_demo, n, last_at in (await session.execute(_USAGE_SQL)).all():
        row = usage[k]
        row["demo" if is_demo else "real"] += int(n)
        if last_at and (row["last_at"] is None or last_at > row["last_at"]):
            row["last_at"] = last_at
    for row in usage.values():
        row["last_at"] = _iso(row["last_at"])

    ai_rows = (await session.execute(text(
        "SELECT feature, count(*), avg(latency_ms), coalesce(sum(redactions), 0), max(created_at),"
        " coalesce(sum(input_tokens), 0), coalesce(sum(output_tokens), 0),"
        " count(*) FILTER (WHERE status <> 'OK') "
        "FROM ai.calls WHERE created_at >= :since GROUP BY feature"
    ), {"since": since_30})).all()
    by_feature = {
        r[0]: {"calls_30d": int(r[1]), "avg_latency_ms": round(float(r[2] or 0)),
               "redactions_30d": int(r[3]), "last_call_at": _iso(r[4]),
               "input_tokens_30d": int(r[5]), "output_tokens_30d": int(r[6]),
               "errors_30d": int(r[7])}
        for r in ai_rows
    }
    last_ai = (await session.execute(text("SELECT max(created_at) FROM ai.calls"))).scalar()
    ai_daily = {
        r[0].date().isoformat(): int(r[1])
        for r in (await session.execute(text(
            "SELECT date_trunc('day', created_at), count(*) FROM ai.calls "
            "WHERE created_at >= :since GROUP BY 1"
        ), {"since": since_14})).all()
    }
    event_daily = {
        r[0].date().isoformat(): int(r[1])
        for r in (await session.execute(text(
            "SELECT date_trunc('day', created_at), count(*) FROM audit.audit_logs "
            "WHERE created_at >= :since GROUP BY 1"
        ), {"since": since_14})).all()
    }
    days = [(since_14 + timedelta(days=i)).date().isoformat() for i in range(14)]
    recent = [
        {"action": r[0], "entity_type": r[1], "at": _iso(r[2]), "demo": bool(r[3])}
        for r in (await session.execute(text(
            "SELECT a.action, a.entity_type, a.created_at, coalesce(o.is_demo, false) "
            "FROM audit.audit_logs a LEFT JOIN org.organizations o ON o.id = a.organization_id "
            "ORDER BY a.created_at DESC LIMIT 12"
        ))).all()
    ]

    migration = None
    if (await session.execute(text("SELECT to_regclass('public.alembic_version')"))).scalar():
        migration = (await session.execute(text("SELECT version_num FROM public.alembic_version"))).scalar()

    redis_ok = await _redis_ok()
    ref = api_reference(app)
    calls_30d = sum(v["calls_30d"] for v in by_feature.values())
    latency = (
        round(sum(v["avg_latency_ms"] * v["calls_30d"] for v in by_feature.values()) / calls_30d)
        if calls_30d else None
    )
    data = {
        "generated_at": now.isoformat(),
        "system": {
            "status": "operational" if redis_ok else "degraded",
            "api": True,
            "database": True,
            "redis": redis_ok,
            "migration": migration,
            "environment": settings.ENV,
            "started_at": STARTED_AT.isoformat(),
            "uptime_seconds": int((now - STARTED_AT).total_seconds()),
        },
        "api": {
            "endpoints": ref["endpoints"],
            "modules": ref["modules"],
            "mcp_tools": [{"name": t.name, "description": t.description} for t in TOOLS],
        },
        "ai": {
            "features": [
                {**f, **by_feature.get(f["feature"], {"calls_30d": 0, "last_call_at": None})}
                for f in _ai_features()
            ],
            "calls_30d": calls_30d,
            "avg_latency_ms_30d": latency,
            "redactions_30d": sum(v["redactions_30d"] for v in by_feature.values()),
            "last_call_at": _iso(last_ai),
            "daily": [{"date": d, "calls": ai_daily.get(d, 0)} for d in days],
        },
        "usage": usage,
        "events": {
            "daily": [{"date": d, "events": event_daily.get(d, 0)} for d in days],
            "recent": recent,
        },
    }
    _cache["live"] = (time.monotonic(), data)
    return data


def clear_cache() -> None:
    _cache.clear()
