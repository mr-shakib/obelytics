# 10 — Scalability Roadmap

How Obelytics grows from one department to many institutions and countries: what scales today, what each AI call costs, and the order of the next steps. Planned work is marked as planned.

## 1. Architecture today

| Part | How it scales |
|---|---|
| API (FastAPI) | Stateless; run more containers behind the load balancer |
| AI work (reading papers, audits) | Background jobs on an arq worker; run more workers. The API answers immediately and the page follows the job |
| Model calls | One gateway for every feature, with a concurrency limit per provider (`AI_HOSTED_CONCURRENCY`, `AI_LOCAL_CONCURRENCY`) and a usage log for cost control |
| Database (PostgreSQL 16) | 17 schemas; every row scoped to an organization. Vertical first, then read replicas for reporting |
| Files | Uploaded papers are not stored; only extracted wording and a fingerprint |
| Deployment | One Docker Compose stack, migrations as a one-shot service. Runs as a shared multi-tenant service or as a dedicated per-institution install |

**Two ways to serve an institution.**
- **Shared (SaaS):** many institutions in one deployment, separated by organization id.
- **Dedicated:** the same stack on the institution's own server. This suits institutions that need data to stay on their premises, and pairs with a self-hosted model for full data residency.

## 2. What the AI costs per unit of work

Measured from the platform's own usage log (`ai.calls`, hosted model, local demo, 2026-11-17):

| Work | Model calls | Average tokens per call (in / out) | Average latency per call |
|---|---|---|---|
| Audit one question | 3 judgments | 723 / 123 | 1.3 s (judgments run in parallel) |
| Read one Word or text-PDF paper | 1 | 1,033 / 455 | 2.0 s |
| Read one job posting's skills | 1 | 393 / 239 | 1.5 s |
| CO–PO suggestions for one course | 1 | 2,130 / 1,186 | 5.9 s |
| Improvement plan for one section | ~4–6 agent steps | 1,119 / 74 per step | 1.3 s per step |
| Market coverage for a curriculum | 1 | 4,014 / 1,721 | 7.5 s |

A typical 6-question paper therefore needs about 13,000 input and 2,200 output tokens to audit. The platform records each call's cost once the provider's prices are set (`AI_HOSTED_INPUT_USD_PER_MTOK` and the output equivalent), so cost per paper can be reported per institution. Institutions on a self-hosted model pay no per-call cost.

## 3. Roadmap

| When | Step | Why |
|---|---|---|
| Done | Multi-institution data model; per-organization AI provider per feature; background AI jobs; Bangla interface | Base for every step below |
| Dec 2026 | Second institution onboarded; onboarding time measured | Proves the platform is not DIU-specific |
| Dec 2026 | Faculty-labelled accuracy and per-group bias report | The accuracy claim every later sale depends on |
| Q1 2027 | Framework packs: ABET and NBA (India), next to BAETE | Same data, different accreditor rules; opens Washington Accord and ABET markets |
| Q1 2027 | Accreditation evidence writer with per-sentence citations | The report institutions spend most time on |
| Q1 2027 | Per-institution install script and timed fresh deploy | Dedicated installs for data-residency customers |
| Q2 2027 | Bangla and mixed-language papers read from photos with a self-hosted vision model | National University colleges and Bangla-medium programs |
| Q2 2027 | Read replicas for reporting; queue-based autoscaling of workers | Exam season brings many papers at once |
| 2027 | Pilots in other Washington Accord countries (India, Pakistan, Malaysia, Sri Lanka) through framework packs | Same outcome-based rules; local accreditor packs |

## 4. Standards

Outcome-based accreditation shares one structure across the Washington Accord, so the same model serves every signatory:
- graduate attributes or program outcomes;
- course outcomes mapped to them;
- assessment evidence;
- continuous improvement.

Accreditor-specific rules are code, not hard-wired into the data. BAETE's knowledge-profile, complex-problem and complex-activity rules today live in one module (`obe/mapping_rules.py`), and a framework pack adds another accreditor's rules beside them.
