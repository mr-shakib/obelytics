# Obelytics — Database Schema Reference

## Overview

| | |
|---|---|
| **Database** | PostgreSQL |
| **Total Schemas** | 13 |
| **Total Tables** | 51 |
| **Primary Keys** | UUID (`gen_random_uuid()`) on every table |
| **Timestamps** | `DateTime(timezone=True)` on every table |
| **Multi-tenancy** | `organization_id` on all tenant-scoped tables |

---

## Schema Index

| Schema | Purpose | Tables |
|---|---|---|
| [`events`](#events) | Transactional outbox for domain events | 1 |
| [`iam`](#iam) | Identity, users, roles, permissions | 6 |
| [`org`](#org) | Organization, departments, programs | 4 |
| [`config`](#config) | Reference / lookup data | 10 |
| [`curriculum`](#curriculum) | Curricula, courses, batches, offerings | 11 |
| [`obe`](#obe) | Outcomes, mappings (CO/PO) | 9 |
| [`assessment`](#assessment) | Assessments, marks, publications | 6 |
| [`attainment`](#attainment) | Attainment results & config | 3 |
| [`approval`](#approval) | Review comments & workflows | 1 |
| [`audit`](#audit) | Immutable audit log | 1 |
| [`notification`](#notification) | In-app notifications | 1 |
| [`accreditation`](#accreditation) | Accreditation cycles & criteria | 3 |
| `reporting` | Reporting views *(no tables yet)* | — |

---

## events

### `events.domain_events`
Transactional outbox — records domain events before they are dispatched.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK, default `gen_random_uuid()` |
| `event_type` | VARCHAR(255) | NOT NULL |
| `aggregate_type` | VARCHAR(100) | NOT NULL |
| `aggregate_id` | UUID | nullable |
| `payload` | TEXT | NOT NULL |
| `status` | VARCHAR(20) | NOT NULL, default `PENDING` |
| `created_at` | TIMESTAMPTZ | NOT NULL, default `now()` |
| `processed_at` | TIMESTAMPTZ | nullable |

**Indexes:** `event_type`, `status`

---

## iam

### `iam.permissions`
System and custom permission codes.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `code` | VARCHAR(100) | NOT NULL, UNIQUE |
| `description` | VARCHAR(500) | nullable |
| `tier` | VARCHAR(20) | NOT NULL, default `SYSTEM` (`SYSTEM` \| `CUSTOM`) |
| `module` | VARCHAR(50) | NOT NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL |

---

### `iam.roles`
Organization-scoped roles that group permissions.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed |
| `name` | VARCHAR(100) | NOT NULL |
| `description` | VARCHAR(500) | nullable |
| `is_system_role` | BOOLEAN | NOT NULL, default `false` |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(organization_id, name)`

---

### `iam.role_permissions`
Junction — which permissions belong to a role.

| Column | Type | Constraints |
|---|---|---|
| `role_id` | UUID | PK, FK → `iam.roles.id` CASCADE |
| `permission_id` | UUID | PK, FK → `iam.permissions.id` CASCADE |

---

### `iam.users`
All users (faculty, staff, admins). Students link via `linked_student_id`.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed |
| `email` | VARCHAR(255) | NOT NULL, UNIQUE |
| `full_name` | VARCHAR(255) | NOT NULL |
| `title` | VARCHAR(20) | nullable |
| `first_name` | VARCHAR(100) | nullable |
| `middle_name` | VARCHAR(100) | nullable |
| `last_name` | VARCHAR(100) | nullable |
| `faculty_type` | VARCHAR(50) | nullable |
| `nid` | VARCHAR(50) | nullable |
| `department_id` | UUID | nullable, FK → `org.departments.id` |
| `designation` | VARCHAR(100) | nullable |
| `contact_number` | VARCHAR(50) | nullable |
| `qualification` | VARCHAR(255) | nullable |
| `experience_years` | SMALLINT | nullable |
| `status` | VARCHAR(20) | NOT NULL, default `ACTIVE` |
| `linked_student_id` | UUID | nullable, UNIQUE (partial — where not null) |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

---

### `iam.password_credentials`
Hashed passwords, one per user.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | NOT NULL, UNIQUE, FK → `iam.users.id` CASCADE |
| `hashed_password` | VARCHAR(255) | NOT NULL |
| `must_change_password` | BOOLEAN | NOT NULL, default `false` |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

---

### `iam.refresh_tokens`
Issued refresh tokens, revokable.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | NOT NULL, indexed, FK → `iam.users.id` CASCADE |
| `token_hash` | VARCHAR(64) | NOT NULL, UNIQUE |
| `expires_at` | TIMESTAMPTZ | NOT NULL |
| `revoked_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | NOT NULL |

---

### `iam.user_role_assignments`
Assigns a role to a user, optionally scoped to a program.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | NOT NULL, indexed, FK → `iam.users.id` CASCADE |
| `role_id` | UUID | NOT NULL, FK → `iam.roles.id` RESTRICT |
| `scope_type` | VARCHAR(20) | NOT NULL (`GLOBAL` \| `PROGRAM`) |
| `scope_id` | UUID | nullable |
| `assigned_by` | UUID | nullable, FK → `iam.users.id` SET NULL |
| `assigned_at` | TIMESTAMPTZ | NOT NULL |
| `removed_at` | TIMESTAMPTZ | nullable |

**Unique (partial):** `(user_id, scope_type, scope_id)` where `removed_at IS NULL`

---

## org

### `org.organizations`
Top-level tenant record.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `name` | VARCHAR(255) | NOT NULL |
| `short_name` | VARCHAR(50) | NOT NULL, UNIQUE |
| `description` | TEXT | nullable |
| `vision` | TEXT | nullable |
| `mission` | TEXT | nullable |
| `logo_file_key` | VARCHAR(500) | nullable |
| `website` | VARCHAR(255) | nullable |
| `address_street` | VARCHAR(255) | nullable |
| `address_city` | VARCHAR(100) | nullable |
| `address_country` | VARCHAR(100) | nullable |
| `address_postal_code` | VARCHAR(20) | nullable |
| `contact_email` | VARCHAR(255) | nullable |
| `contact_phone` | VARCHAR(50) | nullable |
| `email_validation_regex` | VARCHAR(500) | nullable |
| `status` | VARCHAR(20) | NOT NULL, default `ACTIVE` |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

---

### `org.departments`
Academic departments within an organization.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed, FK → `org.organizations.id` RESTRICT |
| `name` | VARCHAR(200) | NOT NULL |
| `short_name` | VARCHAR(30) | NOT NULL |
| `year_established` | SMALLINT | nullable |
| `description` | TEXT | nullable |
| `vision` | TEXT | nullable |
| `mission` | TEXT | nullable |
| `status` | VARCHAR(20) | NOT NULL, default `ACTIVE` |
| `archived_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique (partial):** `(organization_id, short_name)` where `status = 'ACTIVE'`

---

### `org.department_head_history`
Tracks who has been Head of Department and when.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `department_id` | UUID | NOT NULL, indexed, FK → `org.departments.id` RESTRICT |
| `user_id` | UUID | NOT NULL |
| `effective_from` | DATE | NOT NULL |
| `effective_to` | DATE | nullable |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Unique (partial):** `(department_id)` where `effective_to IS NULL` *(one active HoD at a time)*

---

### `org.programs`
Degree programs offered by a department.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed, FK → `org.organizations.id` RESTRICT |
| `department_id` | UUID | NOT NULL, indexed, FK → `org.departments.id` RESTRICT |
| `title` | VARCHAR(255) | NOT NULL |
| `acronym` | VARCHAR(20) | NOT NULL |
| `program_type` | VARCHAR(20) | NOT NULL (`UNDERGRADUATE` \| `POSTGRADUATE` \| `PHD`) |
| `minimum_duration_semesters` | SMALLINT | NOT NULL |
| `total_credits` | SMALLINT | NOT NULL |
| `study_mode` | VARCHAR(20) | NOT NULL (`FULL_TIME` \| `PART_TIME`) |
| `description` | TEXT | nullable |
| `status` | VARCHAR(20) | NOT NULL, default `ACTIVE` |
| `archived_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique (partial):** `(organization_id, acronym)` where `status = 'ACTIVE'`

---

## config

Reference / lookup data, all organization-scoped.

### `config.bloom_domains`
Bloom's Taxonomy domains (e.g., Cognitive, Affective).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed |
| `name` | VARCHAR(100) | NOT NULL |
| `description` | TEXT | nullable |
| `is_active` | BOOLEAN | NOT NULL, default `true` |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(organization_id, name)`

---

### `config.bloom_levels`
Levels within a Bloom's domain (e.g., Remember, Understand, Apply…).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed |
| `bloom_domain_id` | UUID | NOT NULL, indexed, FK → `config.bloom_domains.id` RESTRICT |
| `code` | VARCHAR(10) | NOT NULL |
| `name` | VARCHAR(100) | NOT NULL |
| `order_index` | SMALLINT | NOT NULL |
| `is_active` | BOOLEAN | NOT NULL, default `true` |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(organization_id, bloom_domain_id, code)`

---

### `config.delivery_methods`
Teaching delivery methods (e.g., Lecture, Lab, Online).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed |
| `name` | VARCHAR(100) | NOT NULL |
| `description` | TEXT | nullable |
| `is_active` | BOOLEAN | NOT NULL, default `true` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(organization_id, name)`

---

### `config.course_types`
Course category labels (e.g., Theory, Lab, Project).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed |
| `name` | VARCHAR(100) | NOT NULL |
| `description` | TEXT | nullable |
| `is_active` | BOOLEAN | NOT NULL, default `true` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(organization_id, name)`

---

### `config.assessment_types`
Types of assessments (e.g., Quiz, Mid-term, Final, Lab Report).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed |
| `name` | VARCHAR(100) | NOT NULL |
| `is_sessional` | BOOLEAN | NOT NULL, default `false` |
| `is_active` | BOOLEAN | NOT NULL, default `true` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(organization_id, name)`

---

### `config.complex_problems`
WK1–WK6 style complex-engineering-problem descriptors.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed |
| `code` | VARCHAR(20) | NOT NULL |
| `name` | VARCHAR(150) | nullable |
| `description` | TEXT | NOT NULL |
| `is_active` | BOOLEAN | NOT NULL, default `true` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(organization_id, code)`

---

### `config.complex_activities`
WA1–WA5 style complex-engineering-activity descriptors.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed |
| `code` | VARCHAR(20) | NOT NULL |
| `name` | VARCHAR(150) | nullable |
| `description` | TEXT | NOT NULL |
| `is_active` | BOOLEAN | NOT NULL, default `true` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(organization_id, code)`

---

### `config.knowledge_profiles`
Knowledge profile codes (e.g., P1 Mathematics, P2 Natural Sciences).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed |
| `code` | VARCHAR(20) | NOT NULL |
| `description` | TEXT | NOT NULL |
| `is_active` | BOOLEAN | NOT NULL, default `true` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(organization_id, code)`

---

### `config.po_types`
Program Outcome type labels (e.g., Domain Knowledge, Ethics).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed |
| `name` | VARCHAR(150) | NOT NULL |
| `description` | TEXT | nullable |
| `is_active` | BOOLEAN | NOT NULL, default `true` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(organization_id, name)`

---

### `config.mapping_weight_labels`
Human-readable labels for CO→PO mapping weights (1 = Low, 2 = Medium, 3 = High).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed |
| `weight_value` | SMALLINT | NOT NULL, CHECK `IN (1, 2, 3)` |
| `label` | VARCHAR(50) | NOT NULL |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(organization_id, weight_value)`

---

## curriculum

### `curriculum.curricula`
A versioned curriculum for a program.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, FK → `org.organizations.id` RESTRICT |
| `program_id` | UUID | NOT NULL, indexed, FK → `org.programs.id` RESTRICT |
| `name` | VARCHAR(255) | NOT NULL |
| `code` | VARCHAR(50) | NOT NULL |
| `effective_year` | SMALLINT | NOT NULL |
| `version_number` | SMALLINT | NOT NULL, default `1` |
| `parent_curriculum_id` | UUID | nullable, FK → `curriculum.curricula.id` RESTRICT *(self-ref)* |
| `status` | VARCHAR(20) | NOT NULL, default `DRAFT` (`DRAFT` \| `ACTIVE` \| `ARCHIVED`) |
| `archived_at` | TIMESTAMPTZ | nullable |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(program_id, code, version_number)`

---

### `curriculum.curriculum_term_definitions`
Semester definitions within a curriculum (Semester 1, Semester 2, …).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `curriculum_id` | UUID | NOT NULL, indexed, FK → `curriculum.curricula.id` RESTRICT |
| `term_number` | SMALLINT | NOT NULL |
| `name` | VARCHAR(100) | NOT NULL |
| `total_credit_hours` | SMALLINT | nullable |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(curriculum_id, term_number)`

---

### `curriculum.courses`
Master course catalog (organization-wide).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed, FK → `org.organizations.id` RESTRICT |
| `course_type_id` | UUID | NOT NULL, FK → `config.course_types.id` RESTRICT |
| `code` | VARCHAR(30) | NOT NULL |
| `title` | VARCHAR(255) | NOT NULL |
| `credits` | SMALLINT | NOT NULL |
| `theory_hours` | SMALLINT | NOT NULL, default `0` |
| `lab_hours` | SMALLINT | NOT NULL, default `0` |
| `description` | TEXT | nullable |
| `status` | VARCHAR(20) | NOT NULL, default `ACTIVE` |
| `archived_at` | TIMESTAMPTZ | nullable |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique (partial):** `(organization_id, code)` where `status = 'ACTIVE'`

---

### `curriculum.curriculum_course_slots`
Places a course into a specific semester of a curriculum.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `curriculum_id` | UUID | NOT NULL, indexed, FK → `curriculum.curricula.id` RESTRICT |
| `curriculum_term_definition_id` | UUID | NOT NULL, FK → `curriculum.curriculum_term_definitions.id` RESTRICT |
| `course_id` | UUID | NOT NULL, indexed, FK → `curriculum.courses.id` RESTRICT |
| `is_elective` | BOOLEAN | NOT NULL, default `false` |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(curriculum_id, course_id)` *(a course appears at most once per curriculum)*

---

### `curriculum.course_prerequisites`
Prerequisite relationships between courses.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, FK → `org.organizations.id` RESTRICT |
| `course_id` | UUID | NOT NULL, indexed, FK → `curriculum.courses.id` RESTRICT |
| `prerequisite_course_id` | UUID | NOT NULL, FK → `curriculum.courses.id` RESTRICT |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(course_id, prerequisite_course_id)`  
**Check:** `course_id != prerequisite_course_id`

---

### `curriculum.batches`
A student cohort enrolled in a curriculum (e.g., "BSCS 2024").

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed, FK → `org.organizations.id` RESTRICT |
| `curriculum_id` | UUID | NOT NULL, indexed, FK → `curriculum.curricula.id` RESTRICT |
| `name` | VARCHAR(100) | NOT NULL |
| `intake_year` | SMALLINT | NOT NULL |
| `graduation_year` | SMALLINT | nullable |
| `status` | VARCHAR(20) | NOT NULL, default `ACTIVE` (`ACTIVE` \| `GRADUATED` \| `ARCHIVED`) |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(curriculum_id, name)`

---

### `curriculum.academic_terms`
Calendar terms (e.g., Fall 2024, Spring 2025).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed, FK → `org.organizations.id` RESTRICT |
| `name` | VARCHAR(100) | NOT NULL |
| `year` | SMALLINT | NOT NULL |
| `season` | VARCHAR(20) | NOT NULL (`SPRING` \| `SUMMER` \| `FALL` \| `WINTER`) |
| `start_date` | DATE | NOT NULL |
| `end_date` | DATE | NOT NULL |
| `status` | VARCHAR(20) | NOT NULL, default `UPCOMING` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(organization_id, year, season)`

---

### `curriculum.sections`
Class sections (e.g., Section A, Section B).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, FK → `org.organizations.id` RESTRICT |
| `name` | VARCHAR(50) | NOT NULL |
| `capacity` | SMALLINT | nullable |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(organization_id, name)`

---

### `curriculum.section_offerings`
A specific course offered to a batch in a term and section.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed, FK → `org.organizations.id` RESTRICT |
| `curriculum_id` | UUID | NOT NULL, FK → `curriculum.curricula.id` RESTRICT |
| `batch_id` | UUID | NOT NULL, indexed, FK → `curriculum.batches.id` RESTRICT |
| `course_id` | UUID | NOT NULL, indexed, FK → `curriculum.courses.id` RESTRICT |
| `academic_term_id` | UUID | NOT NULL, indexed, FK → `curriculum.academic_terms.id` RESTRICT |
| `section_id` | UUID | NOT NULL, FK → `curriculum.sections.id` RESTRICT |
| `status` | VARCHAR(20) | NOT NULL, default `UPCOMING` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(batch_id, course_id, academic_term_id, section_id)`

---

### `curriculum.faculty_assignments`
Assigns a faculty member to a section offering with a role.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `section_offering_id` | UUID | NOT NULL, indexed, FK → `curriculum.section_offerings.id` RESTRICT |
| `user_id` | UUID | NOT NULL |
| `role_in_course` | VARCHAR(30) | NOT NULL (`MODULE_LEADER` \| `SECTION_TEACHER`) |
| `assigned_at` | TIMESTAMPTZ | NOT NULL |
| `removed_at` | TIMESTAMPTZ | nullable |

**Unique (partial):** `(section_offering_id, user_id, role_in_course)` where `removed_at IS NULL`

---

## obe

### `obe.program_outcomes`
Program-level outcomes (POs) for a program.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed, FK → `org.organizations.id` RESTRICT |
| `program_id` | UUID | NOT NULL, indexed, FK → `org.programs.id` RESTRICT |
| `bloom_domain_id` | UUID | nullable, FK → `config.bloom_domains.id` RESTRICT |
| `code` | VARCHAR(20) | NOT NULL |
| `reference` | VARCHAR(100) | nullable |
| `statement` | TEXT | NOT NULL |
| `po_type` | VARCHAR(100) | nullable |
| `order_index` | SMALLINT | NOT NULL |
| `status` | VARCHAR(20) | NOT NULL, default `ACTIVE` |
| `archived_at` | TIMESTAMPTZ | nullable |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique (partial):** `(program_id, code)` where `status = 'ACTIVE'`

---

### `obe.po_knowledge_profiles`
Junction — maps a PO to knowledge profiles.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `program_outcome_id` | UUID | NOT NULL, indexed, FK → `obe.program_outcomes.id` RESTRICT |
| `knowledge_profile_id` | UUID | NOT NULL, FK → `config.knowledge_profiles.id` RESTRICT |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(program_outcome_id, knowledge_profile_id)`

---

### `obe.course_outcomes`
Course-level outcomes (COs) for a specific course within a curriculum.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed, FK → `org.organizations.id` RESTRICT |
| `curriculum_id` | UUID | NOT NULL, indexed, FK → `curriculum.curricula.id` RESTRICT |
| `course_id` | UUID | NOT NULL, indexed, FK → `curriculum.courses.id` RESTRICT |
| `bloom_level_id` | UUID | nullable, FK → `config.bloom_levels.id` RESTRICT |
| `code` | VARCHAR(20) | NOT NULL |
| `statement` | TEXT | NOT NULL |
| `status` | VARCHAR(20) | NOT NULL, default `DRAFT` |
| `created_by_user_id` | UUID | nullable |
| `locked_at` | TIMESTAMPTZ | nullable |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(curriculum_id, course_id, code)`  
**Index:** `(curriculum_id, course_id, status)`

---

### `obe.co_delivery_methods`
Junction — teaching delivery methods used for a CO.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `course_outcome_id` | UUID | NOT NULL, indexed, FK → `obe.course_outcomes.id` RESTRICT |
| `delivery_method_id` | UUID | NOT NULL, FK → `config.delivery_methods.id` RESTRICT |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(course_outcome_id, delivery_method_id)`

---

### `obe.co_po_mapping_sets`
Container for a CO→PO mapping for a given course in a curriculum.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed, FK → `org.organizations.id` RESTRICT |
| `curriculum_id` | UUID | NOT NULL, indexed, FK → `curriculum.curricula.id` RESTRICT |
| `course_id` | UUID | NOT NULL, indexed, FK → `curriculum.courses.id` RESTRICT |
| `status` | VARCHAR(20) | NOT NULL, default `DRAFT` |
| `created_by_user_id` | UUID | nullable |
| `published_at` | TIMESTAMPTZ | nullable |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(curriculum_id, course_id)`

---

### `obe.co_po_mapping_entries`
Individual CO→PO weight entries within a mapping set.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `mapping_set_id` | UUID | NOT NULL, indexed, FK → `obe.co_po_mapping_sets.id` RESTRICT |
| `course_outcome_id` | UUID | NOT NULL, indexed, FK → `obe.course_outcomes.id` RESTRICT |
| `program_outcome_id` | UUID | NOT NULL, indexed, FK → `obe.program_outcomes.id` RESTRICT |
| `weight` | SMALLINT | NOT NULL, CHECK `IN (1, 2, 3)` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(mapping_set_id, course_outcome_id, program_outcome_id)`

---

### `obe.co_cp_mappings`
Maps a CO to complex-engineering problems.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, FK → `org.organizations.id` RESTRICT |
| `course_outcome_id` | UUID | NOT NULL, indexed, FK → `obe.course_outcomes.id` RESTRICT |
| `complex_problem_id` | UUID | NOT NULL, FK → `config.complex_problems.id` RESTRICT |
| `status` | VARCHAR(20) | NOT NULL, default `DRAFT` |
| `created_by_user_id` / `approved_by_user_id` | UUID | nullable |
| `approved_at` | TIMESTAMPTZ | nullable |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(course_outcome_id, complex_problem_id)`

---

### `obe.co_ca_mappings`
Maps a CO to complex-engineering activities.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, FK → `org.organizations.id` RESTRICT |
| `course_outcome_id` | UUID | NOT NULL, indexed, FK → `obe.course_outcomes.id` RESTRICT |
| `complex_activity_id` | UUID | NOT NULL, FK → `config.complex_activities.id` RESTRICT |
| `status` | VARCHAR(20) | NOT NULL, default `DRAFT` |
| `created_by_user_id` / `approved_by_user_id` | UUID | nullable |
| `approved_at` | TIMESTAMPTZ | nullable |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(course_outcome_id, complex_activity_id)`

---

### `obe.co_kp_mappings`
Maps a CO to knowledge profiles.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, FK → `org.organizations.id` RESTRICT |
| `course_outcome_id` | UUID | NOT NULL, indexed, FK → `obe.course_outcomes.id` RESTRICT |
| `knowledge_profile_id` | UUID | NOT NULL, FK → `config.knowledge_profiles.id` RESTRICT |
| `status` | VARCHAR(20) | NOT NULL, default `DRAFT` |
| `created_by_user_id` / `approved_by_user_id` | UUID | nullable |
| `approved_at` | TIMESTAMPTZ | nullable |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(course_outcome_id, knowledge_profile_id)`

---

## assessment

### `assessment.students`
Student records (separate from `iam.users`).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed, FK → `org.organizations.id` RESTRICT |
| `student_id_number` | VARCHAR(50) | NOT NULL |
| `full_name` | VARCHAR(255) | NOT NULL |
| `email` | VARCHAR(255) | nullable |
| `program_id` | UUID | nullable, indexed, FK → `org.programs.id` RESTRICT |
| `batch_id` | UUID | nullable, FK → `curriculum.batches.id` RESTRICT |
| `status` | VARCHAR(20) | NOT NULL, default `ACTIVE` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique (partial):** `(organization_id, student_id_number)` where `status != 'WITHDRAWN'`

---

### `assessment.student_enrollments`
Enrolls a student in a section offering.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, FK → `org.organizations.id` RESTRICT |
| `student_id` | UUID | NOT NULL, indexed, FK → `assessment.students.id` RESTRICT |
| `section_offering_id` | UUID | NOT NULL, indexed, FK → `curriculum.section_offerings.id` RESTRICT |
| `status` | VARCHAR(20) | NOT NULL, default `ACTIVE` |
| `enrolled_at` | TIMESTAMPTZ | NOT NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(student_id, section_offering_id)`

---

### `assessment.assessments`
An assessment instrument for a section offering (e.g., Quiz 1, Mid-Term).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed, FK → `org.organizations.id` RESTRICT |
| `section_offering_id` | UUID | NOT NULL, indexed, FK → `curriculum.section_offerings.id` RESTRICT |
| `assessment_type_id` | UUID | NOT NULL, FK → `config.assessment_types.id` RESTRICT |
| `name` | VARCHAR(255) | NOT NULL |
| `total_marks` | NUMERIC(6,2) | NOT NULL |
| `weightage_percent` | NUMERIC(5,2) | NOT NULL |
| `status` | VARCHAR(20) | NOT NULL, default `CONFIGURED` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

---

### `assessment.assessment_co_weights`
How much each CO contributes to an assessment (must sum to 100%).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `assessment_id` | UUID | NOT NULL, indexed, FK → `assessment.assessments.id` RESTRICT |
| `course_outcome_id` | UUID | NOT NULL, indexed, FK → `obe.course_outcomes.id` RESTRICT |
| `contribution_percent` | NUMERIC(5,2) | NOT NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(assessment_id, course_outcome_id)`

---

### `assessment.student_marks`
Marks obtained by a student on an assessment.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, FK → `org.organizations.id` RESTRICT |
| `assessment_id` | UUID | NOT NULL, indexed, FK → `assessment.assessments.id` RESTRICT |
| `student_enrollment_id` | UUID | NOT NULL, indexed, FK → `assessment.student_enrollments.id` RESTRICT |
| `marks_obtained` | NUMERIC(6,2) | nullable |
| `is_absent` | BOOLEAN | NOT NULL, default `false` |
| `entered_by_user_id` | UUID | nullable |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(assessment_id, student_enrollment_id)`  
**Check:** `(is_absent = true AND marks_obtained IS NULL) OR (is_absent = false AND marks_obtained IS NOT NULL)`

---

### `assessment.result_publications`
Tracks the approval workflow for publishing results of a section offering.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, FK → `org.organizations.id` RESTRICT |
| `section_offering_id` | UUID | NOT NULL, indexed, UNIQUE, FK → `curriculum.section_offerings.id` RESTRICT |
| `status` | VARCHAR(20) | NOT NULL, default `DRAFT` |
| `submitted_by_user_id` | UUID | nullable |
| `submitted_at` | TIMESTAMPTZ | nullable |
| `ml_approved_by_user_id` | UUID | nullable |
| `ml_approved_at` | TIMESTAMPTZ | nullable |
| `ml_rejection_comment` | TEXT | nullable |
| `pc_approved_by_user_id` | UUID | nullable |
| `pc_approved_at` | TIMESTAMPTZ | nullable |
| `published_by_user_id` | UUID | nullable |
| `published_at` | TIMESTAMPTZ | nullable |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

---

## attainment

### `attainment.attainment_configs`
Threshold configuration for attainment calculation, per program or org-wide.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed, FK → `org.organizations.id` RESTRICT |
| `program_id` | UUID | nullable, indexed, FK → `org.programs.id` RESTRICT |
| `threshold_student_pct` | NUMERIC(5,2) | NOT NULL, default `50.00` |
| `threshold_co_score_pct` | NUMERIC(5,2) | NOT NULL, default `50.00` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(organization_id, program_id)`  
**Unique (partial):** `(organization_id)` where `program_id IS NULL` *(org-wide default)*

---

### `attainment.co_attainment_results`
Calculated CO attainment results per section offering.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, FK → `org.organizations.id` RESTRICT |
| `section_offering_id` | UUID | NOT NULL, indexed, FK → `curriculum.section_offerings.id` RESTRICT |
| `course_outcome_id` | UUID | NOT NULL, indexed, FK → `obe.course_outcomes.id` RESTRICT |
| `average_attainment_pct` | NUMERIC(5,2) | NOT NULL |
| `students_above_threshold` | INTEGER | NOT NULL |
| `total_students` | INTEGER | NOT NULL |
| `is_attained` | BOOLEAN | NOT NULL |
| `calculated_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(section_offering_id, course_outcome_id)`

---

### `attainment.po_attainment_results`
Aggregated PO attainment results, derived from CO attainment.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, FK → `org.organizations.id` RESTRICT |
| `section_offering_id` | UUID | NOT NULL, indexed, FK → `curriculum.section_offerings.id` RESTRICT |
| `program_outcome_id` | UUID | NOT NULL, indexed, FK → `obe.program_outcomes.id` RESTRICT |
| `attainment_pct` | NUMERIC(5,2) | NOT NULL |
| `contributing_co_count` | INTEGER | NOT NULL |
| `is_attained` | BOOLEAN | NOT NULL |
| `calculated_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(section_offering_id, program_outcome_id)`

---

## approval

### `approval.review_comments`
Free-text review comments attached to any approvable entity.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed, FK → `org.organizations.id` RESTRICT |
| `entity_type` | VARCHAR(50) | NOT NULL |
| `entity_id` | UUID | NOT NULL |
| `author_user_id` | UUID | NOT NULL |
| `comment` | TEXT | NOT NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Index:** `(entity_type, entity_id)`

---

## audit

### `audit.audit_logs`
Immutable record of all state-changing actions.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | nullable, indexed, FK → `org.organizations.id` RESTRICT |
| `actor_user_id` | UUID | nullable |
| `entity_type` | VARCHAR(50) | NOT NULL |
| `entity_id` | UUID | NOT NULL |
| `action` | VARCHAR(50) | NOT NULL |
| `before_status` | VARCHAR(30) | nullable |
| `after_status` | VARCHAR(30) | nullable |
| `extra` | TEXT | nullable *(JSON)* |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Indexes:** `(entity_type, entity_id)`, `(actor_user_id)`

---

## notification

### `notification.notifications`
In-app notifications delivered to users.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed, FK → `org.organizations.id` RESTRICT |
| `recipient_user_id` | UUID | NOT NULL |
| `notification_type` | VARCHAR(50) | NOT NULL |
| `title` | VARCHAR(255) | NOT NULL |
| `body` | TEXT | nullable |
| `entity_type` | VARCHAR(50) | nullable |
| `entity_id` | UUID | nullable |
| `is_read` | BOOLEAN | NOT NULL, default `false` |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `read_at` | TIMESTAMPTZ | nullable |

**Index:** `(recipient_user_id, is_read)`

---

## accreditation

### `accreditation.accreditation_cycles`
An accreditation review cycle for a program (e.g., ABET 2023–2026).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `organization_id` | UUID | NOT NULL, indexed, FK → `org.organizations.id` RESTRICT |
| `program_id` | UUID | NOT NULL, indexed, FK → `org.programs.id` RESTRICT |
| `name` | VARCHAR(255) | NOT NULL |
| `accreditation_body` | VARCHAR(50) | NOT NULL |
| `cycle_start_year` | SMALLINT | NOT NULL |
| `cycle_end_year` | SMALLINT | NOT NULL |
| `status` | VARCHAR(20) | NOT NULL, default `DRAFT` |
| `created_by_user_id` | UUID | nullable |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

---

### `accreditation.accreditation_criteria`
Criteria within a cycle (e.g., Criterion 1 — Student Outcomes).

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `cycle_id` | UUID | NOT NULL, indexed, FK → `accreditation.accreditation_cycles.id` CASCADE |
| `code` | VARCHAR(30) | NOT NULL |
| `title` | VARCHAR(255) | NOT NULL |
| `description` | TEXT | nullable |
| `order_index` | SMALLINT | NOT NULL, default `0` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(cycle_id, code)`

---

### `accreditation.criterion_po_mappings`
Links an accreditation criterion to program outcomes.

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `criterion_id` | UUID | NOT NULL, indexed, FK → `accreditation.accreditation_criteria.id` CASCADE |
| `program_outcome_id` | UUID | NOT NULL, indexed, FK → `obe.program_outcomes.id` RESTRICT |
| `notes` | TEXT | nullable |
| `created_at` | TIMESTAMPTZ | NOT NULL |

**Unique:** `(criterion_id, program_outcome_id)`

---

## Cross-Schema Relationship Summary

```
org.organizations
  └── org.departments
        └── org.programs
              ├── curriculum.curricula
              │     ├── curriculum.curriculum_term_definitions
              │     ├── curriculum.curriculum_course_slots ──► curriculum.courses
              │     ├── curriculum.batches
              │     │     └── curriculum.section_offerings ──► curriculum.academic_terms
              │     │           │                           ──► curriculum.sections
              │     │           ├── curriculum.faculty_assignments
              │     │           ├── assessment.student_enrollments ──► assessment.students
              │     │           ├── assessment.assessments
              │     │           │     └── assessment.assessment_co_weights ──► obe.course_outcomes
              │     │           ├── assessment.student_marks
              │     │           ├── assessment.result_publications
              │     │           ├── attainment.co_attainment_results ──► obe.course_outcomes
              │     │           └── attainment.po_attainment_results ──► obe.program_outcomes
              │     └── obe.co_po_mapping_sets
              │           └── obe.co_po_mapping_entries
              ├── obe.program_outcomes ──► config.bloom_domains
              │     └── obe.po_knowledge_profiles ──► config.knowledge_profiles
              └── obe.course_outcomes ──► config.bloom_levels
                    ├── obe.co_delivery_methods ──► config.delivery_methods
                    ├── obe.co_cp_mappings ──► config.complex_problems
                    ├── obe.co_ca_mappings ──► config.complex_activities
                    └── obe.co_kp_mappings ──► config.knowledge_profiles

iam.users ──► org.departments (optional)
  ├── iam.password_credentials
  ├── iam.refresh_tokens
  └── iam.user_role_assignments ──► iam.roles
                                          └── iam.role_permissions ──► iam.permissions
```
