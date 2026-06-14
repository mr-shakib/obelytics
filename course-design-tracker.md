# Course Design Feature — Implementation Tracker

Source reference: `V2.Theory Outline_CSE311_Summer 2026-SH (1).pdf` (Daffodil International
University "Course Outline" template). Goal: the **Course Design** experience
(`/courses/[id]` + the Module-Leader workspace reached from it) should let a
Module Leader manage and view every section of this document, and the OBE
mapping rules (CEP/CEA requirements, assessment tools) described below.

This file tracks the work as a set of phases. Check items off as they land.
Each phase is a self-contained vertical slice (migration → model → schema →
repository → service → router → `api.d.ts` regen → frontend).

---

## Mapping: PDF section → system entity

| PDF section | Status | System entity |
|---|---|---|
| Basic Information (code, title, credits, hours) | ✅ Exists | `curriculum.courses` |
| Prerequisite | ✅ Exists (UI shipped in Phase 1) | `curriculum.course_prerequisites` |
| Course Content (from syllabus) | ✅ Exists (shipped in Phase 1) | `curriculum.courses.syllabus_content` |
| Course Description/Rationale | ✅ Exists (relabeled in Phase 1) | `curriculum.courses.description` |
| Course Objective (bullets) | ✅ Exists (shipped in Phase 1) | `curriculum.course_objectives` |
| COs + CO statements | ✅ Exists | `obe.course_outcomes` |
| Learning Domains (Bloom) per CO | ✅ Exists (multi-select, just shipped) | `obe.course_outcome_bloom_levels` |
| Knowledge Profile per CO | ⚠️ Model + API exist, no UI | `obe.co_kp_mappings` |
| Complex Engineering Problem (CEP) per CO | ⚠️ Model + API exist, no UI | `obe.co_cp_mappings` |
| Complex Activity (CEA) per CO | ⚠️ Model + API exist, no UI | `obe.co_ca_mappings` |
| CO-PO mapping + justification | ⚠️ Mapping exists, no justification field | `obe.co_po_mapping_entries` |
| Course Delivery Plan (weekly topics/TLA/CO/PO/assessment) | ✅ Exists (shipped in Phase 4) | `curriculum.course_lesson_plan_items` + CO/PO joins |
| PO Validation via Assessment (tools → COs/POs description) | ✅ Exists (folded into Phase 4 via `assessment_strategy` + per-row CO/PO selects) | `curriculum.course_lesson_plan_items` |
| Assessment Pattern (CO-wise marks: Attendance/Quiz/.../Mid/Final) | ✅ Exists (shipped in Phase 5) | `curriculum.course_co_marks` |
| CIE/SEE Bloom-criteria marks breakdown | ✅ Exists (shipped in Phase 5) | `curriculum.course_bloom_marks` |
| Assessment tools selection (Mid/Final checkboxes; Lab Final + Add New) | ❌ Missing | **Phase 2** — new table |
| Learning Materials (textbooks/references) | ✅ Exists (shipped in Phase 6) | `curriculum.course_learning_materials` |
| Prepared/Approved by | Out of scope (handled by existing approval workflow) | — |

---

## Target page layout

Restructure `/courses/[id]` into tabs (keeping the existing header +
Module-Leader banner):

- **Overview** — basic info (existing), Description/Rationale, Course
  Content/Syllabus, Course Objectives, Prerequisites, Bloom domains (existing
  sidebar card)
- **Outcomes & Mappings** — links out to existing CO list, CO-PO mapping, plus
  new CO-CP / CO-CA / CO-KP mapping pages (Phase 3)
- **Assessment Tools** — Phase 2 UI
- **Delivery Plan** — Phase 4 weekly grid
- **Assessment Pattern** — Phase 5 marks matrices
- **Resources** — Phase 6 textbook list

---

## Phase 1 — Course narrative fields (Description, Content, Objectives, Prerequisites UI)

**New fields on `curriculum.courses`:**
- `syllabus_content: Text | null` — "Course Content (from syllabus)"
- keep `description` as-is → maps to "Course Description/Rationale"

**New table `curriculum.course_objectives`:**
- `id`, `course_id` (FK CASCADE), `order_index`, `statement` (Text)

**Tasks**
- [x] Migration `0021`: add `syllabus_content` column to `curriculum.courses`; create `course_objectives` table
- [x] `curriculum/models.py`: add column + `CourseObjective` model (no relationships, mirrors `CourseBloomDomain`)
- [x] `curriculum/schemas.py`: extend `CourseUpdate`/`CourseResponse` with `syllabus_content`; add `CourseObjectiveResponse`/`CourseObjectivesUpdate`
- [x] `curriculum/repository.py` + `service.py`: `CourseObjectiveRepository`/`CourseObjectiveService` — list/replace pattern (delete + bulk-insert by `order_index`), like `CourseBloomDomainRepository.replace_for_course`
- [x] `curriculum/router.py`: `GET/PUT /courses/{id}/objectives` (`curriculum.read` / `course.update`)
- [x] Frontend: regenerate `api.d.ts`
- [x] Frontend: course detail page — "Course Content" display card (syllabus_content), "Course Objectives" card with editable reorderable list (`useFieldArray`, save via PUT), "Prerequisites" card (list + remove + add-via-combobox using existing `course_prerequisites` API, no backend changes needed there), "Edit Details" form extended with a Course Content textarea

Note: scope decision — these fields are **course-level** (shared across all
curricula using the course), per user confirmation; `course_objectives` FKs
only to `course_id`, no `curriculum_id`.

---

## Phase 2 — Assessment Tools per course

Scope: per **(curriculum_id, course_id)** — same scoping as CO-PO mapping
sets, since assessment design can differ per curriculum version.

**New table `curriculum.course_assessment_tools`:**
- `id`, `curriculum_id` (FK), `course_id` (FK), `assessment_type_id` (FK
  `config.assessment_types`), `is_locked` (bool), `created_at`
- unique (`curriculum_id`, `course_id`, `assessment_type_id`)

**Defaults / rules**
- `course_type == LAB` (or `THEORY_LAB`?) → seed **"Lab Final"** with
  `is_locked = true` (cannot be unchecked). Need to confirm/add a "Lab Final"
  row to `config.assessment_types` (current seed has Lab Report, not Lab
  Final — see Open Questions).
- `course_type == THEORY` → seed **"Mid-term Exam"** + **"Final Exam"**, both
  unlocked checkboxes (multi-selectable, default both checked).
- "Add new" button sits **above** the assessment-tools list, opens a picker
  over `config.assessment_types` (org-scoped reference data) with an inline
  "create new type" option for anything not in the list.

**Tasks**
- [x] Migration `0020`: create `course_assessment_tools` table + seed "Lab Final" assessment type for existing orgs
- [x] Decide: does selecting "Lab Final" require adding it to `config.assessment_types` seed data? → Yes, added to `seed_reference_data.py` and backfilled via migration data step
- [x] `curriculum/models.py`: `CourseAssessmentTool` model (no relationships)
- [x] `curriculum/schemas.py`: `CourseAssessmentToolResponse`, `CourseAssessmentToolsUpdate`
- [x] `curriculum/repository.py`: `list_for_course(curriculum_id, course_id)`, `replace_for_course(...)`
- [x] `curriculum/service.py` + `router.py`: `GET/PUT /courses/{id}/assessment-tools?curriculum_id=` — GET auto-seeds defaults (LAB/THEORY_LAB → "Lab Final" locked; THEORY/THEORY_LAB → "Mid-term Exam" + "Final Exam" unlocked) on first call
- [x] Frontend: regenerate `api.d.ts`
- [x] Frontend: "Assessment Tools" card on `/courses/[id]` — "Add new" combobox + inline "create new type" form above a checkbox list; locked items shown disabled+checked with a lock icon, sessional tools tagged with a badge. Curriculum is resolved automatically via `useResolveCourseLocation`.

Note: implemented as a Card on the existing course design page rather than a
separate tab (no tab structure exists yet — see "Target page layout"; tabs
can be introduced later as more phases land).

---

## Phase 3 — CO-CP / CO-CA / CO-KP mapping UI + CEP/CEA validation rules

The backend models/APIs for `obe.co_cp_mappings`, `obe.co_ca_mappings`,
`obe.co_kp_mappings` already exist (approval workflow included) but have
**no frontend**.

**Validation rule (per user spec):**
- CO mapped to **PO1–PO7** → must have ≥1 `COCPMapping` (CEP) — mandatory
- CO mapped to **PO10** → must have ≥1 `COCAMapping` (CEA) — mandatory
- CO mapped to **PO8, PO9, PO11, PO12** → neither CEP nor CEA required
- Determine PO number from `ProgramOutcome.code` (e.g. `"PO1"` → 1, `"PO10"` → 10)

**Tasks**
- [x] Frontend: `frontend/app/(dashboard)/mappings/co-cp/` — page mirroring `co-po-mapping-client.tsx` (select CO, toggle Complex Problems from `config.complex_problems`)
- [x] Frontend: `frontend/app/(dashboard)/mappings/co-ca/` — same for Complex Activities
- [ ] (Deferred) Frontend: `frontend/app/(dashboard)/mappings/co-kp/` — same for Knowledge Profiles (PDF shows this too, lower priority than CEP/CEA; not covered by the user's stated CEP/CEA validation rule)
- [x] Backend: validation helper `MappingSetService.validate()` in `obe/service.py` — given a CO-PO mapping set, for each CO compute required CEP/CEA based on mapped PO codes (PO1-7 → CEP, PO10 → CEA), check against `co_cp_mappings`/`co_ca_mappings`
- [x] Backend: `GET /mappings/co-po/{set_id}/validate` → `COPOMappingValidationResponse {is_valid, issues[]}`; `publish()` now also calls `validate()` and raises 422 (`MappingSetValidationError`) if unresolved
- [x] Frontend: CO-PO mapping page — validation checklist card below the matrix (green "all satisfied" or amber list of COs with "Missing CEP"/"Missing CEA" pills deep-linking to `/mappings/co-cp?course_id=`/`co-ca?course_id=`)
- [x] Fixed permission gap: `GET /ref-data/complex-problems` and `/complex-activities` were gated behind `config.manage` (admin-only) — changed to `co.read` (matches `/bloom-domains`, `/bloom-levels` precedent) so Section Teachers/Module Leaders can load CEP/CEA option lists
- [x] Frontend: regenerated `api.d.ts`, added nav entries "CO-CP Mapping" / "CO-CA Mapping" under Curriculum group

Implementation note: CO-CP and CO-CA pages share one component,
`frontend/components/shared/complex-mapping-client.tsx` (parameterized by
`kind: "cp" | "ca"`), since the two are structurally identical (CO ×
CEP/CEA matrix with click-to-cycle: empty → Draft → Approved → removed,
gated by `mapping.co_{cp,ca}.manage` / `.approve`). No "Publish" button
exists on the CO-PO page yet — the validation card is informational only
for now; `publish()` enforcing it is ready for whenever a Publish UI lands.

---

## Phase 4 — Course Delivery / Lesson Plan (weekly)

Scope: per **(curriculum_id, course_id)**.

**New tables (`curriculum` schema, no `relationship()` — explicit repo
methods, mirroring the `CourseOutcomeBloomLevel` pattern):**

- `course_lesson_plan_items`
  - `id`, `curriculum_id`, `course_id`, `week_number` (smallint), `lesson_label` (e.g. "Lesson 1 & 2"), `topic` (Text), `tla` (Text — Teaching/Learning Activities), `assessment_strategy` (Text), `order_index`
- `course_lesson_plan_item_cos` — join table (`item_id`, `course_outcome_id`)
- `course_lesson_plan_item_pos` — join table (`item_id`, `program_outcome_id`)

This also covers the PDF's "PO Validation via Assessment" table (assessment
tool → mapped COs/POs → free-text description), by letting the
`assessment_strategy` field reference the assessment tools from Phase 2 and
the per-row CO/PO multi-selects.

**Tasks**
- [x] Migration `0023`: create the three tables
- [x] `curriculum/models.py`: `CourseLessonPlanItem`, `CourseLessonPlanItemCO`, `CourseLessonPlanItemPO`
- [x] `curriculum/schemas.py`: `LessonPlanItemInput/Response`, `LessonPlanItemsUpdate` (with `co_ids: list[UUID]`, `po_ids: list[UUID]`)
- [x] `curriculum/repository.py` + `service.py`: `CourseLessonPlanRepository`/`CourseLessonPlanService` — list + replace-for-course (delete-all + bulk-insert, same pattern as Phase 1/6)
- [x] `curriculum/router.py`: `GET/PUT /courses/{id}/lesson-plan?curriculum_id=`
- [x] Frontend: regenerate `api.d.ts`
- [x] Frontend: "Delivery Plan" card on `/courses/[id]` — editable weekly table (Week, Lesson, Topic, T-L-A, Assessment Strategy, CO/PO multi-selects via new `OutcomeCheckboxPopover`, reorder/remove/add) for editors, read-only table for viewers
- [x] Backend integration test (`test_course_lesson_plan` in `test_curriculum_flow.py`)
- [x] Browser verification (Playwright): added Week 1 row with CO mapping, saved, reloaded — persisted correctly, no console errors

---

## Phase 5 — Assessment Pattern + CIE/SEE Bloom breakdown ✅ Done

Scope: per **(curriculum_id, course_id)**.

**New table `curriculum.course_co_marks`** (the "Assessment Pattern" CO-wise
marks table — Attendance/Quiz/Presentation/Assignment/Mid-Term/Final-Term ×
CO1/CO2/CO3):
- `id`, `curriculum_id`, `course_id`, `assessment_type_id` (FK `config.assessment_types`), `course_outcome_id` (nullable — null row = "Total marks" not tied to a CO, e.g. Attendance/Quiz totals), `marks` (numeric)

**New table `curriculum.course_bloom_marks`** (CIE/SEE breakdown — Bloom
cognitive level × assessment component marks):
- `id`, `curriculum_id`, `course_id`, `assessment_type_id` (FK), `bloom_level_id` (FK `config.bloom_levels`, Cognitive domain), `marks` (numeric)
- `component` enum-ish string: `CIE` | `SEE` (since the PDF splits a 60/40 CIE/SEE breakdown). Derived automatically from `assessment_type.is_sessional` (sessional → CIE, non-sessional → SEE) — no separate UI selector.

> Note: implemented in the `curriculum` schema/module (not a literal `assessment`
> schema), following the `CourseAssessmentTool` (Phase 2) precedent which already
> lives in `curriculum` with a cross-schema FK to `config.assessment_types.id`.

**Tasks**
- [x] Migration `0024`: create `curriculum.course_co_marks` + `curriculum.course_bloom_marks`
- [x] `curriculum/models.py`: `CourseCOMarks`, `CourseBloomMarks`
- [x] `curriculum/schemas.py`, `repository.py`, `service.py`, `router.py`: `GET/PUT /courses/{id}/assessment-pattern?curriculum_id=`, `GET/PUT /courses/{id}/bloom-marks?curriculum_id=`
- [x] Frontend: regenerate `api.d.ts`
- [x] Frontend: "Assessment Pattern" + "CIE/SEE Bloom-wise Marks Breakdown" cards on `/courses/[id]` — two editable matrices (CO-wise marks; CIE/SEE Bloom breakdown), with running totals/badges (per-CO column totals, grand total vs. 100, CIE/SEE subtotals)
- [x] Backend integration tests: `test_course_assessment_pattern_and_bloom_marks`, `test_course_assessment_pattern_invalid_assessment_type`

---

## Phase 6 — Learning Materials

**New table `curriculum.course_learning_materials`:**
- `id`, `course_id` (FK CASCADE), `material_type` (`TEXTBOOK` | `REFERENCE`), `order_index`, `title`, `authors`, `publisher`, `edition_year` (string, e.g. "7th Edition, 2019")

**Tasks**
- [x] Migration `0022`: create table
- [x] `curriculum/models.py`: `CourseLearningMaterial`
- [x] `curriculum/schemas.py`, `repository.py`, `service.py`, `router.py`: `GET/PUT /courses/{id}/learning-materials` (replace-for-course pattern, `order_index` computed per `material_type`)
- [x] Frontend: regenerate `api.d.ts`
- [x] Frontend: "Learning Materials" card on `/courses/[id]` — Textbooks/References field-array editors (title/authors/publisher/edition_year, reorder/remove/add) for editors, read-only grouped lists for viewers

---

## Open questions (need user input before/while implementing)

1. **Scope of Phase 1 fields (course content, objectives, description)** —
   course-level (`curriculum.courses`, shared across all curricula that use
   the course) vs. per-curriculum like CO-PO mapping? Default proposal:
   course-level, since the PDF content (syllabus, objectives) doesn't
   typically vary per curriculum version.
2. **"Lab Final" assessment type** — not currently in the seeded
   `config.assessment_types` list (which has Quiz, Assignment, Mid-term Exam,
   Final Exam, Lab Report, Project, Presentation, Viva). Add it to the seed,
   or should "Lab" courses default-lock onto "Final Exam" relabeled? Default
   proposal: add "Lab Final" to seed data.
3. **CO-KP mapping UI (Phase 3)** — PDF shows Knowledge Profile per CO but
   the user's stated rules only cover CEP/CEA (PO1-7/PO10). Include CO-KP UI
   in Phase 3 or defer to a later phase?
4. **CO-PO mapping justification text** — PDF has a free-text "Justification
   of Mapping" per CO-PO/KP/CEP row. Worth adding a `justification: Text`
   column to `co_po_mapping_entries` / `co_kp_mappings` / `co_cp_mappings` /
   `co_ca_mappings`? Not yet scoped into a phase above — flag if wanted.

---

## Suggested order of execution

1. ✅ **Phase 2** (Assessment Tools) — done.
2. ✅ **Phase 3** (CO-CP/CO-CA UI + CEP/CEA validation) — done (CO-KP deferred, see Open Question #3).
3. ✅ **Phase 1** (narrative fields) — done.
4. ✅ **Phase 6** (Learning Materials) — done.
5. ✅ **Phase 4** (Delivery Plan) — done.
6. ✅ **Phase 5** (Assessment Pattern / CIE-SEE) — done.

---

## Resume point

Phases 1, 2, 3, 4, 5, and 6 are complete. All planned phases are done. All open
questions are resolved or deferred (Q3: CO-KP deferred; Q1/Q2: resolved during
Phases 1/2). Q4 (justification text on mapping rows) remains unscoped — flag
to the user if it becomes relevant. Browser/Playwright verification of the
Phase 5 UI has not yet been performed.
