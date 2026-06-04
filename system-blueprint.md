# OBE Accreditation Management Platform
## System Blueprint — Final Architecture Document v1.0

> **Status:** AUTHORITATIVE. This document supersedes and consolidates:  
> FRD v1.0 · DDD Analysis v1.0 · DB Architecture v1.0 · RBAC Architecture v1.0 · Backend Architecture v1.0  
> **Date:** 2026-06-04  
> **Contradictions resolved in §6. Build order in §7.**

---

## Table of Contents

1. [Final System Architecture Overview](#1-final-system-architecture-overview)
2. [Final Module Structure](#2-final-module-structure)
3. [Final Data Ownership Rules](#3-final-data-ownership-rules)
4. [Final Permission-to-Feature Mapping](#4-final-permission-to-feature-mapping)
5. [Final Workflow — End to End](#5-final-workflow--end-to-end)
6. [Final Consistency Checks](#6-final-consistency-checks)
7. [Final Build Order](#7-final-build-order)

---

# 1. Final System Architecture Overview

## 1.1 Layered System Diagram

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           PRESENTATION LAYER                                ║
║                                                                              ║
║   Next.js (App Router)                                                       ║
║   ├── Server Components   (data fetching, SSR for initial page load)         ║
║   ├── Client Components   (interactive forms, real-time updates)             ║
║   ├── Permission Manifest (cached on login; drives UI visibility)            ║
║   └── API Client          (typed, auto-generated from OpenAPI spec)          ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │ HTTPS (via Nginx TLS)
                                    │ /api/v1/*
╔══════════════════════════════════════════════════════════════════════════════╗
║                              API GATEWAY                                     ║
║                                                                              ║
║   Nginx                                                                      ║
║   ├── TLS termination                                                        ║
║   ├── HTTP → HTTPS redirect                                                  ║
║   ├── Rate limiting (edge layer)                                             ║
║   └── Reverse proxy → FastAPI                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
╔══════════════════════════════════════════════════════════════════════════════╗
║                            BACKEND LAYER                                     ║
║                                                                              ║
║   FastAPI (Gunicorn + 4× Uvicorn workers)                                    ║
║   │                                                                          ║
║   ├── Middleware Chain                                                       ║
║   │   CorrelationID → Organization → RateLimit → Audit(post-response)        ║
║   │                                                                          ║
║   ├── 12 API Modules (see §2)                                                ║
║   │   Each: Router → Schemas → Dependencies → Service → Repository          ║
║   │                                                                          ║
║   ├── Authorization Layer                                                    ║
║   │   JWT Validation → Permission Check → Scope Gate → Assignment Gate       ║
║   │                                                                          ║
║   ├── In-Process Event Bus                                                   ║
║   │   Domain events → cache invalidation, in-app notifications               ║
║   │                                                                          ║
║   └── Transactional Outbox                                                   ║
║       Persistent events → ARQ Worker → audit, emails, integrations          ║
║                                                                              ║
║   ARQ Worker (separate process)                                              ║
║   ├── Attainment calculation jobs                                            ║
║   ├── Report generation jobs                                                 ║
║   ├── Email delivery jobs                                                    ║
║   └── Outbox relay + cleanup jobs                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
╔══════════════════════════════════════════════════════════════════════════════╗
║                             DOMAIN LAYER                                     ║
║                                                                              ║
║   Pure Python — no framework imports                                         ║
║   ├── Domain Entities     (state machines, invariant enforcement)            ║
║   ├── Domain Services     (PrerequisiteGraphValidator,                       ║
║   │                        AttainmentCalculationEngine,                      ║
║   │                        MappingMatrixSnapshotBuilder,                     ║
║   │                        WeightageValidator,                               ║
║   │                        ApprovalChainResolver,                            ║
║   │                        PermissionManifestBuilder)                        ║
║   ├── Value Objects       (Email, MappingWeight, WorkflowState, etc.)        ║
║   └── Domain Events       (50+ typed event classes)                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
╔══════════════════════════════════════════════════════════════════════════════╗
║                              DATA LAYER                                      ║
║                                                                              ║
║   PostgreSQL 16                   Redis 7.2           MinIO                  ║
║   ├── 12 schemas                  ├── auth:*           ├── org/logos/        ║
║   │   (one per module)            ├── data:*           ├── reports/          ║
║   ├── asyncpg driver              ├── ratelimit:*      └── accreditation/    ║
║   ├── SQLAlchemy 2.0 async        └── job:*                                  ║
║   └── Alembic migrations                                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                    │
╔══════════════════════════════════════════════════════════════════════════════╗
║                          INFRASTRUCTURE LAYER                                ║
║                                                                              ║
║   Docker Compose (single-server deployment)                                  ║
║   ├── Services: nginx, api, worker, postgres, redis, minio                   ║
║   ├── Networks: internal (api↔data), external (nginx↔api)                    ║
║   └── Volumes: postgres_data, redis_data, minio_data                        ║
║                                                                              ║
║   Observability                                                              ║
║   ├── Structured JSON logs (stdout → log aggregator)                        ║
║   ├── Prometheus metrics at /metrics                                         ║
║   └── OpenTelemetry traces (correlation ID as trace ID)                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## 1.2 Cross-Layer Data Flow

```
User Action (browser)
  │
  ▼ HTTPS request
Nginx → FastAPI Router
  │
  ▼ FastAPI Depends
JWT decoded → user loaded → permission manifest from Redis
  │
  ▼ Permission Check (Gate 1 + 2 + 2b)
Application Service (use case)
  │
  ├── Domain entity loaded via Repository (PostgreSQL)
  ├── Business logic executed on domain entity
  ├── Changes persisted via Unit of Work (commit = DB + outbox in one TX)
  └── Domain events staged
  │
  ▼ After commit
In-Process Event Bus
  ├── Invalidate Redis cache keys
  └── Write in-app notifications to DB
  │
  ▼ Async (ARQ Worker)
Outbox Relay → Audit events → Email queue → External integrations
  │
  ▼ HTTP Response → Next.js → Browser
```

---

# 2. Final Module Structure

## 2.1 Authoritative Module Boundaries

The platform has **12 backend modules**. Each maps 1:1 to a PostgreSQL schema and a Python package under `app/modules/`.

| # | Module Name | Python Package | DB Schema | Domain Classification |
|---|---|---|---|---|
| 1 | **Auth & RBAC** | `iam` | `iam` | Generic |
| 2 | **Organization** | `org` | `org` | Generic |
| 3 | **Reference Data** | `ref_data` | `config` | Generic |
| 4 | **Curriculum** | `curriculum` | `curriculum` | Core |
| 5 | **OBE** | `obe` | `obe` | Core |
| 6 | **Assessment** | `assessment` | `assessment` | Supporting |
| 7 | **Attainment** | `attainment` | `attainment` | Core |
| 8 | **Approval** | `approval` | `approval` | Supporting |
| 9 | **Notification** | `notification` | `notification` | Supporting |
| 10 | **Audit** | `audit` | `audit` | Generic |
| 11 | **Accreditation** | `accreditation` | `accreditation` | Core |
| 12 | **Reporting** | `reporting` | `reporting` | Supporting |

> **Note on naming:** The Python package is `ref_data` (not `config`) because `config` conflicts with Python conventions. The PostgreSQL schema remains `config`. This naming split is intentional and final.

## 2.2 Module Responsibilities

### Module 1: Auth & RBAC (`iam`)

**Owns:** Users, roles, permissions, role assignments, password credentials, refresh tokens.

**Exposes:**
- `POST /auth/login` `POST /auth/refresh` `POST /auth/logout`
- `POST /auth/password-reset-request` `POST /auth/password-reset-confirm`
- `GET/POST/PATCH /users`
- `GET/POST/PATCH /roles` `GET/POST/DELETE /roles/{id}/permissions`
- `GET /me/permissions` (returns permission manifest)

**Key services:** `AuthService`, `UserService`, `PermissionManifestBuilder`

**Does NOT own:** Student identity (owned by `assessment`), faculty-course assignment (owned by `curriculum`)

---

### Module 2: Organization (`org`)

**Owns:** Organization (1 record), departments, programs, department head history.

**Exposes:**
- `GET/PATCH /organization`
- `GET/POST/PATCH /departments`
- `GET/POST/PATCH /programs`

**Programs live here.** The Program Coordinator interacts with programs through OBE and curriculum modules, but the program record itself is defined and owned here by Super Admin.

---

### Module 3: Reference Data (`ref_data`)

**Owns:** Bloom domains, bloom levels, delivery methods, course types, assessment types, complex problems (CP), complex activities (CA), knowledge profiles (KP), mapping weight labels.

**Exposes:**
- `GET/POST/PATCH /ref-data/bloom-domains`
- `GET/POST/PATCH /ref-data/bloom-levels`
- `GET/POST/PATCH /ref-data/delivery-methods`
- `GET/POST/PATCH /ref-data/course-types`
- `GET/POST/PATCH /ref-data/assessment-types`
- `GET/POST/PATCH /ref-data/complex-problems`
- `GET/POST/PATCH /ref-data/complex-activities`
- `GET/POST/PATCH /ref-data/knowledge-profiles`
- `GET/PATCH /ref-data/mapping-weights`

All reference data is cached in Redis at `ref_data:{org_id}:{type}` with a 1-hour TTL.

---

### Module 4: Curriculum (`curriculum`)

**Owns:** Curricula (with versioning), curriculum term definitions, courses, course prerequisites, curriculum course slots, batches, academic terms (operational), sections, section offerings, faculty assignments.

**Exposes:**
- `GET/POST/PATCH /curricula` + `POST /curricula/{id}/version`
- `GET/POST/PATCH /courses`
- `GET/POST /courses/{id}/prerequisites`
- `GET/POST/PATCH /batches`
- `GET/POST/PATCH /academic-terms`
- `GET/POST/PATCH /sections`
- `GET/POST/PATCH /section-offerings`
- `GET/POST/PATCH /faculty-assignments`

**Section Offering** is the atomic unit of course delivery. Everything in Assessment and Attainment roots to a `section_offering_id`.

---

### Module 5: OBE (`obe`)

**Owns:** Program outcomes (POs), course outcomes (COs), CO delivery method links, CO-PO mapping sets and entries, CO-CP mappings, CO-CA mappings, CO-KP mappings.

**Exposes:**
- `GET/POST/PATCH /program-outcomes`
- `GET/POST/PATCH /course-outcomes`
- `POST /course-outcomes/{id}/submit`
- `POST /course-outcomes/{id}/approve`
- `POST /course-outcomes/{id}/reject`
- `POST /course-outcomes/{id}/publish`
- `GET/POST/PATCH /mappings/co-po` + `POST /mappings/co-po/{id}/publish`
- `GET/POST/PATCH /mappings/co-cp`
- `GET/POST/PATCH /mappings/co-ca`
- `GET/POST/PATCH /mappings/co-kp`

**COs are scoped to `curriculum_id + course_id`.** They are not scoped to section offerings. A CO belongs to a course within a curriculum version.

---

### Module 6: Assessment (`assessment`)

**Owns:** Students, student enrollments, assessments, assessment-CO weights, student marks, result publications.

**Exposes:**
- `GET/POST/PATCH /students`
- `GET/POST /enrollments`
- `GET/POST/PATCH /assessments`
- `GET/POST/PATCH /assessments/{id}/co-weights`
- `GET/POST/PATCH /marks`
- `GET/POST /results/{section_offering_id}/submit`
- `POST /results/{section_offering_id}/approve-ml`
- `POST /results/{section_offering_id}/approve-pc`
- `POST /results/{section_offering_id}/publish`

---

### Module 7: Attainment (`attainment`)

**Owns:** Attainment configurations, attainment runs (with JSONB snapshots), CO attainment results, course attainment results, PO attainment results.

**Exposes:**
- `GET/POST/PATCH /attainment/config/{section_offering_id}`
- `POST /attainment/runs` (initiate)
- `GET /attainment/runs/{id}`
- `POST /attainment/runs/{id}/publish`
- `GET /attainment/trend/po` (cross-run PO trend — query service)
- `GET /attainment/trend/co` (cross-run CO trend — query service)

**Attainment runs are never edited.** A new run is initiated if results need to be recalculated. Old runs are immutable.

---

### Module 8: Approval (`approval`)

**Owns:** Workflow definitions, workflow step definitions, approval requests, approval step records, delegate approvers.

**Exposes:**
- `GET /approval/requests` (inbox for the current user)
- `POST /approval/requests/{id}/act` (approve / reject / request-revision)
- `GET/POST /approval/delegates`

**The approval module does not own the entity being approved.** It tracks the workflow state. The entity (CO, result, attainment run) holds its own status. When the approval chain completes, the approval module emits `ApprovalChainCompleted`, and the entity's own service transitions its status.

---

### Module 9: Notification (`notification`)

**Owns:** Notification templates, notification queue (email), in-app notifications.

**Exposes:**
- `GET /notifications` (in-app inbox, paginated)
- `GET /notifications/unread-count`
- `PATCH /notifications/{id}/read`
- `PATCH /notifications/read-all`
- `GET/PATCH /notification-templates` (admin only)

**Notification writes are triggered by domain events only.** No service outside this module writes directly to notification tables.

---

### Module 10: Audit (`audit`)

**Owns:** `audit.audit_events` (append-only, read-only via API).

**Exposes:**
- `GET /audit` (filter by entity_type, entity_id, actor, date range, action)
- `GET /audit/{entity_type}/{entity_id}` (full history of one entity)

**The audit module never writes directly.** All writes come from the outbox relay worker's `AuditEventHandler`. The API surface is read-only.

---

### Module 11: Accreditation (`accreditation`)

**Owns:** Accreditation bodies, accreditation cycles, accreditation reports.

**Exposes:**
- `GET/POST/PATCH /accreditation/bodies`
- `GET/POST/PATCH /accreditation/cycles`
- `GET/POST /accreditation/reports`

Accreditation reports pull data via the `AccreditationEvidenceQueryService`, which reads from attainment, OBE, and curriculum schemas via read-only query services. No writes to other schemas.

---

### Module 12: Reporting (`reporting`)

**Owns:** Report definitions, report runs.

**Exposes:**
- `GET /reports/definitions` (catalog of available reports)
- `POST /reports/runs` (request a report, returns run_id immediately)
- `GET /reports/runs/{id}` (poll for status)
- `GET /reports/runs/{id}/download` (returns pre-signed MinIO URL)

Report generation is always async. All heavy computation runs in the ARQ worker. The API never blocks waiting for a report.

---

## 2.3 Module Dependency Graph

```
ref_data ─────────────────────────────────────────────────────────────┐
org ──────────────────────────────────────────────────────────────────┤
iam ──────────────────────────────────────────────────────────────────┤
                                                                       │
curriculum ── reads: org, ref_data ────────────────────────────────── │
obe ──────── reads: curriculum, org, ref_data ─────────────────────── │
assessment ─ reads: curriculum, obe ──────────────────────────────── ─┤
attainment ─ reads: assessment, obe, curriculum ──────────────────────┤
approval ─── reads: iam (roles) ──────────────────────────────────────┤
notification reads: iam (users) ──────────────────────────────────────┤
                                                                       │
accreditation reads: attainment, obe, curriculum, org ────────────────┤
reporting ─── reads: ALL modules (query services only) ───────────────┘
audit ──────── writes: outbox worker only; reads: API ────────────────┘

Rule: arrows go one direction only. No circular dependencies.
Lower modules never import from higher modules.
```

---

# 3. Final Data Ownership Rules

For every major entity: which module owns it, who can write to it, who can read it, and when it becomes immutable.

## 3.1 Organization & Structure Entities

| Entity | Owner Module | Can Modify | Can Read | Locked When |
|---|---|---|---|---|
| `org.organizations` | `org` | Super Admin | All authenticated users (read) | Never deleted; status always ACTIVE |
| `org.departments` | `org` | Super Admin | All authenticated users | Status = ARCHIVED (no delete) |
| `org.programs` | `org` | Super Admin (create/archive); Program Coordinator (update description/vision only) | All authenticated users | Status = ARCHIVED |
| `config.*` tables | `ref_data` | Super Admin | All modules (via cache) | is_active = FALSE; existing references preserved |
| `iam.users` | `iam` | Super Admin (create/deactivate); User (own password) | Super Admin, Coordinator (within scope) | Status = DEACTIVATED; never deleted |
| `iam.roles` | `iam` | Super Admin | All authenticated (own permissions only) | is_system_role = TRUE roles cannot be deleted |
| `iam.permissions` | `iam` | Super Admin (CUSTOM tier only); SYSTEM tier = code-only | All (own manifest) | SYSTEM tier: immutable |

## 3.2 Curriculum Entities

| Entity | Owner Module | Can Modify | Can Read | Locked When |
|---|---|---|---|---|
| `curriculum.curricula` | `curriculum` | Program Coordinator (PROGRAM scope) | All authenticated | Status = ARCHIVED or VERSIONED |
| `curriculum.courses` | `curriculum` | Program Coordinator | All authenticated | Status = ARCHIVED |
| `curriculum.course_prerequisites` | `curriculum` | Program Coordinator | All authenticated | When curriculum is ARCHIVED |
| `curriculum.curriculum_course_slots` | `curriculum` | Program Coordinator | All authenticated | When curriculum status != DRAFT |
| `curriculum.academic_terms` | `curriculum` | Program Coordinator | All authenticated | Status = COMPLETED |
| `curriculum.sections` | `curriculum` | Program Coordinator | All authenticated | Never locked |
| `curriculum.section_offerings` | `curriculum` | Program Coordinator | Coordinator, ML, Teacher (assigned) | Status = COMPLETED |
| `curriculum.faculty_assignments` | `curriculum` | Program Coordinator | Coordinator (all), ML/Teacher (own) | `removed_at` set; not locked per se |
| `curriculum.batches` | `curriculum` | Program Coordinator | Coordinator, ML, Teacher (within program) | Status = GRADUATED or ARCHIVED |

## 3.3 OBE Entities

| Entity | Owner Module | Can Modify | Can Read | Locked When |
|---|---|---|---|---|
| `obe.program_outcomes` | `obe` | Program Coordinator (PROGRAM scope) | All authenticated | Status = ARCHIVED (guarded by BR-02) |
| `obe.course_outcomes` | `obe` | Section Teacher (DRAFT only); ML (UNDER_REVIEW comments only); PC (all states before PUBLISHED) | All authenticated (within scope) | Status = LOCKED (triggered by AttainmentPublished event) |
| `obe.co_delivery_methods` | `obe` | Section Teacher (while CO is DRAFT/SUBMITTED) | All authenticated | When CO is PUBLISHED |
| `obe.co_po_mapping_sets` | `obe` | Program Coordinator | All authenticated | Status = PUBLISHED |
| `obe.co_po_mapping_entries` | `obe` | Program Coordinator | All authenticated | When mapping set is PUBLISHED |
| `obe.co_cp_mappings` | `obe` | Section Teacher (create); ML/PC (approve) | All authenticated | When CO is PUBLISHED |
| `obe.co_ca_mappings` | `obe` | Section Teacher (create); ML/PC (approve) | All authenticated | When CO is PUBLISHED |
| `obe.co_kp_mappings` | `obe` | Section Teacher (create); ML/PC (approve) | All authenticated | When CO is PUBLISHED |

## 3.4 Assessment Entities

| Entity | Owner Module | Can Modify | Can Read | Locked When |
|---|---|---|---|---|
| `assessment.students` | `assessment` | Super Admin (bulk import); Program Coordinator | Coordinator, ML, Teacher (assigned), Student (self) | Status = GRADUATED or WITHDRAWN |
| `assessment.student_enrollments` | `assessment` | Program Coordinator | Coordinator, ML, Teacher (assigned section), Student (self) | Status = COMPLETED or DROPPED |
| `assessment.assessments` | `assessment` | Program Coordinator (configure); Auto-locked post-publication | Coordinator, ML, Teacher (assigned section) | Status = LOCKED |
| `assessment.assessment_co_weights` | `assessment` | Program Coordinator (while assessment is CONFIGURED) | Coordinator, ML, Teacher (assigned) | When assessment is PUBLISHED |
| `assessment.student_marks` | `assessment` | Section Teacher (entered_by, before PUBLISHED); Auto-locked after | Teacher (assigned section, own entries), ML (read), PC (read), Student (own, PUBLISHED only) | When `result_publications.status = PUBLISHED` |
| `assessment.result_publications` | `assessment` | Each approver advances their step; PC publishes | Coordinator, ML, Teacher (assigned section) | Status = LOCKED |

## 3.5 Attainment Entities

| Entity | Owner Module | Can Modify | Can Read | Locked When |
|---|---|---|---|---|
| `attainment.attainment_configurations` | `attainment` | Program Coordinator | Coordinator, ML (read) | After first run is PUBLISHED |
| `attainment.attainment_runs` | `attainment` | Program Coordinator (initiate, review, publish); System (calculate) | Coordinator, ML, Teacher (read) | Status = PUBLISHED (append-only results) |
| `attainment.co_attainment_results` | `attainment` | System (ARQ worker, write-once) | Coordinator, ML | Immediately (append-only) |
| `attainment.course_attainment_results` | `attainment` | System (ARQ worker, write-once) | Coordinator, ML | Immediately (append-only) |
| `attainment.po_attainment_results` | `attainment` | System (ARQ worker, write-once) | Coordinator, ML, PC | Immediately (append-only) |

## 3.6 Infrastructure Entities

| Entity | Owner Module | Writeable By | Readable By | Deletable |
|---|---|---|---|---|
| `audit.audit_events` | `audit` | ARQ outbox relay worker ONLY | Super Admin | Never |
| `events.domain_events` (outbox) | shared | Application services (via UoW) | ARQ worker | Soft: status = PROCESSED |
| `approval.approval_requests` | `approval` | Approval service (state machine) | Actors in workflow | Never deleted |
| `approval.approval_step_records` | `approval` | Approval service (append-only) | Actors in workflow | Never |
| `notification.in_app_notifications` | `notification` | Notification trigger handlers | Recipient user only | Soft: `deleted_at` (purge after 90 days) |
| `notification.notification_queue` | `notification` | Notification trigger handlers | ARQ email worker | Soft: `deleted_at` after SENT (keep 30 days) |
| `reporting.report_runs` | `reporting` | Reporting service; ARQ worker | Requesting user; Super Admin | Never |

---

# 4. Final Permission-to-Feature Mapping

## 4.1 Role → Scope → Module Access

| Role | Default Scope | DB Scope Filter | Assignment Gate |
|---|---|---|---|
| Super Admin | GLOBAL | None | None |
| Program Coordinator | PROGRAM (per assignment) | `program_id IN (:assigned)` | None |
| Module Leader | PROGRAM (assignment) + OFFERING (data filter) | `program_id IN (:assigned)` | `faculty_assignments.role_in_course = 'MODULE_LEADER'` |
| Section Teacher | PROGRAM (assignment) + OFFERING (data filter) | `program_id IN (:assigned)` | `faculty_assignments.role_in_course = 'SECTION_TEACHER'` |
| Student | SELF | `student_id = :linked_student_id` | `student_enrollments.student_id = :self` |

## 4.2 Super Admin — Feature Map

| Feature | Permission | Module | API |
|---|---|---|---|
| Configure organization | `system.organization.configure` | org | `PATCH /organization` |
| Create departments | `department.create` | org | `POST /departments` |
| Create programs | `program.create` | org | `POST /programs` |
| Create users | `user.create` | iam | `POST /users` |
| Assign roles | `user.role.assign` | iam | `POST /users/{id}/roles` |
| Create roles | `system.roles.create` | iam | `POST /roles` |
| Grant permissions | `system.permissions.grant` | iam | `POST /roles/{id}/permissions` |
| Manage reference data | `config.*.manage` | ref_data | `POST/PATCH /ref-data/*` |
| View all audit logs | `system.audit.read` | audit | `GET /audit` |
| All coordinator features | (all coordinator permissions below) | all | all |

## 4.3 Program Coordinator — Feature Map

| Feature | Permission | Module | API |
|---|---|---|---|
| Create/version curriculum | `curriculum.create` `curriculum.version` | curriculum | `POST /curricula` `POST /curricula/{id}/version` |
| Manage courses | `course.create` `course.update` | curriculum | `POST/PATCH /courses` |
| Manage batches | `batch.create` | curriculum | `POST /batches` |
| Create section offerings | `section_offering.create` | curriculum | `POST /section-offerings` |
| Assign faculty | `faculty_assignment.create` | curriculum | `POST /faculty-assignments` |
| Create/manage POs | `po.create` `po.update` `po.archive` | obe | `POST/PATCH /program-outcomes` |
| Approve/publish COs | `co.approve` `co.publish` | obe | `POST /course-outcomes/{id}/approve` `/publish` |
| Manage CO-PO mapping | `mapping.co_po.create` `mapping.co_po.update` `mapping.co_po.publish` | obe | `POST/PATCH /mappings/co-po` |
| Approve CP/CA/KP mappings | `mapping.co_cp.approve` etc. | obe | `POST /mappings/co-cp/{id}/approve` |
| Configure assessments | `assessment.configure` `assessment.publish_config` | assessment | `POST /assessments` |
| View all marks | `marks.read.all` | assessment | `GET /marks?section_offering_id=` |
| Approve results (PC step) | `result.approve.pc` `result.publish` | assessment | `POST /results/{id}/approve-pc` `/publish` |
| Configure attainment | `attainment.configure` | attainment | `POST /attainment/config` |
| Initiate attainment | `attainment.initiate` | attainment | `POST /attainment/runs` |
| Publish attainment | `attainment.publish` | attainment | `POST /attainment/runs/{id}/publish` |
| Generate all reports | `report.*.generate` | reporting | `POST /reports/runs` |
| Manage accreditation | `accreditation.cycle.create` | accreditation | `POST /accreditation/cycles` |

## 4.4 Module Leader — Feature Map

| Feature | Permission | Scope Gate | Module | API |
|---|---|---|---|---|
| View curricula | `curriculum.read` | PROGRAM | curriculum | `GET /curricula` |
| View POs | `po.read` | PROGRAM | obe | `GET /program-outcomes` |
| View/edit COs (assigned courses) | `co.read` `co.update` | OFFERING (ML) | obe | `GET/PATCH /course-outcomes` |
| Approve/reject COs | `co.approve` `co.reject` | OFFERING (ML) | obe | `POST /course-outcomes/{id}/approve` |
| Approve CP/CA/KP mappings | `mapping.co_cp.approve` etc. | OFFERING (ML) | obe | `POST /mappings/co-cp/{id}/approve` |
| View CO-PO mapping | `mapping.co_po.read` | PROGRAM | obe | `GET /mappings/co-po` |
| View marks (assigned) | `marks.read.section` | OFFERING (ML) | assessment | `GET /marks` |
| Approve results (ML step) | `result.approve.ml` `result.reject.ml` | OFFERING (ML) | assessment | `POST /results/{id}/approve-ml` |
| View attainment | `attainment.read` | OFFERING (ML) | attainment | `GET /attainment/runs` |
| Generate CO/assessment reports | `report.co.generate` `report.assessment.generate` | OFFERING (ML) | reporting | `POST /reports/runs` |

## 4.5 Section Teacher — Feature Map

| Feature | Permission | Scope Gate | Module | API |
|---|---|---|---|---|
| View curricula/courses/POs | `curriculum.read` `po.read` | PROGRAM | curriculum, obe | `GET /curricula` `GET /program-outcomes` |
| Create COs (draft) | `co.create` | OFFERING (Teacher) | obe | `POST /course-outcomes` |
| Edit own draft COs | `co.update` | OFFERING (Teacher) + owned by self | obe | `PATCH /course-outcomes/{id}` |
| Submit COs | `co.submit` | OFFERING (Teacher) | obe | `POST /course-outcomes/{id}/submit` |
| Author CP/CA/KP mappings | `mapping.co_cp.manage` etc. | OFFERING (Teacher) | obe | `POST /mappings/co-cp` |
| View CO-PO mapping | `mapping.co_po.read` | PROGRAM | obe | `GET /mappings/co-po` |
| View assessment config | `assessment.read` | OFFERING (Teacher) | assessment | `GET /assessments` |
| Enter/update marks | `marks.enter` `marks.update` | OFFERING (Teacher) | assessment | `POST/PATCH /marks` |
| Submit results | `result.submit` | OFFERING (Teacher) | assessment | `POST /results/{id}/submit` |
| View own section results | `result.read.section` | OFFERING (Teacher) | assessment | `GET /results/{id}` |
| View attainment | `attainment.read` | OFFERING (Teacher) | attainment | `GET /attainment/runs` |

## 4.6 Student — Feature Map

| Feature | Permission | Scope | Module | API |
|---|---|---|---|---|
| View own profile | `student.profile.read.own` | SELF | iam/assessment | `GET /me` |
| View enrolled curriculum | `student.curriculum.read.own` | SELF | curriculum | `GET /my/curriculum` |
| View enrolled courses | `student.course.read.own` | SELF | curriculum | `GET /my/courses` |
| View POs for program | `student.po.read.own` | SELF | obe | `GET /my/program-outcomes` |
| View COs for enrolled courses | `student.co.read.own` | SELF | obe | `GET /my/course-outcomes` |
| View own marks (published) | `student.marks.read.own` | SELF | assessment | `GET /my/marks` |
| View own results | `student.result.read.own` | SELF | assessment | `GET /my/results` |

---

# 5. Final Workflow — End to End

## The Complete OBE Academic Cycle

This is the authoritative description of the full platform lifecycle from first setup to accreditation report. Every actor, action, state change, module, and event is accounted for.

---

### Phase 1: System Setup (Super Admin)

```
Actor: Super Admin

Step 1.1 — Configure Organization
  Action: PATCH /organization
  Module: org
  Result: org.organizations populated
  Event: OrganizationConfigured

Step 1.2 — Create Reference Data
  Action: POST /ref-data/bloom-domains, /bloom-levels,
          /delivery-methods, /course-types, /assessment-types,
          /complex-problems, /complex-activities, /knowledge-profiles
  Module: ref_data
  Result: config.* tables populated
  Event: ConfigDataCreated (per type)

Step 1.3 — Create Department
  Action: POST /departments
  Module: org
  Result: org.departments row; status = ACTIVE
  Event: DepartmentCreated

Step 1.4 — Create Program
  Action: POST /programs
  Module: org
  Result: org.programs row; linked to department; status = ACTIVE
  Event: ProgramCreated

Step 1.5 — Create Users (Faculty)
  Action: POST /users (with role = Program Coordinator, scope = CSE program)
  Module: iam
  Result: iam.users + iam.user_role_assignments
  Event: UserCreated → email notification with login instructions
```

---

### Phase 2: Curriculum Setup (Program Coordinator)

```
Actor: Program Coordinator (PROGRAM scope = CSE)

Step 2.1 — Create Curriculum
  Action: POST /curricula { program_id, name, code, effective_year }
  Module: curriculum
  Result: curriculum.curricula row; status = DRAFT
  Event: CurriculumCreated

Step 2.2 — Define Structural Terms
  Action: POST /curricula/{id}/terms [Semester 1 … Semester 8]
  Module: curriculum
  Result: curriculum.curriculum_term_definitions (8 rows)

Step 2.3 — Create Courses
  Action: POST /courses (for each course: CSE101, CSE102, ...)
  Module: curriculum
  Result: curriculum.courses rows; status = ACTIVE

Step 2.4 — Set Prerequisites
  Action: POST /courses/{id}/prerequisites
  Module: curriculum
  Domain Service: PrerequisiteGraphValidator.check_cycle() — rejects if cycle detected
  Result: curriculum.course_prerequisites edges

Step 2.5 — Place Courses in Curriculum
  Action: POST /curricula/{id}/course-slots { course_id, term_number }
  Module: curriculum
  Result: curriculum.curriculum_course_slots (one per course per term)

Step 2.6 — Activate Curriculum
  Action: PATCH /curricula/{id} { status: "ACTIVE" }
  Module: curriculum
  Result: curriculum.curricula.status = ACTIVE
  Event: CurriculumActivated

Step 2.7 — Create Batch
  Action: POST /batches { curriculum_id, name: "Batch 66", intake_year: 2024 }
  Module: curriculum
  Result: curriculum.batches row; linked to curriculum version
  Event: BatchCreated
```

---

### Phase 3: PO Configuration (Program Coordinator)

```
Actor: Program Coordinator

Step 3.1 — Create Program Outcomes
  Action: POST /program-outcomes (12 POs)
  Module: obe
  Fields: code (PO1–PO12), statement, bloom_domain_id, po_type, knowledge_profiles
  Result: obe.program_outcomes rows; status = ACTIVE

Step 3.2 — Link POs to Knowledge Profiles
  Action: POST /program-outcomes/{id}/knowledge-profiles
  Module: obe
  Result: obe.po_knowledge_profiles entries
```

---

### Phase 4: Academic Term Setup (Program Coordinator)

```
Actor: Program Coordinator

Step 4.1 — Create Operational Academic Term
  Action: POST /academic-terms { name: "Fall 2025", year: 2025, season: "FALL", dates }
  Module: curriculum
  Result: curriculum.academic_terms row; status = UPCOMING

Step 4.2 — Create Sections
  Action: POST /sections { name: "Section A", capacity: 40 }
  Module: curriculum
  Result: curriculum.sections row

Step 4.3 — Create Section Offerings
  Action: POST /section-offerings { curriculum_id, batch_id, course_id, academic_term_id, section_id }
  Module: curriculum
  Result: curriculum.section_offerings row; status = UPCOMING
          (One row per course × section × batch × term)

Step 4.4 — Assign Faculty
  Action: POST /faculty-assignments
          { section_offering_id, user_id, role_in_course: "MODULE_LEADER" }
          { section_offering_id, user_id, role_in_course: "SECTION_TEACHER" }
  Module: curriculum
  Result: curriculum.faculty_assignments rows
  Event: FacultyAssigned → Redis invalidates user:{id}:offering_ids + manifest

Step 4.5 — Enroll Students
  Action: POST /enrollments { student_id, section_offering_id }
  Module: assessment
  Result: assessment.student_enrollments rows
```

---

### Phase 5: CO Creation (Section Teacher)

```
Actor: Section Teacher (for their assigned section_offerings)
Gate: faculty_assignments.role_in_course = 'SECTION_TEACHER' for this offering

Step 5.1 — Create Course Outcomes (Draft)
  Action: POST /course-outcomes
          { curriculum_id, course_id, code: "CO1", statement, bloom_level_id }
  Module: obe
  Scope check: teaching this course in this curriculum version (via offering gate)
  Result: obe.course_outcomes row; status = DRAFT
  Event: CourseOutcomeDrafted

Step 5.2 — Add Delivery Methods
  Action: POST /course-outcomes/{id}/delivery-methods { delivery_method_id }
  Module: obe
  Result: obe.co_delivery_methods entries

Step 5.3 — Author CP/CA/KP Mappings
  Action: POST /mappings/co-cp { course_outcome_id, complex_problem_id }
          POST /mappings/co-ca { course_outcome_id, complex_activity_id }
          POST /mappings/co-kp { course_outcome_id, knowledge_profile_id }
  Module: obe
  Result: obe.co_cp/ca/kp_mappings rows; status = DRAFT

Step 5.4 — Submit CO for Approval
  Action: POST /course-outcomes/{id}/submit
  Module: obe
  Result: obe.course_outcomes.status = SUBMITTED
          approval.approval_requests row created (entity_type='COURSE_OUTCOME')
  Event: CourseOutcomeSubmitted
  Notification: IN_APP + EMAIL to all MODULE_LEADERs for this course
```

---

### Phase 6: CO Approval (Module Leader → Program Coordinator)

```
Actor: Module Leader (Gate: faculty_assignments.role_in_course = 'MODULE_LEADER')

Step 6.1 — Module Leader Reviews CO
  Action: PATCH /course-outcomes/{id} (comments only; no field edits in UNDER_REVIEW)
          POST /approval/requests/{id}/act { action: "APPROVED", comments: "..." }
  Module: obe + approval
  Result: obe.course_outcomes.status = APPROVED (ML level)
          approval.approval_step_records row (step 1 = APPROVED)
          approval_request.current_step_order advances to 2
  Event: CourseOutcomeApproved (ML)
  Notification: IN_APP to Program Coordinator

Actor: Program Coordinator

Step 6.2 — Program Coordinator Final Approval
  Action: POST /approval/requests/{id}/act { action: "APPROVED" }
  Module: approval + obe
  Result: approval_request.status = APPROVED
          obe.course_outcomes.status = APPROVED (final)
  Event: ApprovalChainCompleted(COURSE_OUTCOME)

Step 6.3 — Program Coordinator Configures CO-PO Mapping
  Action: POST /mappings/co-po { curriculum_id, course_id }
          PATCH /mappings/co-po/{id}/entries [{ co_id, po_id, weight: 1|2|3 }]
  Module: obe
  Result: obe.co_po_mapping_sets + obe.co_po_mapping_entries

Step 6.4 — Program Coordinator Approves CP/CA/KP Mappings
  Action: POST /mappings/co-cp/{id}/approve (etc.)
  Module: obe
  Result: obe.co_cp_mappings.status = APPROVED

Step 6.5 — Program Coordinator Publishes CO
  Action: POST /course-outcomes/{id}/publish
  Module: obe
  Result: obe.course_outcomes.status = PUBLISHED
          obe.co_delivery_methods → READ-ONLY
          obe.co_cp/ca/kp_mappings → READ-ONLY
  Event: CourseOutcomePublished

Step 6.6 — Program Coordinator Publishes CO-PO Mapping
  Action: POST /mappings/co-po/{id}/publish
  Module: obe
  Result: obe.co_po_mapping_sets.status = PUBLISHED
          obe.co_po_mapping_entries → READ-ONLY
  Event: COPOMappingPublished
```

---

### Phase 7: Assessment Configuration (Program Coordinator)

```
Actor: Program Coordinator

Step 7.1 — Configure Assessments
  Action: POST /assessments
          { section_offering_id, assessment_type_id, name: "Quiz 1",
            total_marks: 20, weightage_percent: 10 }
  Module: assessment
  Rule: Sum of all weightage_percent for this section_offering must = 100
        (enforced by WeightageValidator domain service on each addition)
  Result: assessment.assessments rows; status = CONFIGURED

Step 7.2 — Map Assessments to COs
  Action: POST /assessments/{id}/co-weights
          [{ course_outcome_id, contribution_percent: 50 },
           { course_outcome_id, contribution_percent: 50 }]
  Module: assessment
  Constraint: Only PUBLISHED COs can be referenced here
  Result: assessment.assessment_co_weights rows

Step 7.3 — Publish Assessment Configuration
  Action: PATCH /assessments/{id} { status: "MARKS_OPEN" }
  Module: assessment
  Result: assessment.assessments.status = MARKS_OPEN
          Section Teacher can now enter marks
  Event: AssessmentConfigPublished
```

---

### Phase 8: Marks Entry (Section Teacher)

```
Actor: Section Teacher (Gate: SECTION_TEACHER for this section_offering)

Step 8.1 — Enter Marks
  Action: POST /marks [{ assessment_id, student_enrollment_id, marks_obtained }]
  Module: assessment
  Constraint: marks_obtained <= assessment.total_marks
              is_absent XOR marks_obtained must be set
  Result: assessment.student_marks rows

Step 8.2 — Update Marks (if needed)
  Action: PATCH /marks/{id} { marks_obtained: <corrected> }
  Module: assessment
  Constraint: Only while result_publication.status = DRAFT
  Event: MarksUpdated
```

---

### Phase 9: Result Publication Workflow (Teacher → ML → PC)

```
Actor: Section Teacher

Step 9.1 — Submit Results
  Action: POST /results/{section_offering_id}/submit
  Module: assessment
  Result: assessment.result_publications.status = SUBMITTED
          assessment.result_publications.submitted_by/at populated
  Event: ResultSubmittedByTeacher
  Notification: IN_APP + EMAIL to Module Leader

Actor: Module Leader (Gate: MODULE_LEADER for this section_offering)

Step 9.2 — ML Reviews and Approves
  Action: POST /results/{section_offering_id}/approve-ml
  Module: assessment
  Result: result_publications.status = ML_APPROVED
          result_publications.ml_approved_by/at populated
  Event: ResultApprovedByML
  Notification: IN_APP to Program Coordinator

  (If ML rejects):
  Action: POST /results/{section_offering_id}/reject-ml { comment }
  Result: result_publications.status = DRAFT (teacher must resubmit)
  Notification: IN_APP + EMAIL to Section Teacher

Actor: Program Coordinator

Step 9.3 — PC Reviews and Approves
  Action: POST /results/{section_offering_id}/approve-pc
  Module: assessment
  Result: result_publications.status = PC_APPROVED
          result_publications.pc_approved_by/at populated

Step 9.4 — PC Publishes Results
  Action: POST /results/{section_offering_id}/publish
  Module: assessment
  Result: result_publications.status = PUBLISHED
          result_publications.published_at populated
          assessment.student_marks → READ-ONLY for this section_offering
  Event: ResultPublished
  Notification: IN_APP to all enrolled students
```

---

### Phase 10: Attainment Calculation (Program Coordinator + System)

```
Actor: Program Coordinator

Step 10.1 — Configure Thresholds
  Action: POST /attainment/config
          { section_offering_id, co_threshold_percent: 60,
            course_threshold_percent: 65, po_threshold_percent: 70,
            direct_method_weight: 100, indirect_method_weight: 0 }
  Module: attainment
  Result: attainment.attainment_configurations row
  Constraint: direct + indirect weights must = 100

Step 10.2 — Initiate Attainment Run
  Action: POST /attainment/runs { section_offering_id }
  Module: attainment
  Result: attainment.attainment_runs row; status = INITIATED
          ARQ job enqueued: calculate_attainment(run_id)
  Event: AttainmentRunInitiated
  API returns run_id immediately (async — do not wait)

Actor: ARQ Worker (System)

Step 10.3 — System Calculates Attainment
  Job: calculate_attainment(run_id)
  Domain Service: AttainmentCalculationEngine
    a. MappingMatrixSnapshotBuilder → co_po_mapping_snapshot JSONB (stored on run)
    b. Load all assessment_co_weights → assessment_weight_snapshot JSONB (stored on run)
    c. For each CO:
       - Sum (marks_obtained × co_contribution_percent) per student per assessment
       - Compute CO mark per student
       - Count students_attained (CO mark ≥ CO threshold)
       - co_attainment_percent = (students_attained / students_attempted) × 100
    d. course_attainment_percent = weighted average of CO attainments
    e. For each PO with at least one mapping entry:
       - po_attainment = Σ(co_attainment × mapping_weight) / Σ(mapping_weight)
    f. Write: co_attainment_results (one per CO), course_attainment_results (one),
              po_attainment_results (one per PO)
  Result: attainment_run.status = CALCULATED
  Event: AttainmentCalculated
  Notification: IN_APP to Program Coordinator

Step 10.4 — Coordinator Reviews
  Action: GET /attainment/runs/{id}
  Module: attainment
  Result: Coordinator reviews CO, Course, PO attainments vs thresholds
          is_threshold_met flags are visible

Step 10.5 — Coordinator Publishes Attainment
  Action: POST /attainment/runs/{id}/publish
  Module: attainment
  Result: attainment_run.status = PUBLISHED
  Event: AttainmentPublished
  → In-process handler: COLockHandler
      Sets obe.course_outcomes.status = LOCKED for all COs in this run
      Sets obe.course_outcomes.locked_at = NOW()
  → In-process handler: CacheInvalidationHandler
      Invalidates co_po_matrix cache for this curriculum/course
  Notification: IN_APP to all MLs in the program
```

---

### Phase 11: Report Generation (Program Coordinator)

```
Actor: Program Coordinator

Step 11.1 — Request Report
  Action: POST /reports/runs
          { report_definition_id, parameters: { program_id, term_id }, format: "PDF" }
  Module: reporting
  Result: reporting.report_runs row; status = QUEUED
          ARQ job enqueued: generate_report(run_id)
  Response: { run_id } (immediate; do not block)

Actor: ARQ Worker

Step 11.2 — System Generates Report
  Job: generate_report(run_id)
  QueryService: AccreditationEvidenceQueryService (or relevant service)
  Steps:
    a. Load parameters from report_runs
    b. Execute query service across obe, attainment, curriculum schemas
    c. Render to requested format (PDF via WeasyPrint, Excel via openpyxl, CSV)
    d. Upload to MinIO: reports/{org_id}/{year}/{month}/{run_id}.pdf
    e. Update report_runs: status = COMPLETED, file_key = <key>
  Event: ReportGenerated
  Notification: IN_APP to requesting user

Step 11.3 — Download Report
  Action: GET /reports/runs/{id}/download
  Module: reporting
  Auth: Requesting user or admin only
  Result: { download_url } (pre-signed MinIO URL, 15-minute TTL)
  User opens URL in browser → file downloads directly from MinIO
```

---

# 6. Final Consistency Checks

## 6.1 Contradictions Resolved

### C-01: `config` (DB schema) vs `ref_data` (Python module)

**Contradiction:** DB architecture names the schema `config`. Backend architecture names the Python module `ref_data` to avoid collision with Python's `config` naming convention.

**Resolution (FINAL):**
- PostgreSQL schema: `config` — unchanged. All table names: `config.bloom_levels`, etc.
- Python package: `app/modules/ref_data/` — unchanged.
- SQLAlchemy models in `ref_data` module declare `__table_args__ = {"schema": "config"}`.
- This dual naming is intentional, documented, and not a contradiction.

---

### C-02: `result_publications` table vs `approval` module

**Contradiction:** `assessment.result_publications` stores ML/PC approver IDs and timestamps directly. The `approval` module also manages approval workflows. This appeared redundant.

**Resolution (FINAL):**
- `approval.approval_requests` + `approval.approval_step_records`: track the **workflow process** (comments, timestamps, who acted, delegation).
- `assessment.result_publications`: tracks the **terminal state** (published_at, locked status).
- The `result_publications` table is the source of truth for whether results are published. The `approval` tables are the process audit trail.
- Result publication does NOT go through the generic approval module's workflow engine. It uses dedicated endpoints (`/results/{id}/approve-ml`, `/approve-pc`, `/publish`) that directly update `result_publications`. The approval module's generic workflow is used for CO approval and attainment publication only.
- **This eliminates the approval module from the result publication flow entirely. Result publication is self-contained in the assessment module.**

---

### C-03: `linked_student_id` missing from `iam.users`

**Contradiction:** RBAC architecture requires `iam.users.linked_student_id` to resolve the SELF scope for students. This column was not in the DB architecture document.

**Resolution (FINAL):** Add the following column to `iam.users`:

```
linked_student_id  UUID  NULLABLE  FK → assessment.students.id
UNIQUE (linked_student_id) WHERE linked_student_id IS NOT NULL
```

A student user account MUST have `linked_student_id` set before they can access any student-scoped data. The system enforces: if a user's role includes any `student.*` permission, `linked_student_id` must be non-null.

---

### C-04: Section Teacher creating COs — scope ambiguity

**Contradiction:** Section Teachers are assigned to `section_offerings`. COs belong to `curriculum_id + course_id`, not to a section_offering. How does the assignment gate work?

**Resolution (FINAL):**
The assignment gate for CO creation resolves as:

```
A Section Teacher can create/edit COs for course_id X in curriculum_id Y
IF:
  EXISTS faculty_assignments WHERE
    user_id = :teacher_id
    AND role_in_course = 'SECTION_TEACHER'
    AND section_offering_id IN (
      SELECT id FROM section_offerings
      WHERE course_id = X
        AND curriculum_id = Y
    )
```

The gate works because a section_offering links course_id, curriculum_id, batch_id, and teacher together. If a teacher is assigned to Offering A for CSE101 in curriculum CSE-2024, they can create COs for course CSE101 in curriculum CSE-2024.

---

### C-05: Who approves CO-PO mapping — ML or PC only?

**Contradiction:** The role matrix showed ML with mapping governance permissions, but the workflow only shows PC creating and publishing CO-PO mappings.

**Resolution (FINAL):**
- **CO-PO mapping**: Created AND published by Program Coordinator only. ML has read-only access. No ML approval step for CO-PO mapping.
- **CO-CP, CO-CA, CO-KP mappings**: Created by Section Teacher; reviewed and approved by Module Leader; no separate PC approval step (PC approval is implicit in CO publication).
- Remove `mapping.co_po.approve` from Module Leader's permission set. ML has only `mapping.co_po.read`.

---

### C-06: Assessment types vs. sessional types

**Contradiction:** FRD lists both "Assessment Types" (§4.9) and "Sessional Types" (§4.11) as separate configuration entities. DB architecture merged them.

**Resolution (FINAL):** Merged into `config.assessment_types` with `is_sessional BOOLEAN`:
- `is_sessional = TRUE`: Quiz, Assignment, Project, Presentation, Viva
- `is_sessional = FALSE`: Midterm, Final, Lab (terminal assessments)

One table. No separate sessional_types entity. This is final.

---

### C-07: Attainment trigger timing

**Contradiction:** The DDD analysis implies attainment can be manually initiated at any time. The workflow diagram implies it should trigger automatically after result publication.

**Resolution (FINAL):**
- Attainment is **always manually initiated** by the Program Coordinator via `POST /attainment/runs`.
- `ResultPublished` event does NOT auto-trigger attainment calculation. It only sends a notification/hint to the Coordinator that results are ready.
- Reason: The Coordinator must first verify all section_offering results are published before attainment is meaningful. Auto-triggering on the first published section would produce partial results.

---

## 6.2 Redundant Components Removed

| Component | Decision |
|---|---|
| Generic approval workflow for result publication | **Removed.** Result publication uses its own status columns on `result_publications`. The approval module handles CO approval and attainment publication only. |
| `mapping.co_po.approve` permission for Module Leader | **Removed.** ML has read-only on CO-PO mapping. Approval is by PC only. |
| `approval.workflow_step_definitions.required_role_id` FK to `iam.roles` | **Kept.** Used for CO and attainment approval workflows. |

## 6.3 Missing Components — Now Added

| Gap | Resolution |
|---|---|
| `iam.users.linked_student_id` | **Added.** Column + unique partial index. |
| Student enrollment in platform | **Assessment module** owns `assessment.students` and `assessment.student_enrollments`. Super Admin or Program Coordinator creates student records. |
| Attainment formula not specified in FRD | **Resolved.** Formula is Direct Method: CO attainment = % of students who scored ≥ threshold on the CO. PO attainment = weighted average of CO attainments using CO-PO weights. This is the default formula stored as `formula_type = 'DIRECT'`. Configurable in future via `formula_type` enum. |
| Corrective action when attainment below threshold | **Minimum viable:** `is_threshold_met = FALSE` flags are exposed in the attainment run results. Corrective action tracking is deferred to a future `improvement_plans` table. |
| Accreditation body-specific report formats | **Minimum viable:** Accreditation reports are generated as generic evidence bundles (CO-PO attainment + mapping matrix + faculty profile). Body-specific formatting is future work. |

## 6.4 Over-Engineered Parts — Simplified

| Area | Simplification |
|---|---|
| Generic approval workflow for all entity types | Scope reduced: generic approval module handles CO approval and attainment publication. Result publication is self-contained. This reduces workflow complexity by 40%. |
| ABAC extension | Deferred to v2. Current RBAC three-gate model is sufficient. |
| Permission delegation (`permission_delegations` table) | Deferred to v2. Delegate approvers (`approval.delegate_approvers`) covers the urgent use case. |
| WebSocket for real-time notifications | Deferred to v2. Polling (`GET /notifications/unread-count` every 60s) is sufficient for v1. |
| Report CQRS read replica | Deferred. Query services use read-only sessions on the same PostgreSQL instance. Pointing to a replica requires only a connection string change. |

---

# 7. Final Build Order

This is the implementation sequence. Each phase must be **fully tested and stable** before the next begins. Phases are not skippable.

---

## Phase 0 — Infrastructure Foundation *(~2 days)*

```
0.1  Initialize git repository and project structure
     app/ modules/ migrations/ tests/ docker/ scripts/

0.2  Write pyproject.toml (Poetry)
     Dependencies: fastapi, uvicorn, gunicorn, sqlalchemy[asyncio],
     asyncpg, alembic, pydantic-settings, redis[asyncio], aiobotocore,
     python-jose, passlib[bcrypt], arq, jinja2

0.3  Write docker-compose.yml
     Services: postgres, redis, minio
     Verify: all three services start and pass health checks

0.4  Configure Alembic (env.py)
     Async engine setup; all module models imported before autogenerate

0.5  Write core/config.py (Pydantic Settings)
     All environment variables declared with types and defaults

0.6  Write core/database.py
     Async engine + session factory + connection pool configuration

0.7  Write core/redis_client.py
     Async Redis pool initialization

0.8  Write shared/repository/base.py
     Generic BaseRepository[T]

0.9  Write shared/repository/unit_of_work.py
     UoW with outbox support

0.10 Write shared/events/base_event.py, bus.py, outbox.py
     In-process event bus + outbox writer

0.11 Write shared/schemas/pagination.py, response.py
     Standard response wrappers

0.12 Write app/main.py
     FastAPI app factory with lifespan, middleware chain, health endpoints
     Verify: GET /health/live → 200

GATE: All infrastructure services running. Unit of Work tested with a dummy model.
```

---

## Phase 1 — IAM Module (Auth & RBAC) *(~4 days)*

```
1.1  Write iam/models.py
     Tables: users, password_credentials, refresh_tokens, roles,
             permissions, role_permissions, user_role_assignments
     Add: linked_student_id column to users
     Alembic migration: alembic revision --autogenerate -m "iam_initial"
     Run migration. Verify schema created.

1.2  Write iam/repository/user_repository.py
     find_by_email, get_by_id, create, update, deactivate

1.3  Write iam/repository/role_repository.py
     find_by_name, create, add_permission, remove_permission

1.4  Write iam/repository/token_repository.py
     create_refresh_token, find_by_hash, revoke

1.5  Write iam/service/auth_service.py
     login(), refresh_token(), logout(), request_password_reset(), confirm_password_reset()

1.6  Write iam/service/user_service.py
     create_user(), update_user(), deactivate_user(), reset_password()

1.7  Write iam/service/permission_service.py (PermissionManifestBuilder)
     build_manifest(user_id) → PermissionManifest
     Includes Redis caching logic

1.8  Write core/security.py
     create_access_token(), decode_token(), hash_password(), verify_password()

1.9  Write core/dependencies.py
     get_current_user() FastAPI Depends
     require_permission() FastAPI Depends factory

1.10 Write iam/router/auth_router.py + user_router.py + role_router.py

1.11 Seed script: create_superadmin.py
     Creates system roles (Super Admin, Program Coordinator, Module Leader,
     Section Teacher, Student) with all permissions

1.12 Tests:
     unit: test auth_service login/refresh/logout flows
     unit: test PermissionManifestBuilder
     integration: test POST /auth/login → token → GET /me
     integration: test permission denied scenarios (403)

GATE: Login works. JWT validates. Permission manifest returns correct permissions.
      All 5 system roles seeded with correct permissions.
```

---

## Phase 2 — Organization + Reference Data *(~2 days)*

```
2.1  Write org/models.py
     Tables: organizations, departments, department_head_history, programs
     Alembic migration

2.2  Write org/repository + org/service + org/router
     Organization: get, update (no create — seeded)
     Departments: CRUD + archive
     Programs: CRUD + archive

2.3  Write ref_data/models.py
     Tables: bloom_domains, bloom_levels, delivery_methods, course_types,
             assessment_types, complex_problems, complex_activities,
             knowledge_profiles, mapping_weight_labels
     Alembic migration

2.4  Write ref_data/repository + ref_data/service + ref_data/router
     All with Redis caching (1-hour TTL)

2.5  Seed script: seed_reference_data.py
     Seeds default Bloom domains/levels (C1–C6), mapping weights (1=Low, 2=Medium, 3=High)

2.6  Tests:
     integration: CRUD on departments and programs with correct RBAC
     integration: Reference data endpoints return cached data on second call

GATE: Organization configured. Departments and programs exist.
      Reference data seeded and accessible.
```

---

## Phase 3 — Curriculum Module *(~4 days)*

```
3.1  Write curriculum/models.py
     Tables: curricula, curriculum_term_definitions, courses,
             curriculum_course_slots, course_prerequisites, batches,
             academic_terms, sections, section_offerings, faculty_assignments
     Alembic migration

3.2  Write curriculum/domain/entities.py
     PrerequisiteGraph cycle detection logic

3.3  Write curriculum/repository (one file per aggregate)
     curriculum_repository, course_repository, batch_repository,
     section_offering_repository, faculty_assignment_repository

3.4  Write curriculum/service.py
     create_curriculum(), version_curriculum(), activate_curriculum()
     create_course(), add_prerequisite() (calls PrerequisiteGraphValidator)
     create_section_offering(), assign_faculty()

3.5  Write curriculum/router.py

3.6  Tests:
     unit: cycle detection in prerequisites
     unit: curriculum versioning creates new row with parent_id
     integration: full curriculum setup flow (curriculum → terms → courses → slots → batch)
     integration: faculty assignment updates Redis offering cache
     integration: 403 if coordinator tries to access another program's curriculum

GATE: Full curriculum structure can be created. Faculty assignments work.
      Permission scoping verified (Coordinator A cannot see Coordinator B's curriculum).
```

---

## Phase 4 — OBE Module (PO + CO + Mappings) *(~5 days)*

```
4.1  Write obe/models.py
     Tables: program_outcomes, po_knowledge_profiles, course_outcomes,
             co_delivery_methods, co_po_mapping_sets, co_po_mapping_entries,
             co_cp_mappings, co_ca_mappings, co_kp_mappings
     Alembic migration

4.2  Write obe/domain/entities.py
     CourseOutcome state machine:
       DRAFT → SUBMITTED → UNDER_REVIEW → APPROVED → PUBLISHED → LOCKED
     Invariant: cannot edit when PUBLISHED or LOCKED
     Invariant: PO cannot be archived if referenced in active mapping entries

4.3  Write obe/domain/events.py
     All CO and mapping domain events

4.4  Write obe/repository
     po_repository, co_repository, mapping_repository

4.5  Write obe/service/po_service.py
     create_po(), update_po(), archive_po() (with BR-02 guard)

4.6  Write obe/service/co_service.py
     create_co(), update_co(), submit_co(), approve_co(), reject_co(), publish_co()
     lock_cos_by_run(run_id) — called by AttainmentPublished handler
     All operations check state machine validity

4.7  Write obe/service/mapping_service.py
     create_co_po_mapping_set(), update_entries(), publish_co_po_mapping()
     manage_co_cp_mapping(), approve_co_cp_mapping()
     (same pattern for CA, KP)

4.8  Write obe/router

4.9  Wire domain events to handlers:
     CourseOutcomeSubmitted → NotificationTriggerHandler (IN_APP to MLs)
     CourseOutcomePublished → CacheInvalidationHandler (co_po_matrix cache)
     CourseOutcomeRejected → NotificationTriggerHandler (IN_APP + EMAIL to teacher)

4.10 Tests:
     unit: CO state machine transitions (all valid + all invalid paths)
     unit: PO archival guard (BR-02)
     integration: Full CO lifecycle: create → submit → approve (ML) → publish (PC)
     integration: CO-PO mapping matrix persisted and published correctly
     integration: Section Teacher cannot approve own CO
     integration: Module Leader can only approve COs for assigned courses

GATE: CO lifecycle fully operational. Mapping matrices working.
      All business rules (BR-01 through BR-07) tested and passing.
```

---

## Phase 5 — Assessment Module *(~4 days)*

```
5.1  Write assessment/models.py
     Tables: students, student_enrollments, assessments,
             assessment_co_weights, student_marks, result_publications
     Alembic migration

5.2  Write assessment/domain/entities.py
     ResultPublication state machine:
       DRAFT → SUBMITTED → ML_APPROVED → PC_APPROVED → PUBLISHED → LOCKED
     StudentMark: immutable once result is PUBLISHED

5.3  Write assessment/domain events

5.4  Write assessment/service/assessment_service.py
     configure_assessment(), publish_assessment_config()
     WeightageValidator: validates sum = 100% before config publish

5.5  Write assessment/service/marks_service.py
     enter_marks(), update_marks()
     Guards: assessment must be MARKS_OPEN; result must be DRAFT

5.6  Write assessment/service/result_service.py
     submit_results(), approve_ml(), reject_ml(), approve_pc(), publish_results()
     publish_results() emits ResultPublished event
     On publish: StudentMark rows become immutable (guard enforced at service layer)

5.7  Write assessment/router

5.8  Wire events:
     ResultSubmittedByTeacher → NotificationTriggerHandler (IN_APP + EMAIL to ML)
     ResultApprovedByML → NotificationTriggerHandler (IN_APP to PC)
     ResultRejectedByML → NotificationTriggerHandler (IN_APP + EMAIL to Teacher)
     ResultPublished → NotificationTriggerHandler (IN_APP to enrolled students)
     ResultPublished → AuditEventHandler (via outbox)

5.9  Tests:
     unit: marks cannot be updated after result publication
     unit: result cannot be published without full ML → PC chain
     integration: full marks entry → submit → ML approve → PC approve → publish
     integration: marks read-only after publication
     integration: student can only see own published marks

GATE: Marks entry working. Full result approval chain operational.
      Students can view own published results.
```

---

## Phase 6 — Attainment Module *(~4 days)*

```
6.1  Write attainment/models.py
     Tables: attainment_configurations, attainment_runs,
             co_attainment_results, course_attainment_results,
             po_attainment_results
     Alembic migration
     Note: attainment_runs has co_po_mapping_snapshot (JSONB) +
           assessment_weight_snapshot (JSONB)

6.2  Write attainment/domain/entities.py
     AttainmentRun state machine: INITIATED → CALCULATED → REVIEWED → PUBLISHED

6.3  Write attainment/domain services:
     AttainmentCalculationEngine (pure Python — no DB calls)
       Input: snapshots + student marks dataset
       Output: COAttainmentResult[], CourseAttainmentResult, POAttainmentResult[]
     MappingMatrixSnapshotBuilder
       Reads live CO-PO mapping and freezes it as JSONB

6.4  Write attainment/service.py
     configure_thresholds(), initiate_run() → enqueues ARQ job
     review_run(), publish_run()
     publish_run() emits AttainmentPublished event

6.5  Write workers/tasks/attainment.py (ARQ task)
     calculate_attainment(run_id):
       Build snapshots → run AttainmentCalculationEngine → write results → CALCULATED

6.6  Wire events:
     AttainmentPublished → COLockHandler (locks all COs in run via obe service)
     AttainmentPublished → CacheInvalidationHandler
     AttainmentPublished → NotificationTriggerHandler (IN_APP to MLs)
     AttainmentPublished → AuditEventHandler (via outbox)

6.7  Write attainment/router + query services (trend endpoints)

6.8  Tests:
     unit: AttainmentCalculationEngine with known marks → verify exact percentages
     unit: JSONB snapshots immutably captured (live data changes don't affect run)
     integration: full attainment flow: configure → initiate → calculate → publish
     integration: COs are LOCKED after attainment published
     integration: cannot modify marks after attainment published (CO is LOCKED)

GATE: Attainment calculation produces correct results.
      CO locking verified end-to-end.
      Calculation is reproducible from snapshots alone.
```

---

## Phase 7 — Approval Module *(~2 days)*

```
7.1  Write approval/models.py
     Tables: workflow_definitions, workflow_step_definitions,
             approval_requests, approval_step_records, delegate_approvers
     Alembic migration

7.2  Seed: 2 workflow definitions
     - CO_APPROVAL (2 steps: ML review → PC final)
     - ATTAINMENT_PUBLICATION (1 step: PC review)

7.3  Write approval/service.py
     create_request(), act_on_step() (approve/reject/revision)
     ApprovalChainResolver: determines next approver
     On chain completion: emit ApprovalChainCompleted(entity_type, entity_id)
     CO service listens for ApprovalChainCompleted → transitions CO to APPROVED

7.4  Write approval/router

7.5  Tests:
     integration: CO approval uses the generic approval workflow
     integration: rejection returns CO to DRAFT and notifies teacher

GATE: CO approval workflow functional via approval module.
      Result publication (separate flow) unaffected.
```

---

## Phase 8 — Notification + Audit *(~2 days)*

```
8.1  Write notification/models.py
     Tables: notification_templates, notification_queue, in_app_notifications
     Alembic migration
     Seed: default templates for all 14 notification events

8.2  Write notification/service.py + router

8.3  Write workers/tasks/notifications.py (ARQ email worker)
     send_email_notification(notification_id) → SMTP/SES delivery with retry

8.4  Write audit/models.py
     Table: audit.audit_events (append-only)
     Configure: range partitioning by occurred_at (quarterly)
     Alembic migration

8.5  Write audit/router (read-only query interface)

8.6  Wire outbox relay (already partially done):
     workers/tasks/outbox_relay.py
     process_outbox_events() → AuditEventHandler + email queue

8.7  Tests:
     integration: CO submission creates in-app notification for ML
     integration: result publication creates in-app notification for students
     integration: audit events written for all major state transitions
     integration: audit events cannot be modified or deleted

GATE: All notification triggers firing correctly.
      Audit log capturing all significant events.
```

---

## Phase 9 — Reporting + Accreditation *(~3 days)*

```
9.1  Write reporting/models.py + accreditation/models.py
     Tables: report_definitions, report_runs, accreditation_bodies,
             accreditation_cycles, accreditation_reports
     Alembic migration
     Seed: default report definitions (all 10 categories)

9.2  Write query services (CQRS read side):
     AttainmentTrendQueryService (PO trend across runs)
     COPOMappingMatrixQueryService (display matrix)
     BatchProgressQueryService
     AccreditationEvidenceQueryService

9.3  Write workers/tasks/reports.py (ARQ report worker)
     generate_report(run_id) → query service → render → MinIO upload

9.4  Write core/minio_client.py + file_service.py
     Pre-signed upload/download URLs

9.5  Write reporting/router + accreditation/router

9.6  Tests:
     integration: request report → job queued → job completes → download URL returned
     integration: report contains accurate data matching attainment results
     integration: only requesting user (or admin) can download their report

GATE: All report types generate successfully.
      MinIO upload/download working with pre-signed URLs.
```

---

## Phase 10 — Frontend (Next.js) *(parallel with phases 7–9)*

```
10.1  Next.js project setup with App Router, TypeScript, Tailwind CSS

10.2  API client generation from FastAPI OpenAPI spec (openapi-typescript)

10.3  Authentication pages: Login, Forgot Password, Reset Password

10.4  Permission manifest fetched on login; stored in Zustand/Context

10.5  Navigation: role-aware menu (checks manifest.permissions)

10.6  Modules — build in this order (mirrors backend build order):
      a. Organization + Reference Data (admin screens)
      b. User Management (admin screens)
      c. Curriculum Management (coordinator screens)
      d. PO Management (coordinator screens)
      e. CO Management (teacher create, ML approve, PC publish)
      f. CO-PO Mapping Matrix (coordinator screen — grid UI)
      g. Assessment Configuration (coordinator screen)
      h. Marks Entry (teacher screen — tabular data entry)
      i. Result Approval (ML + PC approval screens)
      j. Attainment Dashboard (coordinator screen)
      k. Reports (request + download)
      l. Student Portal (self-service: results, curriculum view)
      m. Audit Log Viewer (super admin screen)

10.7  Tests:
      E2E (Playwright): Full CO lifecycle from teacher create to PC publish
      E2E: Marks entry → result publication → student views result
      E2E: Permission manifest prevents unauthorized UI elements rendering
```

---

## Phase 11 — Hardening *(~3 days)*

```
11.1  Complete integration test suite
      Target: 80%+ coverage on all service layer code

11.2  Load testing (Locust or k6)
      Target: 100 concurrent users, API response P99 < 500ms

11.3  Security review
      OWASP Top 10 checklist
      SQL injection: verify all queries parameterized
      Auth bypass: verify all endpoints have authorization annotations
      Mass assignment: verify Pydantic schemas only expose intended fields

11.4  Structured logging validation
      Verify correlation_id propagates through all log entries
      Verify no PII in log output (no passwords, no token values)

11.5  Monitoring setup
      Prometheus + Grafana dashboards
      Alerts: error rate > 5%, DB pool > 90%, ARQ failure > 10%

11.6  Migration dry-run on production-equivalent data volume

11.7  Deployment runbook
      Checklist: env vars set, migrations run, seeds applied,
                 health checks passing, super admin created
```

---

## Build Order Summary

| Phase | What | Duration |
|---|---|---|
| 0 | Infrastructure Foundation | 2 days |
| 1 | IAM / Auth / RBAC | 4 days |
| 2 | Organization + Reference Data | 2 days |
| 3 | Curriculum Module | 4 days |
| 4 | OBE (PO + CO + Mappings) | 5 days |
| 5 | Assessment (Marks + Results) | 4 days |
| 6 | Attainment Engine | 4 days |
| 7 | Approval Module | 2 days |
| 8 | Notification + Audit | 2 days |
| 9 | Reporting + Accreditation | 3 days |
| 10 | Frontend (Next.js) | 15 days (parallel from Phase 7) |
| 11 | Hardening | 3 days |
| **Total backend** | | **~35 days** |
| **Total with frontend** | | **~45 days** |

**Critical path:** Phase 0 → 1 → 2 → 3 → 4 → 5 → 6. No phase can begin until the previous gates are met. Frontend can begin in parallel from Phase 7 onward, with mock API data for phases not yet complete.

---

*End of System Blueprint — OBE Accreditation Management Platform v1.0*  
*This document is the authoritative architecture reference. All implementation decisions must align with it.*
