"""
Gold set for the integrity auditor (docs/ai-congress/07_Evidence_and_Validation.md §1).

Real question papers and faculty labels are institutional data: keep every input
and output of this script under `private/` (gitignored). Nothing here touches the
database; model calls go through the same AI gateway and reading/judging code as
the app, so the measured accuracy is the app's accuracy.

    # 1. Read the shortlisted papers into questions (resumable)
    python -m scripts.integrity_gold_set read \\
        --candidates ../private/question-bank/gold_set_candidates.csv \\
        --root ../private/question-bank --out ../private/gold

    # 2. One labelling workbook per faculty member (labels are given independently)
    python -m scripts.integrity_gold_set sheets --out ../private/gold --labelers A,B,C \\
        [--outcomes ../private/gold/outcomes.json]

    # 3. The AI's judgments of the same questions
    python -m scripts.integrity_gold_set audit --out ../private/gold [--outcomes ...]

    # 4. Score: faculty-vs-faculty, AI-vs-faculty, reading accuracy; fit calibration on dev
    python -m scripts.integrity_gold_set score --out ../private/gold --split dev

    # Without faculty labels yet: score against reference labels from a stronger model
    # (a development signal only — never report it as faculty agreement)
    python -m scripts.integrity_gold_set score --out ../private/gold --split all \
        --reference ../private/gold/reference/claude_reference.json

outcomes.json maps a course title to its outcomes: {"Data Structures": [{"code": "CO1",
"statement": "..."}, ...]}. Without it, labellers and the AI can judge Bloom levels and
wording but not which CO a question tests.

Papers are split into a dev set (prompt work, calibration) and a held-out test set
(about a third, chosen by paper id) that is only scored for the final report.
"""
import argparse
import asyncio
import csv
import hashlib
import json
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from app.core.config import settings
from app.modules.ai.gateway import AIGateway
from app.modules.ai.providers import build_backend
from app.modules.integrity import documents
from app.modules.integrity.auditing import build_audit_prompt, judge
from app.modules.integrity.calibration import fit_isotonic
from app.modules.integrity.evaluation import (
    BLOOM_ORDER,
    exact_agreement,
    fleiss_kappa,
    majority,
    precision_recall,
    weighted_kappa,
    within_one_level,
)
from app.modules.integrity.prompts import AUDIT_PROMPT_VERSION
from app.modules.integrity.reading import _CO_CODE, attach_bare_labels, read_paper

LABEL_COLUMNS = [
    ("wording_ok", "Wording read correctly? (yes/no)"),
    ("wording_fix", "Correct wording (only if 'no')"),
    ("bloom", "Bloom level it demands (C1–C6)"),
    ("co", "CO it actually tests (e.g. CO2)"),
    ("aligned", "Matches the printed CO? (yes/partial/no)"),
    ("notes", "Notes"),
]
INFO_COLUMNS = [
    ("item_id", "Item"), ("course", "Course"), ("exam", "Exam"), ("semester", "Semester"),
    ("label", "Question"), ("marks", "Marks"), ("printed_co", "Printed CO"),
    ("context", "Shared scenario"), ("text", "Question as read by the AI"), ("figure", "Figure"),
    ("source", "Original paper (link)"),
]

INSTRUCTIONS = """How to label (please work alone — do not discuss items with the other labellers)

For each question:
1. Wording read correctly? Compare with the original paper (link in the last column). Answer
   "no" if any word, number, equation or table is wrong or missing, and type the correct wording.
2. Bloom level: the thinking a typical student must do to answer — not the verb in the question.
   A routine, practised procedure is C3 Apply even if it says "develop", "design" or "evaluate".
   "Identify" or "explain" can be C4/C5 when students must compare options and justify a choice.
     C1 Remember — recall facts, definitions or lists.
     C2 Understand — explain, classify or summarise a known idea in their own words.
     C3 Apply — carry out a known method or procedure on a given problem.
     C4 Analyze — break a new situation into parts, trace, compare or find relationships.
     C5 Evaluate — judge and justify a choice against criteria.
     C6 Create — design or produce something new and original.
3. CO it tests: which course outcome (see the "Course outcomes" sheet) the question exercises.
4. Matches the printed CO? yes / partial (partly) / no.

Leave a cell empty if you cannot judge it, and say why in Notes."""


def _split(paper_id: str) -> str:
    return "test" if int(hashlib.sha256(paper_id.encode()).hexdigest(), 16) % 3 == 0 else "dev"


def _gateway(provider: str) -> AIGateway:
    backend = build_backend(provider)
    if backend is None:
        sys.exit(f"The {provider} AI provider is not configured (see AI_* settings).")
    return AIGateway(backend, provider=provider, feature="integrity",
                     organization_id=uuid.UUID(int=0), user_id=None)


def _load_extracted(out: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted((out / "extracted").glob("*.json"))]


def _items(papers: list[dict]) -> list[dict]:
    """
    One row per question. Readings stored by an earlier pipeline get today's label and
    CO clean-up. A label repeated within a paper gets "#2", "#3" so every id is unique.
    """
    rows = []
    for paper in papers:
        seen: Counter = Counter()
        for q in attach_bare_labels([dict(q) for q in paper["questions"]]):
            seen[q["label"]] += 1
            suffix = f"#{seen[q['label']]}" if seen[q["label"]] > 1 else ""
            printed_co = q.get("co") if q.get("co") and _CO_CODE.fullmatch(q["co"]) else None
            rows.append({
                "item_id": f"{paper['paper_id']}:{q['label']}{suffix}",
                "paper_id": paper["paper_id"],
                "course": paper["course"],
                "exam": paper["exam_type"],
                "semester": paper["semester"],
                "label": q["label"],
                "marks": q.get("marks"),
                "printed_co": printed_co,
                "context": q.get("context"),
                "text": q["text"],
                "figure": q.get("figure"),
                "source": paper.get("page_url"),
                "split": _split(str(paper["paper_id"])),
            })
    return rows


# ── read ──────────────────────────────────────────────────────────────────────

async def cmd_read(args) -> None:
    out = Path(args.out)
    (out / "extracted").mkdir(parents=True, exist_ok=True)
    gateway = _gateway(args.provider)
    with open(args.candidates, newline="") as f:
        candidates = list(csv.DictReader(f))[: args.limit or None]
    for row in candidates:
        target = out / "extracted" / f"{row['paper_id']}.json"
        if target.exists():
            continue
        data = (Path(args.root) / row["file"]).read_bytes()
        prepared = documents.prepare(data, documents.PDF_TYPE, max_pages=settings.INTEGRITY_MAX_PAGES)
        started = time.perf_counter()
        try:
            result = await read_paper(gateway, prepared)
        except Exception as exc:  # keep going; a failed paper can be retried
            print(f"  {row['paper_id']}: FAILED — {exc}")
            continue
        seconds = round(time.perf_counter() - started, 1)
        target.write_text(json.dumps({
            "paper_id": row["paper_id"], "course": row["course"], "exam_type": row["exam_type"],
            "semester": row["semester"], "page_url": row.get("page_url"),
            "method": prepared.method, "pages": prepared.page_count, "seconds": seconds,
            "model": result.model, "prompt_version": result.prompt_version,
            "questions": result.questions,
        }, indent=2, ensure_ascii=False))
        print(f"  {row['paper_id']} {row['course']} {row['exam_type']}: "
              f"{len(result.questions)} questions, {prepared.page_count} pages, {seconds}s")


# ── sheets ────────────────────────────────────────────────────────────────────

def cmd_sheets(args) -> None:
    out = Path(args.out)
    items = _items(_load_extracted(out))
    if not items:
        sys.exit("No extracted papers yet — run `read` first.")
    outcomes = json.loads(Path(args.outcomes).read_text()) if args.outcomes else {}
    (out / "labels").mkdir(exist_ok=True)
    for labeler in [name.strip() for name in args.labelers.split(",") if name.strip()]:
        wb = Workbook()
        guide = wb.active
        guide.title = "How to label"
        for i, line in enumerate(INSTRUCTIONS.splitlines(), 1):
            guide.cell(row=i, column=1, value=line)
        guide.column_dimensions["A"].width = 110

        ws = wb.create_sheet("Questions")
        headers = [title for _, title in INFO_COLUMNS] + [title for _, title in LABEL_COLUMNS]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        fill = PatternFill("solid", fgColor="FFF5D6")
        for item in items:
            ws.append([item[key] for key, _ in INFO_COLUMNS] + [None] * len(LABEL_COLUMNS))
        first_label_col = len(INFO_COLUMNS) + 1
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
            for cell in row[first_label_col - 1:]:
                cell.fill = fill
        widths = {"Question as read by the AI": 70, "Shared scenario": 40, "Correct wording (only if 'no')": 40,
                  "Notes": 30, "Original paper (link)": 30}
        for col, title in enumerate(headers, 1):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = widths.get(title, 14)
        ws.freeze_panes = ws.cell(row=2, column=first_label_col)
        last = len(items) + 1

        def dropdown(key: str, options: str) -> None:
            col = first_label_col + [k for k, _ in LABEL_COLUMNS].index(key)
            letter = ws.cell(row=1, column=col).column_letter
            validation = DataValidation(type="list", formula1=f'"{options}"', allow_blank=True)
            ws.add_data_validation(validation)
            validation.add(f"{letter}2:{letter}{last}")

        dropdown("wording_ok", "yes,no")
        dropdown("bloom", ",".join(BLOOM_ORDER))
        dropdown("aligned", "yes,partial,no")

        cos = wb.create_sheet("Course outcomes")
        cos.append(["Course", "CO", "Statement"])
        for course in sorted({item["course"] for item in items}):
            known = outcomes.get(course) or [{"code": f"CO{i}", "statement": ""} for i in range(1, 6)]
            for co in known:
                cos.append([course, co["code"], co["statement"]])
        cos.column_dimensions["A"].width = 32
        cos.column_dimensions["C"].width = 100

        path = out / "labels" / f"labels_{labeler}.xlsx"
        wb.save(path)
        print(f"  {path} ({len(items)} questions)")


# ── audit ─────────────────────────────────────────────────────────────────────

async def cmd_audit(args) -> None:
    out = Path(args.out)
    items = _items(_load_extracted(out))
    outcomes = json.loads(Path(args.outcomes).read_text()) if args.outcomes else {}
    target = out / f"ai_{AUDIT_PROMPT_VERSION}.json"
    done = json.loads(target.read_text()) if target.exists() else {}
    gateway = _gateway(args.provider)
    for n, item in enumerate(items, 1):
        if item["item_id"] in done:
            continue
        course_outcomes = outcomes.get(item["course"], [])
        prompt = build_audit_prompt(
            course=item["course"],
            outcomes="\n".join(f"{co['code']}: {co['statement']}" for co in course_outcomes),
            label=item["label"],
            marks=f"{item['marks']:g}" if isinstance(item["marks"], (int, float)) else "?",
            question=item["text"], context=item["context"], figure=item["figure"],
        )
        judgment = await judge(gateway, prompt, samples=args.samples,
                               co_codes=[co["code"] for co in course_outcomes])
        done[item["item_id"]] = {
            "bloom": judgment.bloom, "co": judgment.co, "abstain": judgment.abstain,
            "confidence": judgment.confidence, "raw_confidence": judgment.raw_confidence,
            "consistency": judgment.consistency, "model": judgment.model,
            "prompt_version": AUDIT_PROMPT_VERSION, "votes": judgment.details()["votes"],
        }
        target.write_text(json.dumps(done, indent=2))
        print(f"  [{n}/{len(items)}] {item['item_id']}: {judgment.bloom} {judgment.co} "
              f"({judgment.raw_confidence:.2f})")


# ── score ─────────────────────────────────────────────────────────────────────

def _read_labels(path: Path) -> dict[str, dict]:
    ws = load_workbook(path, read_only=True)["Questions"]
    rows = ws.iter_rows(values_only=True)
    headers = list(next(rows))
    keys = {title: key for key, title in INFO_COLUMNS + LABEL_COLUMNS}
    labels = {}
    for values in rows:
        row = {keys.get(h, h): v for h, v in zip(headers, values)}
        if not row.get("item_id"):
            continue

        def clean(value):
            return str(value).strip().upper().replace(" ", "") if value not in (None, "") else None

        labels[str(row["item_id"])] = {
            "wording_ok": (str(row["wording_ok"]).strip().lower() if row.get("wording_ok") else None),
            "bloom": clean(row.get("bloom")),
            "co": clean(row.get("co")),
            "aligned": (str(row["aligned"]).strip().lower() if row.get("aligned") else None),
        }
    return labels


def _fmt(value) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _has_labels(rater: dict[str, dict]) -> bool:
    return any(v["bloom"] or v["co"] or v["aligned"] for v in rater.values())


def _read_reference(path: str) -> dict[str, dict]:
    data = json.loads(Path(path).read_text())
    return {
        item_id: {
            "wording_ok": None,
            "bloom": (v.get("bloom") or None),
            "co": (v.get("co") or "").upper().replace(" ", "") or None,
            "aligned": v.get("aligned"),
        }
        for item_id, v in data.items()
    }


def cmd_score(args) -> None:
    out = Path(args.out)
    items = {i["item_id"]: i for i in _items(_load_extracted(out))}
    if args.split != "all":
        items = {k: v for k, v in items.items() if v["split"] == args.split}
    sheets = sorted((out / "labels").glob("labels_*.xlsx"))
    faculty = {p.stem: r for p in sheets if _has_labels(r := _read_labels(p))}
    reference = _read_reference(args.reference) if args.reference else None
    if len(faculty) >= 2:
        raters = list(faculty.values())
        gold_source = f"faculty majority ({len(faculty)} raters: {', '.join(faculty)})"
    elif reference is not None:
        raters = [reference]
        gold_source = "REFERENCE LABELS FROM A STRONGER MODEL — not faculty; development signal only"
    else:
        sys.exit("Need at least two completed faculty workbooks in labels/, or --reference.")
    ai_path = out / f"ai_{AUDIT_PROMPT_VERSION}.json"
    ai = json.loads(ai_path.read_text()) if ai_path.exists() else {}

    ids = [i for i in items if all(i in r for r in raters)]
    gold_bloom = {i: majority([r[i]["bloom"] for r in raters], ordinal=True) for i in ids}
    gold_co = {i: majority([r[i]["co"] for r in raters]) for i in ids}
    gold_misaligned = {i: majority([r[i]["aligned"] for r in raters]) == "no" for i in ids}

    report: dict = {"split": args.split, "gold": gold_source, "items": len(ids)}
    if len(raters) >= 2:
        bloom_sets = [[r[i]["bloom"] for r in raters] for i in ids]
        pairwise = [
            weighted_kappa([r1[i]["bloom"] for i in ids], [r2[i]["bloom"] for i in ids])
            for n, r1 in enumerate(raters) for r2 in raters[n + 1:]
        ]
        pairwise = [k for k in pairwise if k is not None]
        wording = [majority([r[i]["wording_ok"] for r in raters]) for i in ids]
        wording = [w for w in wording if w in ("yes", "no")]
        report.update({
            "reading_accuracy": (sum(w == "yes" for w in wording) / len(wording)) if wording else None,
            "faculty_bloom_fleiss_kappa": fleiss_kappa([b for b in bloom_sets if all(b)]),
            "faculty_bloom_pairwise_qwk_mean": sum(pairwise) / len(pairwise) if pairwise else None,
            "faculty_co_fleiss_kappa": fleiss_kappa(
                [[r[i]["co"] for r in raters] for i in ids if all(r[i]["co"] for r in raters)]
            ),
        })
        if reference is not None:
            both = [i for i in ids if i in reference and reference[i]["bloom"] and gold_bloom[i]]
            report["reference_vs_faculty_bloom_qwk"] = weighted_kappa(
                [reference[i]["bloom"] for i in both], [gold_bloom[i] for i in both]
            )

    judged = [i for i in ids if i in ai and not ai[i]["abstain"] and gold_bloom[i]]
    ai_bloom = [ai[i]["bloom"] for i in judged]
    gold = [gold_bloom[i] for i in judged]
    co_ids = [i for i in judged if gold_co[i]]
    flag_ids = [i for i in co_ids if items[i]["printed_co"]]
    predicted = [ai[i]["co"] != (items[i]["printed_co"] or "").upper().replace(" ", "") for i in flag_ids]
    precision, recall = precision_recall(predicted, [gold_misaligned[i] for i in flag_ids])
    printed = [i for i in ids if items[i]["printed_co"] and gold_co[i]]
    report.update({
        "gold_bloom_distribution": dict(sorted(Counter(v for v in gold_bloom.values() if v).items())),
        "printed_co_differs_from_gold": (
            sum(gold_co[i] != items[i]["printed_co"].upper().replace(" ", "") for i in printed) / len(printed)
            if printed else None
        ),
        "ai_items_judged": len(judged),
        "ai_abstained": sum(1 for i in ids if i in ai and ai[i]["abstain"]),
        "ai_vs_gold_bloom_qwk": weighted_kappa(ai_bloom, gold),
        "ai_vs_gold_bloom_exact": exact_agreement(ai_bloom, gold),
        "ai_vs_gold_bloom_within_one": within_one_level(ai_bloom, gold),
        "ai_vs_gold_co_exact": exact_agreement([ai[i]["co"] for i in co_ids], [gold_co[i] for i in co_ids]),
        "misaligned_flags_checked": len(flag_ids),
        "misaligned_flag_precision": precision,
        "misaligned_flag_recall": recall,
        "ai_model": next((ai[i]["model"] for i in judged), None),
        "ai_prompt_version": AUDIT_PROMPT_VERSION,
    })
    for key, value in report.items():
        shown = value if isinstance(value, (str, int, list, dict)) else _fmt(value)
        print(f"  {key:36} {shown}")
    suffix = "" if len(faculty) >= 2 else "_reference"
    (out / f"score_{args.split}{suffix}.json").write_text(json.dumps(report, indent=2))

    if args.split == "dev" and judged and len(faculty) >= 2:
        points = fit_isotonic([(ai[i]["raw_confidence"], ai[i]["bloom"] == gold_bloom[i]) for i in judged])
        calibration = {"prompt_version": AUDIT_PROMPT_VERSION, "fitted_on": len(judged), "points": points}
        path = out / f"calibration_{AUDIT_PROMPT_VERSION}.json"
        path.write_text(json.dumps(calibration, indent=2))
        print(f"  calibration → {path} (set INTEGRITY_CALIBRATION_FILE to use it)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    read = sub.add_parser("read")
    read.add_argument("--candidates", required=True)
    read.add_argument("--root", required=True, help="Folder the candidates' `file` paths are relative to")
    read.add_argument("--out", required=True)
    read.add_argument("--provider", default="local", choices=["local", "hosted"])
    read.add_argument("--limit", type=int, default=0)
    sheets = sub.add_parser("sheets")
    sheets.add_argument("--out", required=True)
    sheets.add_argument("--labelers", default="A,B,C")
    sheets.add_argument("--outcomes")
    audit = sub.add_parser("audit")
    audit.add_argument("--out", required=True)
    audit.add_argument("--outcomes")
    audit.add_argument("--provider", default="local", choices=["local", "hosted"])
    audit.add_argument("--samples", type=int, default=settings.INTEGRITY_AUDIT_SAMPLES)
    score = sub.add_parser("score")
    score.add_argument("--out", required=True)
    score.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    score.add_argument("--reference", help="Reference labels JSON, used when faculty labels are missing")
    args = parser.parse_args()

    if args.command == "read":
        asyncio.run(cmd_read(args))
    elif args.command == "sheets":
        cmd_sheets(args)
    elif args.command == "audit":
        asyncio.run(cmd_audit(args))
    else:
        cmd_score(args)


if __name__ == "__main__":
    main()
