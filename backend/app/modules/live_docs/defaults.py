"""
Default content for the /docs page. Inserted once, the first time the page is read;
after that editors change it in the admin panel. A section whose key is missing is
added again, so new built-in sections appear after an upgrade.

Facts here were checked against the code and the deployment on 2026-11-18. Anything
not yet measured is labelled as planned.
"""
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.core.config import settings

# ── Default publishing window: June 10, 00:00 → June 14, 23:59 (local time) ─────


def default_window(now: datetime) -> tuple[datetime, datetime]:
    """The next June 10–14 window that has not ended yet, in DOCS_TIMEZONE."""
    tz = ZoneInfo(settings.DOCS_TIMEZONE)
    local_now = now.astimezone(tz)
    year = local_now.year
    end = datetime.combine(datetime(year, 6, 14).date(), time(23, 59), tz)
    if local_now > end:
        year += 1
        end = datetime.combine(datetime(year, 6, 14).date(), time(23, 59), tz)
    start = datetime.combine(datetime(year, 6, 10).date(), time(0, 0), tz)
    return start, end


# ── Diagrams (Mermaid) ──────────────────────────────────────────────────────────

ARCHITECTURE = """flowchart TB
  subgraph C["Clients"]
    direction LR
    W["Web app · Next.js 16<br/>teachers · coordinators · students"]
    M["AI agents<br/>MCP clients"]
  end
  C -->|"HTTPS · JSON · Streamable HTTP"| N["nginx · TLS"]
  N --> A["FastAPI · /api/v1<br/>auth · RBAC · audit log"]
  A --> S["Domain services<br/>curriculum · OBE · assessment · attainment<br/>integrity · workforce · evidence · CQI"]
  subgraph D["Data"]
    direction LR
    P[("PostgreSQL 16<br/>17 schemas")]
    R[("Redis<br/>job queue")]
    F[("MinIO<br/>object storage")]
  end
  S --> D
  R --> K["arq worker<br/>paper reading · audits"]
  S --> G["AI gateway<br/>model per feature · redaction · usage log"]
  K --> G
  subgraph AI["Models"]
    direction LR
    DS["DeepSeek API<br/>hosted"]
    O["Ollama · Qwen 3.5 4B<br/>self-hosted"]
  end
  G --> AI
"""

DATA_FLOW = """flowchart TB
  subgraph IN["Input"]
    direction LR
    I1["Exam paper<br/>photo · PDF · Word"]
    I2["Course outcomes<br/>and Bloom levels"]
    I3["Accreditation rules<br/>K · CEP · CEA"]
    I4["Job postings"]
  end
  I1 --> RD["Reader<br/>text layer or vision model"]
  RD --> AU["Auditor<br/>3 independent judgments<br/>vote · confidence · abstain"]
  I2 --> AU
  I4 --> WF["Workforce analyst<br/>skills · demand-weighted coverage"]
  AU --> V["Verifiers<br/>rules in code · citation checks · second AI judge"]
  WF --> V
  I3 --> V
  V --> O["Output<br/>flags with evidence · supported attainment<br/>improvement plans · skill gaps"]
  O --> T{"Teacher keeps<br/>or overrides"}
  T -->|"decision + reason"| L[("Audit log<br/>model · prompt version")]
  L -->|"next term"| IA["Improvement agent<br/>follows up on accepted fixes"]
"""

# ── Feature matrix ──────────────────────────────────────────────────────────────
# signal: a live usage counter (see live.py); ai_feature: the AI gateway feature
# whose provider decides whether the item is currently switched on.


def _f(name, area, status, description, signal=None, ai_feature=None):
    return {
        "name": name, "area": area, "status": status, "description": description,
        "signal": signal, "ai_feature": ai_feature,
    }


FEATURES = [
    _f("Program and curriculum design", "Design", "live",
       "Mission, objectives, versioned program outcomes and curricula.", "curricula"),
    _f("Course design and official outline PDF", "Design", "live",
       "Objectives, COs, weekly lesson plans, assessment pattern and Bloom-wise marks.", "courses"),
    _f("Outline importer and outcome writer", "Design", "live",
       "Reads a Word or PDF outline into COs and topics; drafts and sharpens COs, "
       "with quality checks in code.", "outcome_suggestions", "authoring"),
    _f("CO–PO, K, CEP and CEA mapping", "Map", "live",
       "Weighted mappings with a validator for BAETE's knowledge-profile and "
       "complex-problem rules.", "mapping_sets"),
    _f("AI mapping suggestions", "Map", "live",
       "Suggested links with reasons; links that break the rules can't be applied.",
       None, "authoring"),
    _f("Marksheets and result approvals", "Assess", "live",
       "Question-wise marks tagged to COs; teacher → module leader → coordinator → publish.",
       "result_publications"),
    _f("Exam paper reader", "Assess", "live",
       "Word and text PDFs from their text layer; scanned pages through a vision model.",
       "papers", "integrity"),
    _f("Reading phone photos", "Assess", "beta",
       "Works with a vision model; not switched on for this public server yet."),
    _f("Assessment integrity auditor", "Assess", "live",
       "Judges each question's real Bloom level and CO, blind to the teacher's tags, "
       "and flags mismatches with evidence.", "question_audits", "integrity"),
    _f("Question rewriter", "Assess", "live",
       "Rewrites a flagged question; the auditor re-checks it without being told the target.",
       "rewrites", "integrity"),
    _f("CO and PO attainment, course-end reports", "Measure", "live",
       "Computed when results are published; per-section and combined reports as PDF.",
       "published_results"),
    _f("Evidence-weighted attainment", "Measure", "live",
       "The official figure next to the figure counting only questions the audit supports.",
       "question_audits", "integrity"),
    _f("Improvement agent", "Improve", "live",
       "Finds which questions and teaching weeks caused a gap and proposes fixes; "
       "every cited fact is checked.", "improvement_plans", "improvement"),
    _f("Workforce readiness", "Workforce", "live",
       "Job postings → skills → demand-weighted CO coverage → drafted COs for gaps.",
       "market_analyses", "authoring"),
    _f("Student My Skills", "Workforce", "live",
       "Each student's verified, developing and missing in-demand skills. No AI sees student data.",
       "students"),
    _f("Accreditation evidence writer", "Accredit", "live",
       "Report sections where every sentence cites a program record or manual passage.",
       "evidence_drafts", "authoring"),
    _f("OBE Copilot", "Assist", "live",
       "Answers questions about the program's own data, within the user's role.",
       "copilot_conversations", "copilot"),
    _f("MCP server for AI agents", "Platform", "live",
       "Seven read-only tools over Streamable HTTP, running as the signed-in user.", "mcp_calls"),
    _f("AI gateway", "Platform", "live",
       "Model per institution and feature, personal data removed before external calls, "
       "every call logged.", "ai_calls"),
    _f("English and Bangla interface", "Platform", "live",
       "Switch at the top of every page, including the student portal."),
    _f("Faculty-rated accuracy report", "Evidence", "upcoming",
       "AI–faculty agreement compared with faculty–faculty agreement on real questions."),
    _f("Exit, alumni and employer surveys", "Evidence", "upcoming",
       "Indirect evidence summarised per program outcome."),
    _f("ABET and NBA framework packs", "Accredit", "planned",
       "The same data under other accreditors' rules."),
    _f("Bangla papers from photos, self-hosted", "Assess", "planned",
       "A self-hosted vision model for Bangla and mixed-language papers."),
]

# ── Changelog (from the repository history) ────────────────────────────────────

CHANGELOG = [
    {"version": "2026.11.18", "date": "2026-11-18", "title": "Live /docs page",
     "notes": "Pitch deck, technical documentation and live system view, with scheduled "
              "publishing, versioned sections and a team grid."},
    {"version": "2026.11.17", "date": "2026-11-17", "title": "AI across the cycle",
     "notes": "Outcome writer, outline import, mapping suggestions, question rewrites, workforce "
              "readiness with real job postings, improvement agent, accreditation evidence writer, "
              "MCP server, Bangla interface and My Skills. Full test suite green."},
    {"version": "2026.11.12", "date": "2026-11-12", "title": "Evidence-weighted attainment",
     "notes": "Supported attainment next to the official figure; robustness and prompt-injection "
              "test set; provider comparison on the evaluation set."},
    {"version": "2026.11.11", "date": "2026-11-11", "title": "Assessment integrity auditor",
     "notes": "Exam paper reader, auditor with self-consistency, AI gateway with redaction and "
              "usage log, background jobs."},
    {"version": "2026.09.27", "date": "2026-09-27", "title": "Production on a VPS",
     "notes": "CQI gap detection; Docker Compose deployment behind nginx with TLS."},
    {"version": "2026.07.16", "date": "2026-07-16", "title": "OBE Copilot",
     "notes": "Role-aware copilot; password change with session revocation; lab-course marks."},
    {"version": "2026.06.24", "date": "2026-06-24", "title": "Full OBE workflow",
     "notes": "Course design and outline PDF, section results with approvals, course-end reports, "
              "PO versioning, bulk imports, student portal."},
    {"version": "2026.06.05", "date": "2026-06-05", "title": "Platform foundation",
     "notes": "Identity and roles, assessment, attainment engine, approvals, audit trail, reporting."},
]

# ── Sections ────────────────────────────────────────────────────────────────────


def _s(key, group, kind, title, body, data=None):
    return {"key": key, "group": group, "kind": kind, "title": title,
            "body": body.strip() + "\n" if body else "", "data": data or {}}


SECTIONS = [
    # ── A. Pitch deck ──
    _s("problem", "pitch", "markdown", "Problem", """
To be accredited, an engineering degree must prove that its graduates can do what it promises. Every program accredited under the Washington Accord, including Bangladesh's BAETE (a full signatory since 2023), has to:

- define program outcomes and break them into course outcomes;
- map every course outcome to program outcomes, knowledge profiles and complex engineering problems;
- tag every exam question with the outcome it tests and its Bloom level;
- compute attainment from marks, and show that weak results improve term after term.

In many universities this runs on spreadsheets and Word files. Teachers lose time to paperwork, coordinators chase files before every accreditation visit, and two blind spots remain:

1. **Nobody checks the evidence.** Tags are filled in by hand. A course can report that students can "analyze algorithm complexity" when its exam only asked them to recall definitions.
2. **Nobody checks the market.** Outcomes are written once and rarely compared with the skills employers ask for.

So degrees are certified workforce-ready on evidence that is assembled, not verified.

**Who feels it:** section teachers and module leaders (paperwork), program coordinators and quality-assurance offices (accreditation visits), accreditation bodies (evidence they can't verify), and students and employers (degrees that don't show real skills).
"""),
    _s("solution", "pitch", "markdown", "Solution", """
Obelytics runs the whole outcome-based education cycle in one platform and puts AI to work at every stage. Every AI result is explained, checked and overridable.

| Stage | Platform | AI |
|---|---|---|
| Design | Program outcomes, versioned curricula, full course design and the official outline PDF | Imports existing outlines; drafts and sharpens course outcomes |
| Map | CO–PO, knowledge-profile, complex-problem and complex-activity mappings | Suggests links with reasons; accreditation rules enforced in code |
| Assess | Question-wise marksheets; teacher → module leader → coordinator approval | Reads the exam paper and judges what each question really tests, blind to the teacher's tags |
| Measure | CO and PO attainment, course-end reports, a student portal | Shows the official figure next to the figure the exam evidence supports |
| Improve | Automatic gap detection | An agent with fixed, read-only tools finds the cause and proposes fixes |
| Workforce | Job postings per program | Measures how well outcomes cover in-demand skills; drafts outcomes for the gaps |
| Accredit | Reports | Drafts report sections where every sentence cites its source |

**Spreadsheets store mappings. Obelytics verifies them.**
"""),
    _s("why-now", "pitch", "markdown", "Why now", """
- **The standard got stricter.** BAETE became a full signatory of the Washington Accord in 2023, so Bangladeshi engineering degrees are held to the same outcome-based standard as degrees in other signatory countries.
- **The checking work can finally scale.** Deciding what an exam question really demands takes reading and judgment; until recently that meant an expert reading every paper. Language models can now read papers, including scans and Bangla-medium questions, and judge them, as long as every judgment is explained, checked and overridable. Obelytics is built around that condition.
- **Degrees need to show skills.** Linking each course outcome to real job postings turns a transcript into evidence of what a graduate can do.
"""),
    _s("product-demo", "pitch", "demo", "Product demo", """
The live product runs at **[obelytics.bitstreamhq.com](https://obelytics.bitstreamhq.com)** with a demo university that holds synthetic data, so every AI feature can be tried safely. Judges will find the login in our submission's access note.

Things to try:

1. **Assessment → Assessment Integrity:** a sample exam paper (also in Bangla) has been read and audited. Open a flagged question to see the quoted evidence, the reason and the confidence.
2. **Any course → Mappings → Suggest with AI:** CO–PO links with reasons. A link that breaks the knowledge-profile rule can't be applied.
3. **Curriculum → Workforce Readiness:** demand-weighted skill coverage, and a drafted outcome for each gap.
4. **Reports → Accreditation Evidence:** a report section where every sentence cites its source.
5. **As a student → My Skills:** the in-demand skills a student's own published results verify.
""", {"video_url": "", "demo_url": "https://obelytics.bitstreamhq.com"}),
    _s("market", "pitch", "markdown", "Market opportunity", """
**Every outcome-based engineering program has to produce this evidence, every term.**

- **Bangladesh first:** engineering programs that are BAETE-accredited or applying, and institution-level accreditation through the Bangladesh Accreditation Council.
- **The Washington Accord:** accreditors such as NBA (India), PEC (Pakistan), EAC (Malaysia) and IESL (Sri Lanka) follow the same outcome-based rules, so the same data model serves them through framework packs.
- **ABET programs worldwide,** through the same framework packs.

**Who pays:** the university's quality-assurance office (IQAC), the dean or the head of department, the people accountable for the accreditation outcome.

**Who uses it daily:** program coordinators, module leaders and section teachers. Accreditation bodies are a second customer: they get consistent, verifiable evidence across programs.
"""),
    _s("business-model", "pitch", "markdown", "Business model", """
- **B2B SaaS for universities.** Planned price: **$249 per department per month**, to be validated with pilot universities.
- **Sold as a pre-accreditation self-audit:** private to the institution, advisory, and fixable before an evaluator arrives. Never as a policing tool.
- **Two ways to deploy:** shared (many institutions in one deployment, separated by organization) or dedicated on the institution's own server, with a self-hosted model for full data residency, at a premium.
- **Add-ons:** accreditation-season evidence writing; framework packs for other accreditors.
- **Low running cost:** auditing a typical six-question paper takes about 13,000 input and 2,200 output tokens on a low-cost hosted model, and nothing per call on a self-hosted one.
"""),
    _s("traction", "pitch", "traction", "Traction", """
- **Live in production** at obelytics.bitstreamhq.com, deployed with Daffodil International University's CSE curriculum.
- **Built:** every stage of the OBE cycle, five roles (admin, program coordinator, module leader, section teacher, student), and an automated backend test suite that passes in full.
- **Real data behind the AI:** 2,775 past DIU exam papers collected; 226 questions from 30 CSE papers form our evaluation set.
- **Next:** a faculty-rated accuracy report, and a pilot with DIU CSE teachers.

The figures below are read live from this deployment. Demo University holds synthetic data, so it is counted separately.
"""),
    _s("competition", "pitch", "markdown", "Competition", """
| | Spreadsheets and Word files | Assessment and accreditation suites | Obelytics |
|---|---|---|---|
| Stores outcomes, mappings and marks | By hand | ✓ | ✓ |
| Computes CO and PO attainment | By hand-built formulas | ✓ | ✓ |
| Checks that exam questions test what they are tagged with | — | Not that we have found | ✓ AI auditor, blind to the tags |
| Shows how much reported attainment the evidence supports | — | Not that we have found | ✓ |
| Links outcomes to job-market skills | — | Not that we have found | ✓ |
| BAETE rules and a Bangla interface | — | Not that we have found | ✓ |

Commercial suites such as Watermark and Anthology focus on collecting and reporting assessment data. We are still checking their features in detail, and we don't claim a competitor lacks a feature until we have verified it.
"""),
    _s("advantage", "pitch", "markdown", "Unique advantage", """
- **It checks the evidence instead of storing it.** The auditor judges each question without seeing the teacher's tags, makes three independent judgments, and abstains when they disagree.
- **AI checks AI.** Generated output is verified before a teacher sees it, by accreditation rules in code, citation checks, or a second AI judge.
- **One outcome graph.** Program outcome → course outcome → question → marks → attainment → improvement plan in one data model. Every agent, and the MCP server, reads from it.
- **Evidence-weighted attainment:** the official figure next to the figure the exam evidence supports.
- **Data sovereignty by design:** a hosted or self-hosted model per institution and feature, personal data removed before any external call, every call logged.
- **Bangladesh first:** BAETE rules, a Bangla interface, Bangla-medium papers, and local ID and phone formats.
"""),
    _s("go-to-market", "pitch", "markdown", "Go-to-market", """
1. **Now → Dec 2026:** a pilot with DIU CSE teachers, and a second institution, free or discounted in exchange for a case study.
2. **2027:** Bangladeshi private universities with engineering programs that are BAETE-accredited or applying, sold to quality-assurance offices as a pre-visit self-audit.
3. **Then:** other Washington Accord countries (India, Pakistan, Malaysia, Sri Lanka) and ABET programs, through framework packs.
4. **Channels:** accreditation consultants, quality-assurance networks, and Bangladeshi academics abroad as champions.
"""),
    _s("team", "pitch", "team", "Team", "The people building Obelytics."),
    _s("vision", "pitch", "markdown", "Vision", """
**Every degree should come with proof of what its graduates can actually do.**

Obelytics turns accreditation from paperwork into verified evidence: exam questions that really test their outcomes, attainment figures the evidence supports, and curricula that keep pace with the job market. We start with BAETE programs in Bangladesh and grow to every outcome-based accreditor, so that a degree carries proof, not paperwork.
"""),
    # ── B–C. Product ──
    _s("product-overview", "product", "markdown", "Product overview", """
**What it does.** Obelytics is an AI-native platform for outcome-based education (OBE) and accreditation. It runs the cycle a degree program must document (design, mapping, assessment, attainment, improvement and accreditation) and uses AI to draft, check and explain the evidence.

**Target users**

| Role | Uses Obelytics to |
|---|---|
| Section teacher | enter question-wise marks, audit the exam paper, review AI flags |
| Module leader | design the course, approve outcomes and results |
| Program coordinator | own the program's outcomes and mappings, publish results, prepare accreditation |
| Quality-assurance office | see the evidence across programs before an accreditation visit |
| Student | see their own CO and PO attainment and verified skills |
| Admin | manage the institution, roles and AI settings |

**Core use cases**

- Prepare for an accreditation visit with evidence that has already been checked.
- Find exam questions that don't test what they claim, and rewrite them.
- See why an outcome was not attained, and what to change next term.
- Show students and employers which in-demand skills a degree verifies.
"""),
    _s("features", "product", "features", "Feature matrix", """
Status is read live: a feature that depends on AI shows **Off** when its model is switched off on this server, and usage counts come from the database.
""", {"items": FEATURES}),
    # ── D–L. Technical ──
    _s("architecture", "technical", "diagram", "Architecture", """
Every request passes the same API layer, which checks the caller's role and organization. All AI work goes through one gateway, and slow AI jobs run on a background worker.
""", {"mermaid": ARCHITECTURE}),
    _s("data-flow", "technical", "diagram", "Data flow", """
From an exam paper to a teacher's decision. The other AI features follow the same pattern: input → AI → verification in code → teacher decision → audit log.
""", {"mermaid": DATA_FLOW}),
    _s("stack", "technical", "markdown", "Technology stack", """
| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, shadcn/ui, TanStack Query, Zustand, openapi-fetch, Recharts, KaTeX, Mermaid |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy (async, asyncpg), Alembic |
| Database | PostgreSQL 16, one schema per domain, with full-text search |
| Jobs and cache | Redis and an arq background worker |
| Files | MinIO (S3-compatible). Uploaded exam papers are not stored |
| AI | Own AI gateway; DeepSeek (deepseek-v4-flash) through an OpenAI-compatible API; Qwen 3.5 4B self-hosted through Ollama; pypdfium2 and Pillow to read papers |
| Agents | MCP server (Streamable HTTP) with seven read-only tools |
| Infrastructure | Docker Compose on a VPS behind nginx, with Let's Encrypt TLS |
| Quality | pytest, Ruff, ESLint, TypeScript type checks |
"""),
    _s("api", "technical", "api", "API documentation", """
**APIs exposed**

- **REST API** under `/api/v1`, JSON over HTTPS. The live list of endpoints is below.
- **MCP server** at `POST /api/v1/mcp` (Streamable HTTP, JSON-RPC 2.0, protocol 2025-06-18) with seven read-only tools, so any AI agent can use the platform under the user's own permissions.
- **This page:** `GET /api/v1/docs/public`, `/api/v1/docs/live` and `/api/v1/docs/export.md`, available while the page is published.

**APIs used**

- **DeepSeek API** (OpenAI-compatible chat completions with JSON output) for hosted AI features.
- **Ollama API** for self-hosted models.

**Auth model**

- Login returns a short-lived access token, kept in memory in the browser, and a refresh token in an HttpOnly cookie handled by the web app's own backend-for-frontend routes.
- Every call sends `Authorization: Bearer <token>`. The server turns the user's roles into a permission manifest and checks it on every endpoint.
- Records are scoped to the caller's organization; program-scoped calls also send `X-Program-Id`.
- MCP calls use the same bearer token and run as that user.
"""),
    _s("data-layer", "technical", "markdown", "Data layer", """
**Data sources**

- Data entered in the platform: programs, curricula, courses, outcomes, mappings and marks.
- Uploaded documents: exam papers (Word, PDF, photos), course outlines, accreditation manuals, and job postings (links with JobPosting data, or CSV).
- Excel bulk imports for students, marks, courses and reference data.

**Parsing**

- Word files and text PDFs are read from their text layer; scanned pages and photos are rendered to images for a vision model.
- Extracted wording is compared with the source, and wording that can't be found there is flagged.
- Accreditation manuals are split into heading-aware passages and indexed for full-text search.

**Storage**

- PostgreSQL 16, one schema per domain, every record scoped to an organization.
- Uploaded papers and outlines are not kept, only the extracted wording and a SHA-256 fingerprint.

**Privacy**

- No student data goes to an external model. Emails, phone numbers, student IDs and known names are removed before any external call.
- An institution can keep everything on its own server with a self-hosted model.
- All demo data is synthetic. The real exam papers used for evaluation are kept private and are not in the public repository.
"""),
    _s("ai-layer", "technical", "markdown", "AI layer", """
**Models**

| Model | Where | Role |
|---|---|---|
| DeepSeek deepseek-v4-flash | Hosted, OpenAI-compatible API | Judging questions, outcome writing, mapping, the improvement agent, workforce analysis, evidence writing and the copilot |
| Qwen 3.5 4B (Q4_K_M) | Self-hosted through Ollama, with vision | The on-campus option for any feature, when data must not leave the institution |

Models are chosen per institution and per feature through one AI gateway; the live view at the top shows what this server uses. Nothing is trained or fine-tuned on institutional data. Every prompt is versioned in code and stored with each output.

**How the AI reasons**

- **Integrity auditor:** judges each question's Bloom level and course outcome by what it asks students to do, not by its verbs, without seeing the teacher's tags. Three independent judgments, a majority vote, confidence from agreement, and abstention when unsure. Every flag quotes the question.
- **Agents on fixed tools:** the improvement agent picks from four read-only tools (outcome results, question statistics, lesson plan, last term's plan) for at most six steps, and code checks every fact it cites.
- **Retrieval over the outcome graph:** the evidence writer walks program outcome → course outcomes → sections → attainment → audits → improvement plans in code, and searches the accreditor's manual with full-text search. Every sentence must cite a record or passage; code flags any citation or number it can't find.
- **AI checks AI:** rewritten questions are re-judged by the auditor without being told the target, and mapping suggestions that break accreditation rules can't be applied.

**Personalization**

- Per institution: its own outcomes, accreditation rules, models and data.
- Per student: My Skills matches each student's own published results with the skills employers ask for in the program's job postings. It is computed in code, so no AI sees student data.

**Explainability**

- Every AI result shows its evidence (quoted words, cited records) and a plain-language reason.
- Every output records its model and prompt version. Teachers keep or override it with a reason, and every decision is in the audit log.
"""),
    _s("performance", "technical", "markdown", "Performance & scalability", """
**Load we plan for:** steady daytime use by teachers and coordinators, with peaks in exam season, when many papers are uploaded at once, and before accreditation visits.

| Part | Strategy |
|---|---|
| API | Stateless FastAPI containers; add more behind the load balancer |
| AI jobs | Paper reading and audits run on an arq worker. The API answers at once and the page follows the job; add workers for exam season |
| Model calls | One gateway with a concurrency limit per provider and a usage log for cost control |
| Database | Async PostgreSQL with connection pooling and batched queries; read replicas for reporting next |
| Frontend | Stale-while-revalidate caching and route prefetching; heavy parts of this page load lazily |

**Measured on this deployment (Nov 2026):** full page loads 0.91–0.97 s, in-app navigation 0.24 s. Auditing one question takes three parallel judgments, about 1.3 s.

**Cost control:** prompts put fixed instructions first so the provider can cache repeated prefixes; outputs are structured JSON; Word files and text PDFs skip the vision model; each call's tokens and cost are logged per feature.
"""),
    _s("security", "technical", "markdown", "Security", """
- **Authentication:** short-lived JWT access tokens kept in memory; refresh tokens in HttpOnly cookies, revoked when a password changes.
- **Role-based access control:** five roles built from fine-grained permissions (for example `marks.enter` or `result.approve.pc`). Every endpoint checks the caller's permission manifest, and admins can adjust roles.
- **Tenant isolation:** every record belongs to an organization, and queries are scoped to the caller's organization.
- **Data protection:** no student data to external models; personal data removed before any external AI call; uploaded papers not stored; secrets only in server environment files, never in the repository.
- **AI safety:** text from teachers and documents is fenced off from instructions and tested against prompt injection. AI is advisory and never changes a mark or an official figure.
- **Audit trail:** approvals, AI decisions, overrides and MCP tool calls are written to the audit log.
- **Transport:** HTTPS with Let's Encrypt certificates behind nginx; the database and Redis sit on an internal network only.
"""),
    # ── J, M–O. Operations ──
    _s("analytics", "operations", "analytics", "Analytics", """
**KPIs we track**

| KPI | What it tells us |
|---|---|
| AI–faculty agreement vs faculty–faculty agreement | Whether the auditor is as reliable as a second teacher |
| Share of reported attainment backed by exam evidence | How much accreditation evidence holds up |
| Teachers' keep / override rate on AI flags, per prompt version | Whether teachers find the flags useful |
| Course-end report preparation time, before vs after | Time saved for teachers and coordinators |
| Attainment gaps closed in the next term | Whether the improvement loop works |
| Demand-weighted skill coverage | How well the curriculum matches the job market |

The usage figures below are read live from this deployment.
"""),
    _s("roadmap", "operations", "markdown", "Product roadmap", """
| Horizon | What | Why |
|---|---|---|
| **Short term** (Dec 2026) | Faculty-rated accuracy and per-group bias report | The accuracy figure every later step depends on |
| | Pilot with DIU CSE teachers; a second institution | Real use, and proof the platform is not DIU-specific |
| | Exit, alumni and employer surveys, summarised by program outcome | Indirect evidence accreditors ask for |
| **Mid term** (H1 2027) | Framework packs: ABET and NBA next to BAETE | The same data under other accreditors' rules |
| | Per-institution install script; read replicas and worker autoscaling | Dedicated installs; exam-season load |
| | Bangla and mixed-language papers read from photos with a self-hosted vision model | Bangla-medium programs and colleges |
| **Long term** (2027 onward) | Pilots in other Washington Accord countries | Same outcome-based rules, local accreditor packs |
| | Opt-in, aggregated benchmarks across institutions | Programs can compare themselves fairly |
"""),
    _s("contributors", "operations", "contributors", "Team & contributors", """
The people behind Obelytics are listed under [Team](#team). The code and its full history are public on [GitHub](https://github.com/mr-shakib/obelytics). We build in VS Code with Claude Code (Anthropic) as an AI coding assistant; every change is reviewed by the team and checked by the automated test suite.
"""),
    _s("changelog", "operations", "changelog", "Changelog", "Milestones from the repository history.",
       {"items": CHANGELOG}),
]
