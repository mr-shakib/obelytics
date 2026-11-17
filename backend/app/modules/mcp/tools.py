"""
Obelytics' fixed, read-only tools, offered to AI agents over the Model Context Protocol.

The same rules as the in-app agents apply: a small, fixed set of tools (no model-written
queries); each tool checks the caller's own permissions and organization; results are
class-level figures, outcome statements and question wording — never one student's data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.curriculum.models import Curriculum
from app.modules.evidence.records import gather_records
from app.modules.evidence.service import EvidenceService
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse
from app.modules.integrity.service import IntegrityService
from app.modules.workforce.models import MarketAnalysis


class ToolError(Exception):
    """Shown to the agent as a tool error (isError), not a protocol error."""


@dataclass
class Context:
    db: AsyncSession
    user: User
    manifest: PermissionManifestResponse

    def need(self, permission: str) -> None:
        if not (self.manifest.is_super_admin or permission in self.manifest.permissions):
            raise ToolError(f"You do not have the '{permission}' permission.")

    async def curriculum(self, curriculum_id: str) -> Curriculum:
        row = (await self.db.execute(select(Curriculum).where(and_(
            Curriculum.id == _uuid(curriculum_id), Curriculum.organization_id == self.user.organization_id,
        )))).scalar_one_or_none()
        if row is None:
            raise ToolError("Curriculum not found.")
        return row


def _uuid(value: Any) -> UUID:
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise ToolError(f"Not a valid id: {value}") from exc


# ── Tools ────────────────────────────────────────────────────────────────────

async def list_curricula(ctx: Context, args: dict) -> dict:
    ctx.need("curriculum.read")
    rows = (await ctx.db.execute(
        select(Curriculum).where(Curriculum.organization_id == ctx.user.organization_id).order_by(Curriculum.name)
    )).scalars().all()
    return {"curricula": [{"id": str(c.id), "name": c.name, "program_id": str(c.program_id)} for c in rows]}


async def list_sections(ctx: Context, args: dict) -> dict:
    ctx.need("integrity.read")
    sections = await IntegrityService(ctx.db).list_sections(ctx.user, ctx.manifest)
    return {"sections": [
        {"id": str(s.id), "course": f"{s.course_code} {s.course_title}", "section": s.section_name, "term": s.term_name}
        for s in sections
    ]}


async def section_attainment(ctx: Context, args: dict) -> dict:
    ctx.need("integrity.read")
    service = IntegrityService(ctx.db)
    offering = await service.get_offering(_uuid(args.get("section_id")), ctx.user, ctx.manifest)
    evidence = await service.evidence_attainment(offering)
    return {
        "threshold_pct": evidence.threshold_pct,
        "students": evidence.total_students,
        "outcomes": [{
            "co": o.course_outcome.code,
            "statement": o.course_outcome.statement,
            "reported_attained_share_pct": round(o.reported.attained_share_pct, 1),
            "reported_attained": o.reported.is_attained,
            "supported_attained_share_pct": round(o.evidence.attained_share_pct, 1) if o.evidence else None,
            "verdict": o.verdict,
            "questions_testing_another_outcome": sum(q.status == "CONTRADICTED" for q in o.questions),
        } for o in evidence.outcomes],
    }


async def paper_audit(ctx: Context, args: dict) -> dict:
    ctx.need("integrity.read")
    exam = str(args.get("exam_type") or "FINAL").upper()
    if exam not in ("MID", "FINAL"):
        raise ToolError("exam_type must be MID or FINAL.")
    service = IntegrityService(ctx.db)
    offering = await service.get_offering(_uuid(args.get("section_id")), ctx.user, ctx.manifest)
    overview = await service.overview(offering, exam)
    return {
        "summary": overview.summary.model_dump(),
        "questions": [{
            "label": q.label,
            "marks": q.max_marks,
            "wording": q.question_text,
            "mapped": [q.declared_course_outcome.code if q.declared_course_outcome else None,
                       q.declared_bloom_level.code if q.declared_bloom_level else None],
            "ai_judged": ([q.audit.ai_course_outcome.code if q.audit.ai_course_outcome else None,
                           q.audit.ai_bloom_level.code if q.audit.ai_bloom_level else None] if q.audit else None),
            "alignment": q.audit.alignment if q.audit else None,
            "confidence": q.audit.confidence if q.audit else None,
            "reason": q.audit.rationale if q.audit else None,
            "teacher_review": q.audit.review_status if q.audit else None,
        } for q in overview.questions],
    }


async def skill_coverage(ctx: Context, args: dict) -> dict:
    ctx.need("po.read")
    curriculum = await ctx.curriculum(args.get("curriculum_id"))
    row = (await ctx.db.execute(
        select(MarketAnalysis).where(MarketAnalysis.curriculum_id == curriculum.id)
        .order_by(MarketAnalysis.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    if row is None:
        return {"analysis": None, "note": "No job-market analysis has been run for this curriculum."}
    return {
        "analysed_on": row.created_at.date().isoformat(),
        "postings": row.posting_count,
        "summary": row.result.get("summary", {}),
        "skills": [{
            "skill": s["skill"], "coverage": s["coverage"], "postings": s["postings"],
            "covering_outcomes": [o["ref"] for o in s.get("outcomes", [])],
            "program_outcomes": s.get("program_outcomes", []),
        } for s in row.result.get("skills", [])],
    }


async def program_outcome_map(ctx: Context, args: dict) -> dict:
    ctx.need("po.read")
    curriculum = await ctx.curriculum(args.get("curriculum_id"))
    records = await gather_records(ctx.db, ctx.user.organization_id, curriculum.program_id, curriculum.id)
    return {"program_outcomes": [
        {"po": r.label, "mapping": r.text} for r in records if r.kind == "program_outcome"
    ]}


async def search_accreditation_documents(ctx: Context, args: dict) -> dict:
    ctx.need("accreditation.read")
    query = str(args.get("query") or "").strip()
    if len(query) < 3:
        raise ToolError("Give a query of at least 3 characters.")
    hits = await EvidenceService(ctx.db, ctx.user).search(query, limit=min(int(args.get("limit") or 5), 10))
    return {"passages": [
        {"document": title, "heading": p.heading, "text": p.text} for p, title in hits
    ]}


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    run: Callable[[Context, dict], Awaitable[dict]]


def _object(properties: dict | None = None, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": properties or {}, "required": required or [],
            "additionalProperties": False}


_ID = {"type": "string", "format": "uuid"}

TOOLS: list[Tool] = [
    Tool("list_curricula", "The organization's curricula, with their program ids.", _object(), list_curricula),
    Tool("list_sections", "Course sections the caller may see on the Assessment Integrity page.",
         _object(), list_sections),
    Tool("section_attainment",
         "Course-outcome attainment for one section: the official figure and the figure counting only exam "
         "questions the AI audit supports. Class-level figures only.",
         _object({"section_id": _ID}, ["section_id"]), section_attainment),
    Tool("paper_audit",
         "The AI audit of one exam paper: each question's wording, the teacher's mapping, the AI's judgment, "
         "confidence, reason and the teacher's review.",
         _object({"section_id": _ID, "exam_type": {"type": "string", "enum": ["MID", "FINAL"]}}, ["section_id"]),
         paper_audit),
    Tool("skill_coverage",
         "The latest job-market analysis of a curriculum: demanded skills, how well course outcomes cover "
         "them, and the program outcomes they reach.",
         _object({"curriculum_id": _ID}, ["curriculum_id"]), skill_coverage),
    Tool("program_outcome_map", "Each program outcome with the course outcomes mapped to it and their weights.",
         _object({"curriculum_id": _ID}, ["curriculum_id"]), program_outcome_map),
    Tool("search_accreditation_documents",
         "Full-text search over accreditation manuals and templates the institution uploaded.",
         _object({"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 10}},
                 ["query"]), search_accreditation_documents),
]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}
