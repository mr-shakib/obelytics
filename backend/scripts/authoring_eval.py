"""
Measures AI CO-PO mapping suggestions against the links teachers already made
(docs/ai-congress/07_Evidence_and_Validation.md).

For each course that has a CO-PO mapping, the model is asked for links with the
app's own prompt and rule checks (app/modules/authoring), without seeing the
teacher's links. The script then reports:

- link precision, recall and F1 against the teacher's links (micro-averaged),
- weight agreement on links both made: exact, and within one step,
- how many suggested links pass the K, CEP and CEA rules as suggested.

Teacher links are a reference, not ground truth: some break the rules themselves,
so treat the numbers as a development signal.

The database is only read — no suggestion or usage rows are written.
Course data is institutional: keep every output under private/ (gitignored).

    python -m scripts.authoring_eval --org-id <uuid> --out ../private/authoring-eval \\
        [--provider hosted] [--limit 20]
"""
import argparse
import asyncio
import json
import time
import uuid
from pathlib import Path

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.modules.ai.gateway import AIGateway
from app.modules.ai.providers import AIError, build_backend
from app.modules.authoring import prompts
from app.modules.authoring.context import load_course_context
from app.modules.authoring.service import build_links
from app.modules.obe.models import COPOMappingEntry, COPOMappingSet


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


async def _courses(org_id: uuid.UUID, limit: int) -> list[tuple[uuid.UUID, uuid.UUID]]:
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(COPOMappingSet.curriculum_id, COPOMappingSet.course_id)
            .join(COPOMappingEntry, COPOMappingEntry.mapping_set_id == COPOMappingSet.id)
            .where(COPOMappingSet.organization_id == org_id)
            .group_by(COPOMappingSet.curriculum_id, COPOMappingSet.course_id)
            .having(func.count(COPOMappingEntry.id) > 0)
            .order_by(COPOMappingSet.course_id)
        )
        pairs = [(r[0], r[1]) for r in rows.all()]
    return pairs[:limit] if limit else pairs


async def _evaluate_course(org_id, curriculum_id, course_id, provider: str) -> dict:
    async with AsyncSessionLocal() as session:
        ctx = await load_course_context(session, org_id, curriculum_id, course_id, with_attributes=True)
        mapping_set = (await session.execute(select(COPOMappingSet).where(
            COPOMappingSet.curriculum_id == curriculum_id, COPOMappingSet.course_id == course_id,
        ))).scalar_one()
        entries = (await session.execute(select(COPOMappingEntry).where(
            COPOMappingEntry.mapping_set_id == mapping_set.id
        ))).scalars().all()
        teacher = {(e.course_outcome_id, e.program_outcome_id): e.weight for e in entries}

    gateway = AIGateway(build_backend(provider), provider=provider, feature="authoring",
                        organization_id=org_id, user_id=None)
    started = time.perf_counter()
    completion = await gateway.complete_json(
        purpose="suggest_co_po_mapping_eval",
        prompt=prompts.mapping_prompt(ctx),
        schema=prompts.mapping_schema(ctx),
        prompt_version=prompts.CO_PO_PROMPT_VERSION,
        temperature=0.0,
    )
    seconds = time.perf_counter() - started
    links = build_links(ctx, completion.data.get("mappings"), existing=set())
    ai = {(link.course_outcome_id, link.program_outcome_id): link for link in links}

    both = set(ai) & set(teacher)
    co_codes = {co.id: co.code for co in ctx.outcomes}
    po_codes = {po.id: po.code for po in ctx.program_outcomes}

    def label(pair):
        return f"{co_codes.get(pair[0], '?')}-{po_codes.get(pair[1], '?')}"

    return {
        "course": f"{ctx.code} {ctx.title}",
        "model": completion.model,
        "seconds": round(seconds, 1),
        "teacher_links": len(teacher),
        "ai_links": len(ai),
        "matched": len(both),
        "weight_exact": sum(ai[p].weight == teacher[p] for p in both),
        "weight_within_one": sum(abs(ai[p].weight - teacher[p]) <= 1 for p in both),
        "ai_links_passing_rules": sum(not link.issues for link in links),
        "only_ai": sorted(label(p) for p in set(ai) - set(teacher)),
        "only_teacher": sorted(label(p) for p in set(teacher) - set(ai)),
        "rule_issues": {label(p): link.issues for p, link in ai.items() if link.issues},
    }


def _summary(results: list[dict]) -> dict:
    ok = [r for r in results if "error" not in r]
    teacher = sum(r["teacher_links"] for r in ok)
    ai = sum(r["ai_links"] for r in ok)
    matched = sum(r["matched"] for r in ok)
    precision = matched / ai if ai else 0.0
    recall = matched / teacher if teacher else 0.0
    return {
        "courses": len(results),
        "failed": len(results) - len(ok),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(_f1(precision, recall), 3),
        "weight_exact": round(sum(r["weight_exact"] for r in ok) / matched, 3) if matched else None,
        "weight_within_one": (
            round(sum(r["weight_within_one"] for r in ok) / matched, 3) if matched else None
        ),
        "rule_pass_rate": round(sum(r["ai_links_passing_rules"] for r in ok) / ai, 3) if ai else None,
        "prompt_version": prompts.CO_PO_PROMPT_VERSION,
    }


async def main(args: argparse.Namespace) -> None:
    org_id = uuid.UUID(args.org_id)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    courses = await _courses(org_id, args.limit)
    print(f"{len(courses)} course(s) with teacher mappings")

    results = []
    for i, (curriculum_id, course_id) in enumerate(courses, 1):
        try:
            result = await _evaluate_course(org_id, curriculum_id, course_id, args.provider)
        except AIError as exc:
            result = {"course_id": str(course_id), "error": str(exc)}
        results.append(result)
        print(f"[{i}/{len(courses)}] {result.get('course', course_id)}: "
              f"{result.get('matched', '-')}/{result.get('teacher_links', '-')} teacher links matched")

    summary = _summary(results)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = out / f"co_po_eval_{args.provider}_{stamp}.json"
    path.write_text(json.dumps({"summary": summary, "courses": results}, indent=2, default=str))
    print(json.dumps(summary, indent=2))
    print(f"Wrote {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--org-id", required=True)
    parser.add_argument("--out", required=True, help="Output folder, under private/")
    parser.add_argument("--provider", default="hosted", choices=["local", "hosted"])
    parser.add_argument("--limit", type=int, default=0)
    asyncio.run(main(parser.parse_args()))
