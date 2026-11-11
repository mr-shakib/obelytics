# 07 — Evidence and Validation Plan

Rule: **measure everything, invent nothing.** Every number in the pitch must come from this file's results table.

## 1. Gold set (auditor accuracy)

- **Sample:** 200–300 real questions from past DIU midterm/final papers, ≥5 courses, stratified by theory/lab, year level, and (if available) a second department.
- **Permission:** written approval from the department before using papers; strip any student information.
- **Labels (3 faculty, independently):** Bloom level (C1–C6); which CO the question tests; aligned with declared CO? (yes / partial / no).
- **Metrics:**
  - Faculty-vs-faculty agreement (Fleiss' kappa; pairwise quadratic-weighted kappa for Bloom) → the human ceiling.
  - AI vs faculty majority (same metrics) + within-one-level agreement.
  - Precision/recall of "misaligned" flags.
- **Split:** dev set for prompt iteration; held-out test set untouched until the final report. The split is by paper (about a third held out), fixed by paper id.
- **Tooling:** `backend/scripts/integrity_gold_set.py` reads the shortlisted papers with the app's own pipeline, writes one labelling workbook per faculty member (no AI judgments shown), runs the auditor, and scores agreement (`read` → `sheets` → `audit` → `score`). Scoring on the dev split also fits the confidence calibration file. All inputs and outputs stay in `private/`.
- **Reading accuracy:** labellers also mark whether each question's wording was read correctly (and correct it), which measures the reader and the question splitter.
- **Robustness:** verb-stuffed rewrites ("Analyze: state the definition of…") must not fool it.
- **Fairness:** report accuracy per stratum (department, theory/lab, writing style).

## 2. Retrospective audit (headline number)

- Run the auditor on N past course offerings with stored marks.
- Report: share of "attained" COs whose supporting questions are misaligned; reported vs evidence-weighted attainment per CO.
- Whatever the number is, it is the headline. Don't guess it in advance.

## 3. Time study

- 5 faculty prepare an end-of-course report for one offering: manually vs with Obelytics. Record minutes.
- With the IQAC/program coordinator: time to draft one accreditation criterion section, before vs after.

## 4. Pilots

| Site | Scope | Status |
|---|---|---|
| DIU CSE | Existing deployment; run auditor on ≥5 courses | Not started |
| Second department or university | Onboard one program; time the onboarding | No contact yet |

## 5. Interviews (~10–15)

Who: ~10 faculty (module leaders, section teachers), 2–3 IQAC directors/program coordinators, 1 BAETE evaluator if reachable, 1 NRB academic.

Questions:
1. How many hours per semester do you spend on OBE/CO-PO paperwork?
2. How confident are you that your CO-question mappings reflect what the exam actually tests?
3. What happens before an accreditation visit? Who scrambles, for how long?
4. What tools do you use now (Excel, in-house, vendor)? What do they cost?
5. Would you want a tool that flags misaligned questions *before* the evaluator does? What would make you distrust it?
6. Who would approve buying it, and from which budget?

## 6. Letters of intent (target 3–5)

From department heads, IQAC directors or deans. Content: the problem they have, intent to pilot or adopt after the competition, contact. Not a purchase commitment.

## 7. Results table (fill as measured)

| KPI | Result | Date | Source |
|---|---|---|---|
| Faculty-vs-faculty agreement (Bloom) | TBD | | |
| AI-vs-faculty agreement (Bloom) | TBD | | |
| Misalignment flag precision / recall | TBD | | |
| Share of "attained" COs with misaligned evidence | TBD | | |
| End-of-course report time: before → after | TBD | | |
| Program onboarding time | TBD | | |
| Faculty acceptance rate of CQI suggestions | TBD | | |
| Institutions piloting | 1 (DIU) | 2026-10-26 | Live deployment |
| Letters of intent | 0 | 2026-10-26 | |
| Interviews completed | 0 | 2026-10-26 | |

## 8. Development measurements (not faculty-validated — do not use as pitch numbers)

Measured while building, to choose models and find bugs. The "reference labels" are Bloom/CO labels for all 226 gold-set questions written by a stronger AI model (Claude) before any auditor run; they are **not** faculty labels, and an AI may share blind spots with the models it checks. The faculty rows in §7 stay TBD until a faculty panel labels the gold set.

| Measurement | Result | Date | Source |
|---|---|---|---|
| Question reading: wording read exactly | 56 / 59 questions (95%) on a 7-paper sample of the gold set; 1 question missed, 2 lost a code line or table | 2026-11-12 | Extracted text compared with the page images by Claude; faculty check pending |
| Bloom level vs reference labels, shown in app (confidence ≥ 0.5) | DeepSeek `deepseek-v4-flash`: 80% exact, 94% within one level, weighted κ 0.59 · local `qwen3.5:4b`: 64% exact, 82% within one, κ 0.28 | 2026-11-12 | `scripts/integrity_gold_set.py score --reference`, prompt `audit-v3`, 3 judgments per question, 226 questions from 30 DIU CSE papers |
| Robustness (synthetic set `robustness-v1`, DeepSeek) | Added higher-order verbs raised the level in 0 / 13 cases; planted instructions moved it in 0 / 4; plain wording lowered a demanding question in 1 / 6 | 2026-11-12 | `scripts/integrity_robustness.py` |
| CO alignment on the gold set | **Not valid yet**: the CO statements used come from the 2022 syllabus, but Summer 2026 papers follow newer course outlines with different COs (checked for CSE311: 3 COs vs the syllabus's 4). Needs the Summer 2026 outlines | 2026-11-12 | — |

