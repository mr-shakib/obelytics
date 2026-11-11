# AI Builders World Congress 2026 — Obelytics Upgrade

Obelytics is being upgraded for the International AI Builders Congress 2026 (Congress Day: 2026-12-26, Daffodil International University, Dhaka), Idea to Unicorn track. Challenge: **LearnSphere AI → Workforce Ready**.

**The upgrade in one line:** from OBE record-keeping to *assessment integrity intelligence* — check whether reported learning outcomes are backed by what exams actually test, explain why gaps happen, and draft accreditation evidence with every claim cited.

## Docs

| File | What it holds |
|---|---|
| `01_Competition_Brief.md` | Event, tracks, domains and challenges, timeline, judging rubric |
| `06_AI_Upgrade_Build_Plan.md` | AI features to build, data-model changes, infrastructure, codebase touchpoints |
| `07_Evidence_and_Validation.md` | How accuracy, impact and demand will be measured; results table |
| `09_Ethics_and_Governance.md` | Safeguards, data flow, bias evaluation, risk register |

## Rules for every AI feature

1. **Advisory only.** AI never changes marks or official attainment.
2. **No student data to external models.** All model calls go through the AI gateway, which redacts personal data.
3. **Fixed, permission-aware tools.** No model-generated SQL.
4. **Traceable.** Every AI output stores its model and prompt version and is written to the audit log.
5. **Explainable and overridable.** Every flag shows evidence, reason and confidence; teachers can override with a reason.
6. **Measured.** AI changes must pass the evaluation harness (`07`) before merging.

## Local-only notes

`strategy/` holds planning notes (scoring, pitch, business, timeline, decisions). It is gitignored and never committed — this repo is public.
