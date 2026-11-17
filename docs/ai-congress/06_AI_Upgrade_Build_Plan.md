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

- One entry point for every model call (integrity, copilot and outcome authoring). Providers: `local` (Ollama) and `hosted` (any OpenAI-compatible API; existing `DEEPSEEK_*` settings still work).
- Redaction before any external call: emails, phone numbers, student-ID patterns, an optional institution regex, and names the caller knows (e.g. the signed-in user).
- Usage log with cost estimate; **AI Settings** page (Configuration → AI Settings) to choose providers per feature and see usage.
- Still to do: shared prompt-injection test suite (T25), per-call output storage for the copilot (copilot v2).

## Outcome authoring (implemented — migration `0058_outcome_authoring`, `backend/app/modules/authoring/`)

Helps teachers write course outcomes and map them to POs. Gateway feature `authoring` (default `hosted`: it reads course text only — description, syllabus, objectives, weekly topics, COs, POs — never student data).

- **Write COs with AI** (course → Mappings): drafts 1–8 COs from the course text and the program's POs. Each draft can be edited, refined or dropped; nothing is saved until the teacher adds it through the normal CO endpoint.
- **Write with AI / Refine with AI** (every CO statement box; "Write" in the Add CO dialogs drafts one new CO, optionally on a given focus): improves an AI draft or the teacher's own wording and shows what changed. The teacher picks "Use this" or "Keep mine".
- **Quality checks in code** (`authoring/quality.py`), shown as warnings and never blocking: vague verbs (understand, know, learn…), statements that describe the course instead of the student, a verb that does not fit the tagged Bloom level, two outcomes in one, length, near-duplicates of other COs.
- **Mapping rules in one place** (`obe/mapping_rules.py`), used by the mapping validator *and* the AI:
  - K rule — a CO mapped to a PO must be mapped to at least one of the PO's required knowledge profiles (`obe.po_knowledge_profiles`, edited on the program page). POs with none are not checked.
  - CEP rule — PO1–PO7 need a complex engineering problem on the CO.
  - CEA rule — PO10 needs a complex engineering activity on the CO.
- **Suggest with AI** (CO-PO matrix): the model proposes links with weight, justification, confidence and the K/CEP/CEA attributes that justify them. Code re-checks every link: links that break a rule are shown but cannot be applied; links in another Bloom domain than the PO get a warning. Applying re-checks the rules against the current data and adds the CO's K/CEP/CEA mappings together with the link, in one transaction.
- **Traceable and measured**: every suggestion is stored in `obe.outcome_suggestions` (request, result, provider, model, prompt version, the teacher's decision: accepted / edited / partial / rejected) and written to the audit log. `scripts/authoring_eval.py` scores mapping suggestions against teachers' existing links (precision, recall, weight agreement, rule pass rate); keep its output in `private/`.
- Prompts: `co-draft-v2`, `co-refine-v1`, `co-po-v2` (`authoring/prompts.py`); course text is fenced as data.
- Tests: `backend/tests/integration/test_outcome_authoring.py`, `backend/tests/unit/test_outcome_quality.py`, `backend/tests/unit/test_mapping_rules.py`.
- **Import outline** (course page header): reads a course outline (Word or text PDF, via the integrity document reader; only a SHA-256 is kept) into a preview of description, objectives, COs and weekly topics. Code flags CO wording not found word for word in the document and Bloom levels the outline does not state; existing COs are never overwritten. Prompt `outline-v1`; migration `0060_outline_import`.

## Auditor fix — "Rewrite to fit the mapping" (implemented — migration `0059_question_rewrites`)

- On an audited question, AI rewrites it so it really tests the mapped CO and Bloom level (changing the task, not just the verb), and the **auditor checks the rewrite without being told the target**. If it falls short, the writer gets the checker's reason and tries once more (`integrity/rewriting.py`, prompt `rewrite-v2`).
- Advisory: the marksheet question is never changed — a kept rewrite is wording for the next paper. Every attempt and its judgment are stored in `integrity.question_rewrites`.
- Tests: `backend/tests/integration/test_integrity_rewrite.py`.

## Workforce readiness — job market ↔ outcomes (implemented — migration `0061_workforce_market`, `backend/app/modules/workforce/`)

- **Workforce Readiness** page (Curriculum → Workforce Readiness): a program collects job postings; AI reads each posting's skills (`job-skills-v1`), then judges which of the curriculum's COs develop each in-demand skill (`skill-coverage-v2`).
- Code does the rest: counts demand across postings, drops CO references that don't exist (a claimed "covered" with no real CO becomes a gap), derives POs from the CO-PO mapping, and scores **demand-weighted coverage** (covered 1, partial ½, gap 0, weighted by how many postings ask).
- Each gap or partial skill has a suggested course and **Draft a CO** (today's CO writer, given the skill as focus); the teacher edits and adds it, then maps it with ✨ per CO.
- Near-duplicate skill names are merged in code before counting (`workforce/analysis.py`): known aliases (JS → JavaScript, OOP, k8s…), filler words ("strong", "experience with"), and a generic suffix or plural that folds into a head skill other postings ask for ("Python scripting" → Python). A posting counts once per merged skill; the merged spellings are shown and passed to the coverage prompt. Postings hold no student data.
- **Real postings:** import from links to public job pages (schema.org `JobPosting` data first, visible text otherwise) or from a CSV export (`workforce/importing.py`). The fetcher only reaches public addresses, re-checks every redirect, and caps size (2 MB) and time (15 s). Imported postings are read at the next analysis.
- Tests: `backend/tests/integration/test_workforce.py`, `backend/tests/unit/test_workforce_analysis.py`.

## Improvement agent (implemented — migration `0062_improvement_agent`, `backend/app/modules/improvement/`)

- Card 4 on the Assessment Integrity page. A short agent loop (at most 6 steps, gateway feature `improvement`) over **fixed, read-only tools** scoped to the section the user may see: `outcome_attainment` (reported vs audit-supported), `question_stats` (average, share ≥ half, share zero, discrimination, declared vs AI Bloom), `lesson_plan`, `previous_plan`. Tools return class aggregates only — no student identities or individual marks reach the model. No model-written queries.
- The first steps are fixed (CO overview; the course's previous plan if any), so every plan starts from the same facts and follows up on what was accepted last time.
- The plan's evidence is **checked in code**: each citation must be a ref the cited tool actually returned; unsupported diagnoses are flagged. Teachers accept or reject each intervention; decisions feed the next plan. Prompt `improve-v1`.
- Tests: `backend/tests/integration/test_improvement_agent.py`.

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

## Student verified skills (implemented — no migration, `GET /workforce/students/me/skills`)

- Student portal → **My Skills**: each skill the program's latest market analysis found in job postings, matched with the student's own published CO results. **Verified** if the student attained a CO that develops the skill, **developing** if they took it but did not attain it, **not yet** if none of their completed courses develops it. A readiness bar counts verified skills among the 10 most demanded.
- Pure computation over the student's own results and the stored analysis; **no model call**, so student data never reaches a model.
- Tests: `backend/tests/unit/test_workforce_import.py`. Demo data: `scripts/seed_student_demo.py` (a synthetic student login with published results).

## Bangla (implemented)

- **Interface:** English/বাংলা switch in the header, the student portal and the login page (`frontend/lib/i18n/`). Typed dictionaries, so a missing Bangla string fails the type-check. Translated: navigation, Assessment Integrity, Workforce Readiness, the student portal and login. Model-written explanations stay in the language the model wrote them in.
- **Bangla-medium papers:** labels printed with Bangla numerals and letters (১(ক), প্রশ্ন ২) are matched to marksheet labels (`integrity/documents.py: normalize_label`). A synthetic Bangla sample paper is downloadable from the integrity page.

## Bias check (implemented)

- `scripts/integrity_gold_set.py strata` reports the auditor's accuracy per group of questions: exam, course, reference Bloom level, and wording style (math, code, scenario, figure, length). Results and limits are in `09` §6.

## Accreditation evidence writer (implemented — migration `0063_evidence_writer`, `backend/app/modules/evidence/`)

- **Retrieval:**
  - Reference documents (an accreditor's manual, report templates; PDF, Word or text) are split into passages under their headings and indexed with PostgreSQL full-text search (`accreditation.reference_passages.tsv`, GIN).
  - Program evidence is gathered in code by walking the outcome graph: POs → mapped COs → sections with marks → reported and audit-supported CO attainment → paper audits → improvement plans, plus the latest market analysis (`evidence/records.py`).
  - No model writes queries.
- **Drafting:** the model writes one criterion section where every sentence cites the records `[E…]` and passages `[M…]` it was given; the JSON schema limits citations to those ids (`evidence-v1`, gateway feature `authoring`).
- **Checking in code** (`evidence/writer.py`): a sentence is flagged when it
  - cites a source it was not given;
  - states a fact without a program record;
  - contains a number not found in its cited sources.

  Honest evidence gaps are allowed and listed with "evidence still to collect".
- **Page:** Reports → Accreditation Evidence. Upload documents, draft, click a citation to read its source, edit, accept or reject. Drafts keep their sources, model and prompt version; decisions go to the audit log.
- Tests: `backend/tests/unit/test_evidence_writer.py`, `backend/tests/integration/test_evidence_writer.py`. A clearly labelled synthetic demo guide is in `frontend/public/samples/`.

## MCP server (implemented — `backend/app/modules/mcp/`, no new dependency)

- `POST /api/v1/mcp` speaks the Model Context Protocol (Streamable HTTP transport, JSON responses; JSON-RPC 2.0: `initialize`, `ping`, `tools/list`, `tools/call`). Any MCP client or agent can use Obelytics as a tool server.
- **Seven fixed, read-only tools:**
  - `list_curricula`, `list_sections`;
  - `section_attainment` (official vs audit-supported);
  - `paper_audit`;
  - `skill_coverage`;
  - `program_outcome_map`;
  - `search_accreditation_documents`.
- They follow the same rules as the in-app agents: each call runs as the signed-in user, under their permissions and organization; results are class-level; every call is written to the audit log (`MCP_TOOL_CALL`).
- **Connect:** send the user's bearer token, e.g. `npx mcp-remote https://<host>/api/v1/mcp --header "Authorization: Bearer <token>"`.
- **Known limit:** access tokens are short-lived; a long-lived, revocable agent token is not built yet.
- Tests: `backend/tests/integration/test_mcp.py`.
