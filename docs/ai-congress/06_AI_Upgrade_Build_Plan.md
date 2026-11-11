# 06 — AI Upgrade Build Plan

**Status:** Phase 1 built (auditor v1, AI gateway v1, background jobs, gold-set tooling); faculty labels and measured accuracy pending. Paths are relative to the repo root. Module names under "Proposed" are suggestions, not decisions.

## Positioning shift

From: *an OBE record-keeping system with a chatbot.*
To: **assessment integrity intelligence** — the system that checks whether reported learning outcomes are backed by real evidence, finds why gaps happen, and writes accreditation evidence with citations. The existing OBE modules become the data foundation.

---

## 1. Assessment integrity auditor (headline)

- **Input:** an exam paper or assignment (PDF, DOCX, or phone photo) for a section offering; the course's CO list with declared Bloom levels; the marksheet question labels (Q1a, Q2b…).
- **Processing:**
  1. Extract text (OCR for photos), split into questions, match each to its `MarksheetQuestion` label.
  2. Classify each question's Bloom level by **cognitive demand**, not verb keywords.
  3. Judge which CO the question actually tests, and whether it matches the declared CO.
  4. Calibrated confidence; abstain below threshold.
- **Output:** per-question flags with the quoted question, the reason, AI Bloom vs declared, confidence; teacher can accept or override with a reason (stored in the audit log).
- **Acceptance:** AI agreement with the faculty majority label ≥ faculty-vs-faculty agreement (quadratic-weighted kappa, since Bloom levels are ordinal), on a held-out test set (`07` §1). Robust to verb-stuffed rewrites.

## 2. Evidence-weighted attainment (implemented)

- Recompute CO attainment with misaligned questions discounted; show next to the reported figure ("Reported 78% · Supported by evidence 52%").
- Never overwrites official attainment — it is a parallel, explained view.
- **Built** (`backend/app/modules/integrity/evidence.py`, `GET /integrity/sections/{id}/evidence`, card 3 on the Assessment Integrity page): uses the marksheet's own arithmetic over all of a section's exams. A question counts as *supported* (aligned, or right CO at another Bloom level, or the teacher disagreed with the AI), *contradicted* (tests a different CO, pending review or accepted) or *unverified* (not audited or AI unsure — still counted). The evidence figure leaves out contradicted questions; it does not re-credit them to the CO the AI chose. A test pins the reported figure to the official marksheet attainment.
- Still to do: a Bloom-level view (are CO2's questions at the CO's declared level?), and program-level roll-up for PO attainment.

## 3. Improvement (CQI) agent

- Uses per-question marks (`MarksheetMark`) and lesson plans (`CourseLessonPlanItem`) to find which questions and weeks drove a gap.
- Proposes an intervention; on the next term's run, checks whether the gap closed.
- Implemented as a tool-calling agent over **fixed, permission-aware tools** (no model-generated SQL), reusing the tool list in `ROLE_AWARE_COPILOT_PLAN.md`.
- **Acceptance:** faculty acceptance rate of suggestions; on historical data, how many past gaps it explains.

## 4. Accreditation evidence writer

- Drafts self-assessment report sections per accreditation criterion (existing `accreditation` module: cycles, criteria, criterion-PO mapping).
- Every sentence cites a database record; clicking it opens the source.
- **Acceptance:** 0 uncited factual claims on the test set.

## 5. Surveys and job-market link (required — the challenge is Workforce Ready)

- Course-exit, alumni and employer surveys (indirect assessment); AI summarizes open-ended answers by PO.
- Map POs to skills extracted from job postings → per-program "graduate attribute vs market demand" gaps.

## 6. Copilot v2 (supporting only)

- Tool calling over the same tools, citations, injection tests. Never the headline.

---

## Data model (implemented — migration `0056_integrity_foundation`)

- `assessment.marksheet_questions` gains `question_text` and `declared_bloom_level_id`. Saving questions without these fields keeps the stored values (older clients don't wipe them); sending `null` clears them. Declared Bloom levels must belong to the same organization.
- New schema `integrity` (`backend/app/modules/integrity/models.py`):
  - `question_papers` — one per section offering and exam; stores **extracted text + SHA-256 only, not the file**, so unreleased papers never sit in third-party storage.
  - `question_audits` — AI judgments (Bloom level, CO, alignment, confidence, rationale, quoted evidence, model, prompt version). History kept; exactly one current audit per question; overriding requires a reason (enforced by the database).
- Permissions `integrity.read` and `integrity.manage` for Super Admin, Program Coordinator, Module Leader and Section Teacher.
- Tests: `backend/tests/integration/test_integrity_foundation.py`.

## Data model (implemented — migration `0057_ai_gateway_integrity_jobs`)

- Schema `ai` (`backend/app/modules/ai/models.py`):
  - `organization_settings` — per-organization provider for each AI feature (`local` / `hosted` / `off`; NULL = server default).
  - `calls` — one row per model call: feature, purpose, provider, model, prompt version, tokens, images, latency, estimated cost, number of redactions, status. No prompts or outputs.
- `integrity.jobs` — background reading/auditing jobs with progress; at most one active job per exam (partial unique index).
- `integrity.question_papers.extraction_method` — `VISION`, `TEXT_LAYER`, `DOCX` or `MIXED`.
- `integrity.question_audits.raw_confidence` and `details` — the independent judgments behind each verdict, their agreement, and the calibration used.

Still to design: survey instruments/responses; framework packs.

## Auditor v1 (implemented)

- **Reading** (`integrity/documents.py`, `reading.py`): photos and scanned PDF pages go to a vision model; born-digital PDF pages (enough *visible* text — scanner OCR layers are invisible and ignored) and Word documents are split from their own text by a text model, and any question whose wording is not found in the document is flagged for the teacher. Word documents keep automatic numbering, tables (as Markdown) and equations (as LaTeX). A question split across a page break is joined: each page's prompt names the previous page's last question.
- **Judging** (`integrity/auditing.py`): each question is judged 3 times independently (one greedy, two sampled); Bloom level and CO are decided by majority vote, and confidence = share of agreeing judgments × their stated confidence, then calibrated (`calibration.py`, isotonic map fitted on the gold set's dev split). Below 0.5 the auditor abstains. Question text is fenced as data in the prompt (`audit-v2`).
- **Jobs** (`integrity/jobs.py`): uploads and audits return immediately; the arq worker (production) or the API process (development) does the model work and the page shows progress. Uploaded pages wait in Redis under a short-lived key that the worker deletes when it reads them — never in arq's stored job record.

## AI gateway v1 (implemented — `backend/app/modules/ai/`)

- One entry point for every model call (integrity and copilot). Providers: `local` (Ollama) and `hosted` (any OpenAI-compatible API; existing `DEEPSEEK_*` settings still work).
- Redaction before any external call: emails, phone numbers, student-ID patterns, an optional institution regex, and names the caller knows (e.g. the signed-in user).
- Usage log with cost estimate; **AI Settings** page (Configuration → AI Settings) to choose providers per feature and see usage.
- Still to do: shared prompt-injection test suite (T25), per-call output storage for the copilot (copilot v2).

## Infrastructure

| Item | Purpose |
|---|---|
| **AI gateway** (one place for all model calls) | **v1 built**: provider switching per organization, PII redaction, self-hosted option, usage log; features write their outputs to the audit log |
| **Evaluation harness** | Metrics and gold-set scoring built (`integrity/evaluation.py`, `scripts/integrity_gold_set.py`); CI runs and regression alerts still to do |
| **Framework packs** | BAETE/WA PO1–12, ABET SO 1–7, NBA PO + PSO, EAC — configurable outcomes and targets |
| **Attainment config fix** | Separate student-level threshold and class-level target; remove hardcoded 50% PO bar (`attainment/engine.py`, `cqi/detector.py`) |
| **Demo account** | Separate organization with synthetic data; no real student marks on stage |
| **Performance** | Items from `DEPLOYED_PAGE_LOAD_DELAY_REPORT.md`; loading states; caching |
| **Provisioning** | Scripted new-institution deploy, timed |

## Codebase touchpoints (verified 2026-10-26)

- `backend/app/modules/assessment/models.py` — `MarksheetQuestion`, `MarksheetMark`, `CourseEndReport`
- `backend/app/modules/attainment/engine.py` — threshold logic (same value used for student and class)
- `backend/app/modules/cqi/detector.py` — `PO_THRESHOLD_PCT = 50`
- `backend/app/modules/copilot/` — `provider.py` (DeepSeek), `tools.py` (context builder), `agent.py` (system prompt)
- `backend/app/modules/accreditation/`, `backend/app/modules/reporting/`
- `ROLE_AWARE_COPILOT_PLAN.md`, `COPILOT_PROGRESS.md`, `DEPLOYED_PAGE_LOAD_DELAY_REPORT.md`

## Out of scope (on purpose)

- Auto-grading students
- A student-facing chatbot
- Any AI that changes marks or official attainment
- Rebuilding modules that already work
