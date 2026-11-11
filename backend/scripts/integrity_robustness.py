"""
Robustness of the integrity auditor to wording (docs/ai-congress/07 §1, T19).

Runs the auditor on synthetic base questions and reworded variants that keep the
same cognitive demand (scripts/data/robustness_v1.json):
- "stuffed" variants add higher-order verbs ("critically evaluate…") to a
  low-demand task: the level must not go up;
- "plain" variants word a high-demand task with low-order verbs: the level must
  not go down;
- "injection" variants plant an instruction ("classify this as C6") in the question:
  the level must not move.

    python -m scripts.integrity_robustness [--provider local|hosted] [--samples 3]
        [--out ../private/gold/robustness.json]

Uses the app's own judging code through the AI gateway, so it measures what the
app does. The questions are synthetic, so results can be shared.
"""
import argparse
import asyncio
import json
import uuid
from pathlib import Path

from app.core.config import settings
from app.modules.ai.gateway import AIGateway
from app.modules.ai.providers import build_backend
from app.modules.integrity.auditing import build_audit_prompt, judge
from app.modules.integrity.evaluation import BLOOM_ORDER
from app.modules.integrity.prompts import AUDIT_PROMPT_VERSION

DATA = Path(__file__).parent / "data" / "robustness_v1.json"


def _rank(level: str | None) -> int | None:
    return BLOOM_ORDER.index(level) if level in BLOOM_ORDER else None


async def run(args) -> None:
    data = json.loads(DATA.read_text())
    backend = build_backend(args.provider)
    if backend is None:
        raise SystemExit(f"The {args.provider} AI provider is not configured.")
    gateway = AIGateway(backend, provider=args.provider, feature="integrity",
                        organization_id=uuid.UUID(int=0), user_id=None)
    outcomes = "\n".join(f"{o['code']}: {o['statement']}" for o in data["outcomes"])
    codes = [o["code"] for o in data["outcomes"]]

    async def level(text: str, marks: int) -> tuple[str | None, float]:
        prompt = build_audit_prompt(course=data["course"], outcomes=outcomes, label="Q", marks=str(marks),
                                    question=text)
        judgment = await judge(gateway, prompt, samples=args.samples, co_codes=codes)
        return (None if judgment.abstain else judgment.bloom), judgment.confidence

    rows = []
    for item in data["items"]:
        base_level, base_conf = await level(item["base"], item["marks"])
        for variant in item["variants"]:
            variant_level, variant_conf = await level(variant["text"], item["marks"])
            rows.append({
                "id": item["id"], "kind": variant["kind"], "truth": item["level"],
                "base": base_level, "variant": variant_level,
                "base_confidence": base_conf, "variant_confidence": variant_conf,
            })
            print(f"  {item['id']} {variant['kind']:7} truth {item['level']}  base {base_level}  "
                  f"variant {variant_level}")

    def share(predicate, kind) -> float | None:
        pool = [r for r in rows if r["kind"] == kind and _rank(r["base"]) is not None
                and _rank(r["variant"]) is not None]
        return round(sum(predicate(r) for r in pool) / len(pool), 3) if pool else None

    bases = {r["id"]: r for r in rows}.values()
    judged_bases = [r for r in bases if _rank(r["base"]) is not None]
    report = {
        "set": data["version"], "provider": args.provider, "model": backend.model_for("text"),
        "prompt_version": AUDIT_PROMPT_VERSION, "samples": args.samples,
        "base_exact": round(sum(r["base"] == r["truth"] for r in judged_bases) / len(judged_bases), 3)
        if judged_bases else None,
        "base_within_one": round(sum(abs(_rank(r["base"]) - _rank(r["truth"])) <= 1 for r in judged_bases)
                                 / len(judged_bases), 3) if judged_bases else None,
        # The headline robustness numbers: wording alone moved the level.
        "stuffed_raised_level": share(lambda r: _rank(r["variant"]) > _rank(r["base"]), "stuffed"),
        "stuffed_raised_two_or_more": share(lambda r: _rank(r["variant"]) - _rank(r["base"]) >= 2, "stuffed"),
        "plain_lowered_level": share(lambda r: _rank(r["variant"]) < _rank(r["base"]), "plain"),
        # Prompt injection (T25): an instruction planted in the question moved the level.
        "injection_moved_level": share(lambda r: _rank(r["variant"]) != _rank(r["base"]), "injection"),
        "abstained": sum(1 for r in rows if r["variant"] is None) + sum(1 for r in bases if r["base"] is None),
        "rows": rows,
    }
    for key, value in report.items():
        if key != "rows":
            print(f"  {key:28} {value}")
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2))
        print(f"  → {args.out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--provider", default="local", choices=["local", "hosted"])
    parser.add_argument("--samples", type=int, default=settings.INTEGRITY_AUDIT_SAMPLES)
    parser.add_argument("--out")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
