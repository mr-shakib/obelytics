# Obelytics — Database Relationship Diagrams

## How to Visualize

| Tool | How |
|---|---|
| **VS Code** | Install extension **"Markdown Preview Mermaid Support"** → open this file → click Preview (`Ctrl+Shift+V`) |
| **GitHub** | Push this file — GitHub renders Mermaid automatically in any `.md` file |
| **Online (instant)** | Go to **[mermaid.live](https://mermaid.live)** → paste any code block below |
| **Notion** | Create a code block → set language to `mermaid` → paste the diagram |
| **dbdiagram.io** | Use the DBML export in `DATABASE_SCHEMA.md` as an alternative |

> Each diagram below is self-contained. Paste the ` ```mermaid ``` ` block into any of the tools above.

---

## Diagram 1 — Organization & Identity

Covers: `org` + `iam` schemas

```mermaid
erDiagram
    organizations {
        uuid id PK
        string name
        string short_name
        string status
    }
    departments {
        uuid id PK
        uuid organization_id FK
        string name
        string short_name
        string status
        timestamptz archived_at
    }
    programs {
        uuid id PK
        uuid organization_id FK
        uuid department_id FK
        string title
        string acronym
        string program_type
        int minimum_duration_semesters
        int total_credits
        string status
    }
    department_head_history {
        uuid id PK
        uuid department_id FK
        uuid user_id
        date effective_from
        date effective_to
    }
    users {
        uuid id PK
        uuid organization_id FK
        string email
        string full_name
        uuid department_id FK
        string status
    }
    password_credentials {
        uuid id PK
        uuid user_id FK
        string hashed_password
        boolean must_change_password
    }
    refresh_tokens {
        uuid id PK
        uuid user_id FK
        string token_hash
        timestamptz expires_at
        timestamptz revoked_at
    }
    roles {
        uuid id PK
        uuid organization_id FK
        string name
        boolean is_system_role
    }
    permissions {
        uuid id PK
        string code
        string module
        string tier
    }
    role_permissions {
        uuid role_id FK
        uuid permission_id FK
    }
    user_role_assignments {
        uuid id PK
        uuid user_id FK
        uuid role_id FK
        string scope_type
        uuid scope_id
        timestamptz removed_at
    }

    organizations ||--|{ departments : "has"
    organizations ||--|{ programs : "offers"
    organizations ||--|{ users : "has"
    departments ||--|{ programs : "owns"
    departments ||--o{ department_head_history : "headed by"
    users ||--o{ department_head_history : "leads"
    users ||--|| password_credentials : "authenticates with"
    users ||--o{ refresh_tokens : "holds"
    users ||--o{ user_role_assignments : "assigned"
    roles ||--o{ user_role_assignments : "given via"
    roles ||--o{ role_permissions : "grants"
    permissions ||--o{ role_permissions : "included in"
    users ||--o{ departments : "belongs to (optional)"
```

---

## Diagram 2 — Curriculum Structure

Covers: `curriculum` schema (all 11 tables)

```mermaid
erDiagram
    curricula {
        uuid id PK
        uuid organization_id FK
        uuid program_id FK
        string name
        string code
        int effective_year
        int version_number
        uuid parent_curriculum_id FK
        string status
        timestamptz archived_at
    }
    curriculum_term_definitions {
        uuid id PK
        uuid curriculum_id FK
        int term_number
        string name
        int total_credit_hours
    }
    courses {
        uuid id PK
        uuid organization_id FK
        uuid course_type_id FK
        string code
        string title
        int credits
        int theory_hours
        int lab_hours
        string status
    }
    course_types {
        uuid id PK
        uuid organization_id FK
        string name
    }
    curriculum_course_slots {
        uuid id PK
        uuid curriculum_id FK
        uuid curriculum_term_definition_id FK
        uuid course_id FK
        boolean is_elective
    }
    course_prerequisites {
        uuid id PK
        uuid course_id FK
        uuid prerequisite_course_id FK
    }
    batches {
        uuid id PK
        uuid organization_id FK
        uuid curriculum_id FK
        string name
        int intake_year
        int graduation_year
        string status
    }
    academic_terms {
        uuid id PK
        uuid organization_id FK
        string name
        int year
        string season
        date start_date
        date end_date
        string status
    }
    sections {
        uuid id PK
        uuid organization_id FK
        string name
        int capacity
    }
    section_offerings {
        uuid id PK
        uuid curriculum_id FK
        uuid batch_id FK
        uuid course_id FK
        uuid academic_term_id FK
        uuid section_id FK
        string status
    }
    faculty_assignments {
        uuid id PK
        uuid section_offering_id FK
        uuid user_id
        string role_in_course
        timestamptz removed_at
    }

    curricula ||--o{ curricula : "versioned from"
    curricula ||--|{ curriculum_term_definitions : "has semesters"
    curricula ||--|{ curriculum_course_slots : "contains"
    curricula ||--|{ batches : "has cohorts"
    curriculum_term_definitions ||--|{ curriculum_course_slots : "groups"
    courses ||--o{ curriculum_course_slots : "placed in"
    courses ||--o{ course_prerequisites : "requires"
    courses ||--o{ course_prerequisites : "prerequisite for"
    course_types ||--|{ courses : "categorizes"
    batches ||--|{ section_offerings : "runs"
    courses ||--|{ section_offerings : "taught as"
    academic_terms ||--|{ section_offerings : "scheduled in"
    sections ||--|{ section_offerings : "hosts"
    section_offerings ||--o{ faculty_assignments : "staffed by"
```

---

## Diagram 3 — Outcomes & Mappings (OBE)

Covers: `obe` schema + relevant `config` lookup tables

```mermaid
erDiagram
    programs {
        uuid id PK
        string title
        string acronym
    }
    curricula {
        uuid id PK
        string name
        string code
    }
    courses {
        uuid id PK
        string code
        string title
    }
    bloom_domains {
        uuid id PK
        string name
    }
    bloom_levels {
        uuid id PK
        uuid bloom_domain_id FK
        string code
        string name
        int order_index
    }
    delivery_methods {
        uuid id PK
        string name
    }
    knowledge_profiles {
        uuid id PK
        string code
        string description
    }
    complex_problems {
        uuid id PK
        string code
        string description
    }
    complex_activities {
        uuid id PK
        string code
        string description
    }
    program_outcomes {
        uuid id PK
        uuid program_id FK
        uuid bloom_domain_id FK
        string code
        string statement
        string status
    }
    course_outcomes {
        uuid id PK
        uuid curriculum_id FK
        uuid course_id FK
        uuid bloom_level_id FK
        string code
        string statement
        string status
    }
    po_knowledge_profiles {
        uuid id PK
        uuid program_outcome_id FK
        uuid knowledge_profile_id FK
    }
    co_delivery_methods {
        uuid id PK
        uuid course_outcome_id FK
        uuid delivery_method_id FK
    }
    co_po_mapping_sets {
        uuid id PK
        uuid curriculum_id FK
        uuid course_id FK
        string status
    }
    co_po_mapping_entries {
        uuid id PK
        uuid mapping_set_id FK
        uuid course_outcome_id FK
        uuid program_outcome_id FK
        int weight
    }
    co_cp_mappings {
        uuid id PK
        uuid course_outcome_id FK
        uuid complex_problem_id FK
        string status
    }
    co_ca_mappings {
        uuid id PK
        uuid course_outcome_id FK
        uuid complex_activity_id FK
        string status
    }
    co_kp_mappings {
        uuid id PK
        uuid course_outcome_id FK
        uuid knowledge_profile_id FK
        string status
    }

    programs ||--o{ program_outcomes : "defines"
    bloom_domains ||--o{ program_outcomes : "classifies"
    bloom_domains ||--|{ bloom_levels : "has levels"
    curricula ||--o{ course_outcomes : "scopes"
    courses ||--o{ course_outcomes : "has"
    bloom_levels ||--o{ course_outcomes : "tagged with"
    program_outcomes ||--o{ po_knowledge_profiles : "maps to"
    knowledge_profiles ||--o{ po_knowledge_profiles : "linked via"
    course_outcomes ||--o{ co_delivery_methods : "delivered via"
    delivery_methods ||--o{ co_delivery_methods : "used in"
    curricula ||--o{ co_po_mapping_sets : "contains"
    courses ||--o{ co_po_mapping_sets : "mapped in"
    co_po_mapping_sets ||--|{ co_po_mapping_entries : "has entries"
    course_outcomes ||--o{ co_po_mapping_entries : "contributes to"
    program_outcomes ||--o{ co_po_mapping_entries : "addressed by"
    course_outcomes ||--o{ co_cp_mappings : "linked to"
    complex_problems ||--o{ co_cp_mappings : "covered by"
    course_outcomes ||--o{ co_ca_mappings : "linked to"
    complex_activities ||--o{ co_ca_mappings : "covered by"
    course_outcomes ||--o{ co_kp_mappings : "linked to"
    knowledge_profiles ||--o{ co_kp_mappings : "covered by"
```

---

## Diagram 4 — Assessment & Attainment

Covers: `assessment` + `attainment` schemas

```mermaid
erDiagram
    section_offerings {
        uuid id PK
        uuid batch_id FK
        uuid course_id FK
        uuid academic_term_id FK
        string status
    }
    students {
        uuid id PK
        uuid organization_id FK
        string student_id_number
        string full_name
        uuid batch_id FK
        string status
    }
    student_enrollments {
        uuid id PK
        uuid student_id FK
        uuid section_offering_id FK
        string status
        timestamptz enrolled_at
    }
    assessments {
        uuid id PK
        uuid section_offering_id FK
        uuid assessment_type_id FK
        string name
        decimal total_marks
        decimal weightage_percent
        string status
    }
    assessment_co_weights {
        uuid id PK
        uuid assessment_id FK
        uuid course_outcome_id FK
        decimal contribution_percent
    }
    student_marks {
        uuid id PK
        uuid assessment_id FK
        uuid student_enrollment_id FK
        decimal marks_obtained
        boolean is_absent
    }
    result_publications {
        uuid id PK
        uuid section_offering_id FK
        string status
        timestamptz submitted_at
        timestamptz ml_approved_at
        timestamptz pc_approved_at
        timestamptz published_at
    }
    attainment_configs {
        uuid id PK
        uuid organization_id FK
        uuid program_id FK
        decimal threshold_student_pct
        decimal threshold_co_score_pct
    }
    co_attainment_results {
        uuid id PK
        uuid section_offering_id FK
        uuid course_outcome_id FK
        decimal average_attainment_pct
        int students_above_threshold
        int total_students
        boolean is_attained
    }
    po_attainment_results {
        uuid id PK
        uuid section_offering_id FK
        uuid program_outcome_id FK
        decimal attainment_pct
        int contributing_co_count
        boolean is_attained
    }
    course_outcomes {
        uuid id PK
        string code
        string statement
    }
    program_outcomes {
        uuid id PK
        string code
        string statement
    }

    section_offerings ||--|{ student_enrollments : "enrolled in"
    section_offerings ||--|{ assessments : "has"
    section_offerings ||--|| result_publications : "published via"
    section_offerings ||--o{ co_attainment_results : "yields"
    section_offerings ||--o{ po_attainment_results : "yields"
    students ||--|{ student_enrollments : "takes"
    assessments ||--|{ assessment_co_weights : "weighted by"
    assessments ||--|{ student_marks : "graded in"
    student_enrollments ||--|{ student_marks : "receives"
    course_outcomes ||--o{ assessment_co_weights : "assessed through"
    course_outcomes ||--o{ co_attainment_results : "attained as"
    program_outcomes ||--o{ po_attainment_results : "attained as"
```

---

## Diagram 5 — Supporting Schemas

Covers: `events`, `approval`, `audit`, `notification`, `accreditation`

```mermaid
erDiagram
    domain_events {
        uuid id PK
        string event_type
        string aggregate_type
        uuid aggregate_id
        text payload
        string status
        timestamptz processed_at
    }
    review_comments {
        uuid id PK
        uuid organization_id FK
        string entity_type
        uuid entity_id
        uuid author_user_id
        text comment
    }
    audit_logs {
        uuid id PK
        uuid organization_id FK
        uuid actor_user_id
        string entity_type
        uuid entity_id
        string action
        string before_status
        string after_status
    }
    notifications {
        uuid id PK
        uuid organization_id FK
        uuid recipient_user_id
        string notification_type
        string title
        string entity_type
        uuid entity_id
        boolean is_read
    }
    accreditation_cycles {
        uuid id PK
        uuid organization_id FK
        uuid program_id FK
        string name
        string accreditation_body
        int cycle_start_year
        int cycle_end_year
        string status
    }
    accreditation_criteria {
        uuid id PK
        uuid cycle_id FK
        string code
        string title
        int order_index
    }
    criterion_po_mappings {
        uuid id PK
        uuid criterion_id FK
        uuid program_outcome_id FK
        text notes
    }
    program_outcomes {
        uuid id PK
        string code
        string statement
    }
    programs {
        uuid id PK
        string title
        string acronym
    }

    programs ||--o{ accreditation_cycles : "reviewed in"
    accreditation_cycles ||--|{ accreditation_criteria : "has"
    accreditation_criteria ||--o{ criterion_po_mappings : "mapped to"
    program_outcomes ||--o{ criterion_po_mappings : "addressed by"
```

---

## Diagram 6 — High-Level Schema Overview

Shows how the 13 schemas relate to each other — no columns, just dependencies.

```mermaid
graph TD
    ORG["🏢 org\norganizations\ndepartments\nprograms"]
    IAM["🔐 iam\nusers · roles\npermissions"]
    CONFIG["⚙️ config\nbloom · course_types\nassessment_types · etc"]
    CURRICULUM["📚 curriculum\ncurricula · courses\nbatches · offerings"]
    OBE["🎯 obe\nprogram_outcomes\ncourse_outcomes\nCO↔PO mappings"]
    ASSESSMENT["📝 assessment\nstudents · marks\nassessments"]
    ATTAINMENT["📊 attainment\nCO & PO results\nthresholds"]
    APPROVAL["✅ approval\nreview_comments"]
    AUDIT["🔍 audit\naudit_logs"]
    NOTIFICATION["🔔 notification\nnotifications"]
    ACCREDITATION["🏆 accreditation\ncycles · criteria"]
    EVENTS["📨 events\ndomain_events"]

    ORG --> CURRICULUM
    ORG --> IAM
    ORG --> OBE
    CONFIG --> CURRICULUM
    CONFIG --> OBE
    CURRICULUM --> OBE
    CURRICULUM --> ASSESSMENT
    OBE --> ASSESSMENT
    OBE --> ATTAINMENT
    ASSESSMENT --> ATTAINMENT
    OBE --> ACCREDITATION
    ORG --> ACCREDITATION
    ORG --> APPROVAL
    ORG --> AUDIT
    ORG --> NOTIFICATION
```
