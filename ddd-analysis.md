# OBE Accreditation Management Platform
## Domain-Driven Design (DDD) Analysis
### Architecture Document v1.0

> **Prepared for:** OBE Accreditation Management Platform  
> **Based on:** Functional Requirements Document v1.0  
> **Perspective:** Principal Software Architect — Enterprise Academic Systems  
> **Date:** 2026-06-04  

---

## Table of Contents

1. [Domain Analysis](#1-domain-analysis)
2. [Bounded Contexts](#2-bounded-contexts)
3. [Aggregate Roots](#3-aggregate-roots)
4. [Entities](#4-entities)
5. [Value Objects](#5-value-objects)
6. [Domain Events](#6-domain-events)
7. [Business Rules](#7-business-rules)
8. [State Machines](#8-state-machines)
9. [Approval Workflows](#9-approval-workflows)
10. [Entity Lifecycles](#10-entity-lifecycles)
11. [Risks and Architectural Challenges](#11-risks-and-architectural-challenges)
12. [Missing Requirements in the FRD](#12-missing-requirements-in-the-frd)
13. [Future-Proofing Recommendations](#13-future-proofing-recommendations)
14. [Recommended Modular Architecture](#14-recommended-modular-architecture)

---

# 1. Domain Analysis

The domain is partitioned into three layers following the DDD subdomain classification: **Core**, **Supporting**, and **Generic**. The classification drives investment decisions — Core domains justify custom, deep implementation; Supporting domains can be partially templated; Generic domains may be off-the-shelf or thin wrappers.

---

## 1.1 Core Domains

These domains represent the primary competitive differentiator of this platform. They encode unique, complex business logic that no off-the-shelf tool handles correctly for OBE accreditation.

| Domain | Why It Is Core |
|---|---|
| **OBE Mapping Domain** | CO-PO, CO-CP, CO-CA, CO-KP mapping logic with weighted correlation matrices is the intellectual heart of the platform. No generic tool handles this correctly. |
| **Attainment Calculation Domain** | Multi-dimensional calculation of CO attainment → Course attainment → PO attainment with configurable thresholds, weightages, and assessment contributions is deeply specialized. |
| **Accreditation Compliance Domain** | Accreditation bodies (e.g., ABET, NBA, NAAC) have specific audit trails, report structures, and evidence requirements. This logic must be owned internally. |
| **Curriculum Management Domain** | Managing multi-version curricula, course-to-term placement, credit structures, prerequisite graphs, and their relationship to batches over time is complex and central to everything else. |

---

## 1.2 Supporting Domains

These domains are necessary for the platform to function but do not themselves constitute competitive advantage. They support and enable the core domains.

| Domain | Role |
|---|---|
| **Assessment Domain** | Manages assessment design, CO mapping, marks entry, and result publication. Feeds attainment calculations. |
| **Academic Structure Domain** | Terms, sections, faculty-to-course assignments. Provides the operational scaffolding for each semester. |
| **Approval Workflow Domain** | Manages multi-level approval chains that gate state transitions across CO, assessments, and results. |
| **Reporting Domain** | Aggregates data from all core domains and renders structured reports in multiple formats (PDF, Excel, CSV). |
| **Notification Domain** | Drives communication for approval requests, publication events, and workflow transitions. |

---

## 1.3 Generic Domains

These domains are standard, well-understood, and do not require custom intellectual investment. They should use proven patterns or libraries.

| Domain | Notes |
|---|---|
| **Identity & Access Management (IAM)** | RBAC with dynamic roles and permissions. Standard pattern; leverage proven JWT + refresh token strategies. |
| **Audit Logging** | Append-only change tracking. Standard pattern with well-known implementations. |
| **Organization Management** | Organization, department, program metadata. Mostly CRUD with little behavioral complexity. |

---

# 2. Bounded Contexts

Each Bounded Context owns its own domain language, model, and persistence. Cross-context communication happens through well-defined interfaces (domain events, ACLs, or shared kernel for reference data).

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         OBELYTICS PLATFORM                                   │
│                                                                              │
│  ┌─────────────────┐   ┌──────────────────┐   ┌──────────────────────────┐  │
│  │   IAM Context   │   │   Org Context    │   │   Curriculum Context     │  │
│  │  (Generic)      │   │   (Generic)      │   │   (Core)                 │  │
│  │                 │   │                  │   │                          │  │
│  │ User            │   │ Organization     │   │ Curriculum               │  │
│  │ Role            │   │ Department       │   │ AcademicTerm             │  │
│  │ Permission      │   │ Program          │   │ Course                   │  │
│  └────────┬────────┘   └────────┬─────────┘   │ Batch                    │  │
│           │                    │              │ CoursePrerequisite        │  │
│           │  ◄─────────────────┤              └──────────────┬───────────┘  │
│           │                    │                             │              │
│  ┌────────▼────────────────────▼─────────────────────────────▼───────────┐  │
│  │                        OBE Context (Core)                              │  │
│  │  ProgramOutcome   CourseOutcome   CO-PO Map   CO-CP Map   CO-CA/KP Map│  │
│  └────────────────────────────────────┬───────────────────────────────────┘  │
│                                       │                                      │
│  ┌────────────────────────────────────▼───────────────────────────────────┐  │
│  │                    Assessment Context (Supporting)                      │  │
│  │  Assessment   AssessmentCOMapping   StudentMark   ResultPublication     │  │
│  └────────────────────────────────────┬───────────────────────────────────┘  │
│                                       │                                      │
│  ┌────────────────────────────────────▼───────────────────────────────────┐  │
│  │                    Attainment Context (Core)                            │  │
│  │  AttainmentConfig   COAttainment   CourseAttainment   POAttainment      │  │
│  └────────────────────────────────────┬───────────────────────────────────┘  │
│                                       │                                      │
│  ┌──────────────────┐  ┌──────────────▼──────────┐  ┌─────────────────┐    │
│  │  Approval Context│  │  Accreditation Context  │  │  Reporting Ctx  │    │
│  │  (Supporting)    │  │  (Core)                 │  │  (Supporting)   │    │
│  └──────────────────┘  └─────────────────────────┘  └─────────────────┘    │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────────────────────────────────────┐ │
│  │ Notification Ctx │  │                   Audit Context                  │ │
│  │ (Supporting)     │  │                   (Generic)                      │ │
│  └──────────────────┘  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Context Map — Integration Patterns

| Upstream Context | Downstream Context | Integration Pattern |
|---|---|---|
| IAM | All Contexts | Shared Kernel (UserIdentity, RoleRef) |
| Org | Curriculum | Customer/Supplier — Program is a foreign key reference |
| Curriculum | OBE | Customer/Supplier — Course is the anchor for COs |
| OBE | Assessment | Published Language — CO identifiers consumed |
| OBE | Attainment | Customer/Supplier — CO-PO mappings drive PO attainment |
| Assessment | Attainment | Customer/Supplier — Marks and weightages feed calculations |
| Attainment | Accreditation | Customer/Supplier — Published attainment data forms evidence |
| Attainment | Reporting | Open Host Service — Query API for report generation |
| All Contexts | Audit | Event-Driven — AuditLog consumes domain events |
| All Contexts | Notification | Event-Driven — Notification listens for workflow events |
| All Contexts | Approval | Conformist — Contexts conform to Approval workflow protocol |

---

# 3. Aggregate Roots

Aggregate Roots are the consistency boundaries. All mutations within an aggregate go through its root. External references use only the root's identity.

| Bounded Context | Aggregate Root | Consistency Responsibility |
|---|---|---|
| **IAM** | `User` | User identity, role assignments, permissions |
| **IAM** | `Role` | Permission set membership |
| **Org** | `Organization` | Single-instance org metadata |
| **Org** | `Department` | Department metadata, archival |
| **Org** | `Program` | Program metadata, type, mode |
| **Curriculum** | `Curriculum` | Version lifecycle, term-course structure |
| **Curriculum** | `Course` | Course definition, prerequisites |
| **Curriculum** | `Batch` | Batch-curriculum binding, intake/graduation tracking |
| **OBE** | `ProgramOutcome` | PO definition, attributes, archival guard |
| **OBE** | `CourseOutcome` | CO definition, delivery methods, state lifecycle |
| **OBE** | `COPOMapping` | Mapping matrix for a given course-curriculum version |
| **Assessment** | `Assessment` | Assessment config, CO mapping, marks collection |
| **Assessment** | `SectionOffering` | A course offered in a section/term, owns its assessments |
| **Attainment** | `AttainmentRun` | A complete attainment calculation for a course offering in a term |
| **Approval** | `ApprovalRequest` | Approval chain state and history |

---

# 4. Entities

Entities have identity and lifecycle within their aggregate. They are referenced by ID but mutated only through their aggregate root.

## IAM Context

| Entity | Parent Aggregate | Description |
|---|---|---|
| `UserRoleAssignment` | `User` | Binding of a user to a role, scoped to a program or department |
| `PasswordCredential` | `User` | Hashed credential, reset token, expiry |

## Org Context

| Entity | Parent Aggregate | Description |
|---|---|---|
| `DepartmentHead` | `Department` | Points to a User reference; tracks HOD history |

## Curriculum Context

| Entity | Parent Aggregate | Description |
|---|---|---|
| `CurriculumTerm` | `Curriculum` | A semester slot within a curriculum version |
| `CurriculumCourseSlot` | `Curriculum` | A course placed in a curriculum term with credit allocation |
| `CoursePrerequisite` | `Course` | Directed prerequisite edge (parent → required course) |

## OBE Context

| Entity | Parent Aggregate | Description |
|---|---|---|
| `CODeliveryMethod` | `CourseOutcome` | Association between a CO and a delivery method |
| `COPOMappingEntry` | `COPOMapping` | A single CO↔PO cell value (1/2/3) in the mapping matrix |
| `COCPMappingEntry` | `CourseOutcome` | CO to Complex Problem link |
| `COCAMappingEntry` | `CourseOutcome` | CO to Complex Activity link |
| `COKPMappingEntry` | `CourseOutcome` | CO to Knowledge Profile link |

## Assessment Context

| Entity | Parent Aggregate | Description |
|---|---|---|
| `AssessmentCOWeight` | `Assessment` | Maps an assessment to a CO with a contribution weight |
| `StudentMark` | `Assessment` | A student's mark for an assessment |
| `ResultPublication` | `SectionOffering` | Tracks publication state and approver chain for a section's results |

## Attainment Context

| Entity | Parent Aggregate | Description |
|---|---|---|
| `COAttainmentResult` | `AttainmentRun` | Computed attainment value for each CO in the run |
| `CourseAttainmentResult` | `AttainmentRun` | Aggregated course-level attainment |
| `POAttainmentResult` | `AttainmentRun` | PO-level attainment derived from CO-PO mapping weights |
| `AttainmentThreshold` | `AttainmentRun` | Threshold configuration captured at time of calculation |

---

# 5. Value Objects

Value Objects are immutable, identity-less, and defined entirely by their attributes.

## Identifiers & Codes

| Value Object | Structure | Validation Rule |
|---|---|---|
| `Email` | String | Must match configurable regex; unique per user |
| `CourseCode` | String | Alphanumeric, department prefix, sequence number |
| `POCode` | String | e.g., `PO1` to `PO12` |
| `COCode` | String | e.g., `CO1`, `CO2` within a course |
| `PermissionCode` | String | Dot-separated: `domain.action` (e.g., `user.create`) |

## Enumerations (Sealed Value Objects)

| Value Object | Allowed Values |
|---|---|
| `ProgramType` | Undergraduate, Postgraduate, PhD |
| `StudyMode` | FullTime, PartTime |
| `MappingWeight` | 1 (Low), 2 (Medium), 3 (High) |
| `BloomDomain` | Cognitive, Affective, Psychomotor |
| `BloomLevel` | C1-Remember, C2-Understand, C3-Apply, C4-Analyze, C5-Evaluate, C6-Create |
| `FacultyType` | Permanent, Adjunct, Visiting, Contractual |
| `WorkflowState` | Draft, Submitted, UnderReview, Approved, Rejected, Published, Locked |
| `ApprovalAction` | Approve, Reject, RequestRevision |

## Quantities & Measures

| Value Object | Description |
|---|---|
| `CreditHours` | Positive integer; theory and lab hours tracked separately |
| `Weightage` | Decimal percentage; must be positive, ≤ 100 |
| `AttainmentPercentage` | Decimal 0–100; computed, not manually entered |
| `AttainmentThreshold` | Decimal 0–100; configured by coordinator |
| `AcademicYear` | Integer year (e.g., 2026) |
| `IntakeYear` | Integer year for batch intake |

## Complex Value Objects

| Value Object | Description |
|---|---|
| `MappingMatrix` | 2D structure: CO × PO with MappingWeight cells; immutable snapshot |
| `AttainmentFormula` | Captures the formula type (direct/indirect) and weightage split used in a run |
| `AddressInfo` | Street, city, country, postal code for organization |
| `ContactInfo` | Email, phone number, validated as a unit |
| `ApproverSignature` | UserId + timestamp + action; immutable once recorded |

---

# 6. Domain Events

Domain Events represent facts that have happened in the domain. They are the primary mechanism for loose coupling between bounded contexts.

## IAM Events

| Event | Trigger | Consumers |
|---|---|---|
| `UserCreated` | Admin creates a new user | Notification, Audit |
| `UserDeactivated` | Admin deactivates a user | Audit, reassign open workflows |
| `RoleAssigned` | Role bound to a user | Audit |
| `RoleRevoked` | Role removed from a user | Audit |
| `PasswordReset` | Password changed or auto-generated | Notification, Audit |
| `PermissionSetChanged` | Permissions added/removed from role | Audit |

## Org Events

| Event | Trigger | Consumers |
|---|---|---|
| `OrganizationConfigured` | Initial setup or major update | Audit |
| `DepartmentCreated` | New department added | Audit |
| `DepartmentArchived` | Department deactivated | Audit, guard curriculum links |
| `ProgramCreated` | New academic program defined | Audit |
| `ProgramArchived` | Program deactivated | Audit, guard curriculum links |

## Curriculum Events

| Event | Trigger | Consumers |
|---|---|---|
| `CurriculumCreated` | New curriculum version started | Audit |
| `CurriculumActivated` | Curriculum moved to active status | Batch assignment |
| `CurriculumVersioned` | A new version derived from existing | Audit, OBE migration check |
| `CurriculumArchived` | Old version retired | Audit |
| `CourseCreated` | New course defined | Audit |
| `CourseArchived` | Course deactivated | Audit, guard active curricula |
| `BatchCreated` | New student batch registered | Audit |
| `BatchCurriculumAssigned` | Batch linked to a curriculum version | Audit |

## OBE Events

| Event | Trigger | Consumers |
|---|---|---|
| `ProgramOutcomeCreated` | PO defined | Audit |
| `ProgramOutcomeUpdated` | PO statement changed | Audit, CO-PO mapping invalidation check |
| `ProgramOutcomeArchived` | PO retired | Audit, guard mapping links |
| `CourseOutcomeDrafted` | CO created in Draft | Audit |
| `CourseOutcomeSubmitted` | Teacher submits CO for review | Approval, Notification |
| `CourseOutcomeApproved` | Module Leader / Coordinator approves | Notification, Audit |
| `CourseOutcomeRejected` | Approver rejects CO | Notification, Audit |
| `CourseOutcomePublished` | CO published | Audit, Assessment context |
| `CourseOutcomeLocked` | CO locked after attainment publication | Audit |
| `COPOMappingCreated` | Mapping matrix created | Audit |
| `COPOMappingApproved` | Mapping approved | Audit, Attainment context |
| `COPOMappingPublished` | Mapping published | Audit, Accreditation context |
| `COCPMappingApproved` | CP mapping approved | Audit |
| `COCAMappingApproved` | CA mapping approved | Audit |
| `COKPMappingApproved` | KP mapping approved | Audit |

## Assessment Events

| Event | Trigger | Consumers |
|---|---|---|
| `AssessmentCreated` | Assessment configured | Audit |
| `AssessmentCOWeightSet` | CO mapping assigned to assessment | Audit |
| `MarksEntered` | Teacher enters marks | Audit |
| `MarksUpdated` | Teacher updates marks before publication | Audit |
| `ResultSubmittedByTeacher` | Teacher submits for approval | Approval, Notification |
| `ResultApprovedByModuleLeader` | Module Leader approves | Notification, Audit |
| `ResultRejectedByModuleLeader` | Module Leader rejects | Notification, Audit |
| `ResultApprovedByCoordinator` | Coordinator gives final approval | Notification, Audit |
| `ResultPublished` | Results published to students | Notification, Audit, Attainment trigger |
| `MarksLocked` | Marks frozen after publication | Audit |

## Attainment Events

| Event | Trigger | Consumers |
|---|---|---|
| `AttainmentRunInitiated` | Attainment calculation started | Audit |
| `COAttainmentCalculated` | Per-CO attainment computed | Audit |
| `CourseAttainmentCalculated` | Course-level attainment computed | Audit |
| `POAttainmentCalculated` | PO-level attainment computed | Audit, Accreditation |
| `AttainmentPublished` | Full run published | Notification, Audit, CO lock trigger |
| `AttainmentThresholdConfigured` | Coordinator sets threshold | Audit |

## Approval / Workflow Events

| Event | Trigger | Consumers |
|---|---|---|
| `ApprovalRequestCreated` | Workflow step initiated | Notification |
| `ApprovalRequestApproved` | Step approved | Downstream step or published event |
| `ApprovalRequestRejected` | Step rejected | Notification, upstream entity state reset |
| `ApprovalChainCompleted` | All steps in chain approved | Published domain event |

---

# 7. Business Rules

Business rules are invariants the domain must enforce at all times. They are distinct from validation — they encode domain policy.

## Invariant Rules (must never be violated)

| Rule ID | Rule | Enforcement Point |
|---|---|---|
| BR-01 | A CourseOutcome MUST NOT be modified after the related AttainmentRun is published. | `CourseOutcome` aggregate |
| BR-02 | A ProgramOutcome MUST NOT be archived or deleted if it has active CO-PO mapping entries linked to a non-archived curriculum. | `ProgramOutcome` aggregate |
| BR-03 | Only ONE Organization may exist in a single deployment (single-tenant model). | `Organization` aggregate |
| BR-04 | Curriculum versions MUST coexist; a prior version MUST NOT be deleted once a Batch has been assigned to it. | `Curriculum` aggregate |
| BR-05 | Marks MUST NOT be modified after result publication for the SectionOffering. | `Assessment` aggregate |
| BR-06 | Course prerequisite graph MUST NOT contain cycles. | `Course` aggregate, domain service |
| BR-07 | CO-PO mapping weight values MUST be 1, 2, or 3 only. A null/empty cell means no mapping. | `COPOMappingEntry` value object |
| BR-08 | Assessment weightages within a SectionOffering MUST sum to 100%. | `SectionOffering` aggregate |
| BR-09 | A result MUST NOT be published without the full approval chain being completed in order (Teacher → Module Leader → Coordinator). | `ApprovalRequest` aggregate |
| BR-10 | Attainment MUST NOT be calculated unless at least one threshold is configured. | `AttainmentRun` aggregate |
| BR-11 | An archived entity (Department, Program, Course, PO) MUST NOT be selectable for new curriculum or mapping creation. | Application service layer |
| BR-12 | A User MUST NOT be assigned a role that has no permissions. | `Role` aggregate |
| BR-13 | Email format MUST match the organization-configured regex pattern before a user is created. | `User` aggregate |
| BR-14 | CO Delivery Methods MUST reference only active DeliveryMethod reference data entries. | `CourseOutcome` aggregate |
| BR-15 | An `AttainmentRun` MUST reference a snapshot of the CO-PO mapping matrix at the time of calculation, not the live mapping. | `AttainmentRun` aggregate |

## Conditional Rules (enforced under specific conditions)

| Rule ID | Rule | Condition |
|---|---|---|
| BR-16 | When a CO moves to `Published`, all its mapping entries (CO-PO, CO-CP, CO-CA, CO-KP) transition to read-only. | CO published event |
| BR-17 | When a curriculum is versioned, new COs for the new version are created in `Draft`; existing approved COs may be copied as new drafts. | Curriculum versioning |
| BR-18 | A Module Leader may only approve materials for courses they are explicitly assigned to. | Permission + assignment check |
| BR-19 | When a result is rejected at any approval level, it reverts to Draft and notifies the teacher. | Approval rejection |
| BR-20 | When attainment is below threshold, the system MUST flag the CO/PO for corrective action. | Post-calculation analysis |

---

# 8. State Machines

## 8.1 CourseOutcome State Machine

```
                    ┌─────────┐
         create()   │  DRAFT  │
         ──────────►│         │◄─────────────────────────────────┐
                    └────┬────┘                                   │
                         │ submit()                               │
                         ▼                                        │
                   ┌──────────────┐                              │
                   │  SUBMITTED   │                              │
                   └──────┬───────┘                              │
                           │ reviewStart()                        │
                           ▼                                      │
                   ┌──────────────┐  reject()                    │
                   │ UNDER_REVIEW │ ─────────────────────────────┘
                   └──────┬───────┘
                           │ approve()
                           ▼
                    ┌──────────┐
                    │ APPROVED │
                    └─────┬────┘
                          │ publish()
                          ▼
                   ┌────────────┐
                   │ PUBLISHED  │ ◄── COs are read-only at this point
                   └─────┬──────┘     Mappings become read-only
                          │ lock()   [triggered by AttainmentPublished event]
                          ▼
                    ┌────────┐
                    │ LOCKED │  ── Terminal State: No further changes permitted
                    └────────┘
```

**Allowed Transitions:**

| From | To | Action | Actor |
|---|---|---|---|
| DRAFT | SUBMITTED | submit() | Section Teacher |
| SUBMITTED | UNDER_REVIEW | reviewStart() | Module Leader |
| UNDER_REVIEW | APPROVED | approve() | Module Leader / Coordinator |
| UNDER_REVIEW | DRAFT | reject() | Module Leader / Coordinator |
| APPROVED | PUBLISHED | publish() | Program Coordinator |
| PUBLISHED | LOCKED | lock() | System (event-driven) |

---

## 8.2 Assessment Result State Machine

```
               ┌─────────┐
    create()   │  DRAFT  │◄──────────────────────────────────┐
    ──────────►│         │                                    │
               └────┬────┘                                    │
                    │ submit() [Teacher]                       │
                    ▼                                          │
           ┌────────────────┐                                 │
           │ PENDING_ML     │ (Pending Module Leader Approval) │
           │ APPROVAL       │                                 │
           └───────┬────────┘                                 │
                   │ approve() [Module Leader]                 │
                   ▼                                           │
           ┌────────────────┐  reject() [Module Leader]       │
           │ PENDING_PC     │ ────────────────────────────────┘
           │ APPROVAL       │ (Pending Program Coordinator)
           └───────┬────────┘
                   │ approve() [Program Coordinator]
                   ▼
           ┌───────────────┐
           │   PUBLISHED   │  ── StudentMark entities become read-only
           └───────┬───────┘  ── Triggers AttainmentRun initiation
                   │ lock() [System]
                   ▼
            ┌────────────┐
            │   LOCKED   │  ── Terminal State
            └────────────┘
```

---

## 8.3 Curriculum State Machine

```
               ┌─────────┐
    create()   │  DRAFT  │
    ──────────►│         │
               └────┬────┘
                    │ activate()
                    ▼
               ┌──────────┐
               │  ACTIVE  │ ◄── Multiple versions can be ACTIVE simultaneously
               └────┬─────┘
                    │
          ┌─────────┴────────┐
          │                  │
          ▼ version()        ▼ archive()
    ┌──────────────┐    ┌──────────────┐
    │   VERSIONED  │    │   ARCHIVED   │  ── Terminal State (referenced data preserved)
    │  (spawns new │    └──────────────┘
    │    DRAFT)    │
    └──────────────┘
```

**Rule:** A curriculum version cannot be ARCHIVED while any ACTIVE batch references it.

---

## 8.4 Approval Request State Machine

```
                    ┌─────────┐
         create()   │ PENDING │
         ──────────►│         │
                    └────┬────┘
                         │ assign to approver
                         ▼
                  ┌──────────────┐
                  │ UNDER_REVIEW │
                  └──────┬───────┘
               ┌─────────┴──────────┐
               │                    │
         approve()              reject()
               │                    │
               ▼                    ▼
         ┌──────────┐         ┌──────────┐
         │ APPROVED │         │ REJECTED │
         └──────────┘         └──────────┘
```

---

## 8.5 ProgramOutcome State Machine

```
              ┌────────┐
   create()   │ ACTIVE │
   ──────────►│        │
              └────┬───┘
                   │ archive()  [blocked if linked to active curriculum]
                   ▼
              ┌──────────┐
              │ ARCHIVED │  ── Read-only; existing references valid; not selectable for new work
              └──────────┘
```

---

## 8.6 Attainment Run State Machine

```
              ┌────────────┐
   initiate() │  INITIATED │
   ──────────►│            │
              └─────┬──────┘
                    │ calculate() [automated]
                    ▼
              ┌────────────┐
              │ CALCULATED │
              └─────┬──────┘
                    │ review() [Coordinator]
                    ▼
              ┌────────────┐
              │  REVIEWED  │
              └─────┬──────┘
                    │ publish()
                    ▼
              ┌────────────┐
              │ PUBLISHED  │ ── Triggers CourseOutcome LOCKED event
              └────────────┘
```

---

# 9. Approval Workflows

## 9.1 Course Outcome & Mapping Approval Workflow

This workflow governs the lifecycle of CO definitions and all associated mapping artifacts.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Section Teacher                                                       │
│  - Creates CO in DRAFT                                                        │
│  - Configures: Statement, Bloom Level, Delivery Methods                       │
│  - Creates CO-CP, CO-CA, CO-KP mappings (optional, in Draft)                 │
│  - Submits CO for review → State: SUBMITTED                                  │
└────────────────────────────┬─────────────────────────────────────────────────┘
                             │ [ApprovalRequested event emitted]
                             │ [Module Leader notified via Notification Context]
                             ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Module Leader                                                         │
│  - Reviews CO statement, bloom level, delivery methods                        │
│  - Reviews CO-CP, CO-CA, CO-KP mappings                                       │
│  - May REQUEST REVISION (returns to DRAFT with comments)                      │
│  - Or APPROVES → State: APPROVED at ML level                                  │
└────────────────────────────┬─────────────────────────────────────────────────┘
                             │ [ResultApprovedByModuleLeader event emitted]
                             │ [Program Coordinator notified]
                             ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Program Coordinator                                                   │
│  - Reviews CO and all mappings                                                │
│  - Configures CO-PO Mapping Matrix (weights 1/2/3)                            │
│  - Gives final APPROVAL → State: APPROVED                                     │
│  - PUBLISHES → State: PUBLISHED                                               │
└────────────────────────────┬─────────────────────────────────────────────────┘
                             │ [COPublished event emitted]
                             │ CO and mappings become read-only
                             ▼
                    [Assessment Context can now reference published COs]
```

---

## 9.2 Assessment Result Publication Workflow

This workflow governs marks entry and result publication per SectionOffering per term.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 0: Configuration (Program Coordinator)                                   │
│  - Configures assessments for the course section (types, weightages, marks)   │
│  - Maps each assessment to one or more COs with contribution weights           │
│  - Publishes assessment configuration → Section Teacher can enter marks       │
└────────────────────────────┬─────────────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Section Teacher                                                        │
│  - Enters marks per student per assessment                                    │
│  - Can update marks until submission                                          │
│  - Reviews marks for accuracy                                                 │
│  - Submits results for Module Leader approval                                 │
└────────────────────────────┬─────────────────────────────────────────────────┘
                             │ [ResultSubmittedByTeacher event emitted]
                             ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Module Leader                                                          │
│  - Reviews marks entered by teacher                                           │
│  - May reject with comments (returns to teacher)                              │
│  - Approves marks → forwarded to Coordinator                                 │
└────────────────────────────┬─────────────────────────────────────────────────┘
                             │ [ResultApprovedByModuleLeader event emitted]
                             ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Program Coordinator                                                   │
│  - Final review of marks                                                      │
│  - Approves and PUBLISHES results                                             │
│  - Marks become immutable (locked)                                            │
└────────────────────────────┬─────────────────────────────────────────────────┘
                             │ [ResultPublished event emitted]
                             │ Students can view results
                             │ Attainment calculation is triggered
                             ▼
                    [Attainment Context receives trigger]
```

---

## 9.3 Attainment Publication Workflow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Program Coordinator                                                   │
│  - Configures attainment thresholds (CO, Course, PO levels)                  │
│  - Selects direct/indirect method weightages                                  │
│  - Initiates AttainmentRun                                                    │
└────────────────────────────┬─────────────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: System (Automated Calculation)                                        │
│  1. Retrieves all StudentMark records for the SectionOffering                 │
│  2. Applies assessment CO weights to calculate per-CO marks                   │
│  3. Computes CO attainment % against threshold                                │
│  4. Computes Course attainment from CO attainments                            │
│  5. Applies CO-PO mapping weights to compute PO contributions                 │
│  6. Aggregates PO attainment across all courses                               │
└────────────────────────────┬─────────────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Program Coordinator                                                   │
│  - Reviews calculated attainment results                                      │
│  - Reviews CO/PO attainment vs threshold (flags for corrective action)        │
│  - Publishes the AttainmentRun                                                │
└────────────────────────────┬─────────────────────────────────────────────────┘
                             │ [AttainmentPublished event emitted]
                             │ [CourseOutcomeLocked event emitted for all COs in run]
                             ▼
                    [Accreditation Context consumes published data]
```

---

# 10. Entity Lifecycles

## 10.1 Organization Lifecycle

```
[System Initialization]
        │
        ▼ configure()
   ┌──────────┐
   │  ACTIVE  │ ◄─── Only one instance exists
   └────┬─────┘
        │ update() [Logo, Contact, Vision, Mission]
        ▼
   ┌──────────┐
   │ UPDATED  │ ── History captured in Audit Log
   └──────────┘
```

**Lifecycle Notes:**
- Created once during system initialization; cannot be deleted.
- Updates are versioned in audit logs only; no formal state transition.
- All other entities exist within this organization's boundary.

---

## 10.2 Department Lifecycle

```
create()    ┌──────────┐    archive()    ┌──────────┐
───────────►│  ACTIVE  │───────────────►│ ARCHIVED │
            │          │                └──────────┘
            └──────────┘
                  │ update()
                  ▼ [name, head, vision, mission]
            [Audit entry created]
```

**Lifecycle Notes:**
- Archiving is blocked if any non-archived Program references the department.
- Archived departments remain in the system for historical data integrity.
- The Head of Department reference must always point to an active user.

---

## 10.3 Program Lifecycle

```
create()    ┌──────────┐    archive()    ┌──────────┐
───────────►│  ACTIVE  │───────────────►│ ARCHIVED │
            │          │                └──────────┘
            └──────────┘
```

**Lifecycle Notes:**
- A program can be archived only if no active batches are enrolled in its curricula.
- Program metadata (type, credits, study mode) can be updated while active.
- Archiving a program does not archive its curricula; those are independently managed.

---

## 10.4 Curriculum Lifecycle

```
create()   ┌─────────┐   activate()   ┌──────────┐
──────────►│  DRAFT  │──────────────►│  ACTIVE  │
           └─────────┘               └────┬─────┘
                                          │
                              ┌───────────┴──────────┐
                              │                      │
                         archive()              version()
                              │                      │
                              ▼                      ▼
                        ┌──────────┐        ┌─────────────────┐
                        │ ARCHIVED │        │    VERSIONED    │
                        └──────────┘        │ (spawns new     │
                                            │  DRAFT version) │
                                            └─────────────────┘
```

**Lifecycle Notes:**
- A curriculum in DRAFT can be edited freely (terms, courses, structure).
- Once ACTIVE, structural changes require creating a new version.
- Versioning creates a new DRAFT curriculum inheriting course structure; changes are made there.
- Archived curriculum data remains accessible for historical reports.
- Multiple ACTIVE versions may coexist (e.g., Batch 66 on v2024, Batch 67 on v2026).

---

## 10.5 Course Lifecycle

```
create()   ┌──────────┐   archive()   ┌──────────┐
──────────►│  ACTIVE  │─────────────►│ ARCHIVED │
           │          │              └──────────┘
           └──────────┘
```

**Lifecycle Notes:**
- A course can be archived only if it is not present in any ACTIVE curriculum version.
- If the course has active prerequisite relationships, those must be resolved before archival.
- Archived courses remain in the course library; existing curriculum references are preserved and labeled accordingly.
- Course content (code, title, credits) can be edited while ACTIVE unless the course is referenced by a published curriculum.

---

## 10.6 Course Outcome (CO) Lifecycle

```
                   ┌─────────┐
        create()   │  DRAFT  │ ◄─────────────────────────────────────────────┐
        ──────────►│         │                                                │
                   └────┬────┘                                                │
                        │ submit()                                            │ reject()
                        ▼                                                     │
                  ┌───────────┐   reject()                                   │
                  │ SUBMITTED │ ─────────────────────────────────────────────┘
                  └─────┬─────┘
                        │ [Module Leader picks up]
                        ▼
                 ┌──────────────┐
                 │ UNDER_REVIEW │
                 └──────┬───────┘
                        │ approve()
                        ▼
                  ┌──────────┐
                  │ APPROVED │
                  └────┬─────┘
                       │ publish()  [Program Coordinator]
                       ▼
                 ┌────────────┐
                 │ PUBLISHED  │ ◄── CO and all mappings become read-only
                 └─────┬──────┘     Assessments may now reference this CO
                       │ lock()  [triggered by AttainmentPublished event]
                       ▼
                  ┌────────┐
                  │ LOCKED │ ── Terminal State: immutable record
                  └────────┘
```

**Lifecycle Notes:**
- A CO in DRAFT or SUBMITTED can be edited by the owning teacher.
- A CO in UNDER_REVIEW may only be commented on by the reviewer (no edits).
- At PUBLISHED, all four mapping types (CO-PO, CO-CP, CO-CA, CO-KP) are frozen.
- LOCKED is triggered by the system — not a manual action — when attainment is published.

---

## 10.7 Program Outcome (PO) Lifecycle

```
create()   ┌──────────┐   archive()   ┌──────────┐
──────────►│  ACTIVE  │─────────────►│ ARCHIVED │
           │          │   [blocked   └──────────┘
           └──────────┘    if linked]
```

**Lifecycle Notes:**
- PO statements can be updated while ACTIVE; changes propagate to future mappings only.
- Archival is blocked by BR-02: if any non-archived curriculum has CO-PO mapping entries referencing this PO, archival is refused.
- Once archived, the PO is not selectable in new CO-PO mapping matrices.
- Existing published mapping matrices that reference an archived PO are preserved as immutable historical records.
- The system ships with PO1–PO12 as defaults; coordinators may extend.

---

## 10.8 Assessment Lifecycle

```
configure()   ┌─────────────┐   publishConfig()   ┌──────────────────┐
─────────────►│  CONFIGURED │───────────────────►│ MARKS_OPEN       │
              │             │                     │ (Teacher enters  │
              └─────────────┘                     │  marks)          │
                                                  └────────┬─────────┘
                                                           │ submit()
                                                           ▼
                                                  ┌──────────────────┐
                                                  │ PENDING_APPROVAL │
                                                  └────────┬─────────┘
                                                           │ [approval chain]
                                                           ▼
                                                  ┌──────────────────┐
                                                  │    PUBLISHED     │
                                                  └────────┬─────────┘
                                                           │ [attainment published]
                                                           ▼
                                                    ┌────────────┐
                                                    │   LOCKED   │
                                                    └────────────┘
```

---

## 10.9 Attainment Lifecycle

```
[ResultPublished event received from Assessment Context]
        │
        ▼ initiate()  [Coordinator or automatic trigger]
 ┌──────────────┐
 │  INITIATED   │
 └──────┬───────┘
        │ [System auto-calculates]
        ▼
 ┌──────────────┐
 │  CALCULATED  │
 └──────┬───────┘
        │ review()  [Coordinator reviews numbers]
        ▼
 ┌──────────────┐
 │   REVIEWED   │
 └──────┬───────┘
        │ publish()  [Coordinator publishes]
        ▼
 ┌──────────────┐
 │  PUBLISHED   │ ── Triggers: CO locked, Accreditation report updated
 └──────────────┘
```

**Lifecycle Notes:**
- The AttainmentRun captures a snapshot of: CO-PO mapping weights, assessment CO weights, threshold configuration, and student marks at the time of calculation.
- Recalculation requires creating a new AttainmentRun; previous runs are immutable.
- Trend analysis compares AttainmentRun results across semesters and batches.

---

# 11. Risks and Architectural Challenges

## 11.1 Data Integrity Across Curriculum Versions

**Risk Level: Critical**

When a curriculum is versioned, existing courses, COs, mappings, and attainment records must remain associated with the correct version. Over 10+ years, a program may have 4–6 curriculum versions. Each batch must query its specific version's structure for accurate historical attainment.

**Challenge:** Reports that span multiple batches must reconcile heterogeneous curriculum structures (different COs, different POs, changed mapping weights).

**Recommendation:** Introduce a `CurriculumSnapshot` value object that is captured and stored alongside each `AttainmentRun`. Never recalculate attainment against a live curriculum — always against the snapshot.

---

## 11.2 Attainment Calculation Correctness

**Risk Level: Critical**

The calculation chain (StudentMark → CO attainment → Course attainment → PO attainment) involves multiple configurable parameters: assessment weightages, CO contribution weights, direct/indirect method split, threshold percentages. A bug or misconfiguration at any layer silently corrupts accreditation evidence.

**Challenge:** Accreditation auditors will inspect calculation methodology. The system must make the calculation formula inspectable and auditable, not just the output.

**Recommendation:** Implement `AttainmentFormula` as a fully stored value object within each `AttainmentRun`. Expose a calculation trace log for auditors. Consider a dedicated domain service `AttainmentCalculationService` with exhaustive unit test coverage.

---

## 11.3 CO Locking vs. Curriculum Versioning Conflict

**Risk Level: High**

A CO in `LOCKED` state due to published attainment cannot be edited. When a new curriculum version is needed, the system must decide: do locked COs migrate as-is, or are new COs created from scratch?

**Challenge:** If locked COs are copied to the new version, they start in DRAFT again — but historical attainment referenced the locked version. Accidental references to wrong-version COs in new mappings are a serious data integrity risk.

**Recommendation:** Model CO versions explicitly. A `CourseOutcome` entity should carry a `curriculumVersionId` reference. Cross-version CO similarity is advisory (for coordinator UX) — not structural coupling.

---

## 11.4 RBAC Extensibility at Runtime

**Risk Level: High**

The FRD requires future roles to be created without code changes. This implies a fully dynamic permission system. However, dynamic permissions introduce the risk of privilege escalation if the permission grant/revoke workflow is not itself tightly governed.

**Challenge:** Who can create new permissions? Who can assign custom roles? If super admins can invent arbitrary permission codes, an error in naming breaks all guards that check for that code.

**Recommendation:** Introduce two tiers of permissions: **system-defined permissions** (hardcoded strings, never deletable, always enforced in code) and **custom permissions** (coordinator-created, enforced by soft policy checks). System permissions take precedence.

---

## 11.5 Approval Workflow Bottlenecks

**Risk Level: Medium**

With the 3-level approval chain, if a Module Leader is unavailable, COs, marks, and results are blocked system-wide for their assigned courses.

**Challenge:** Academic institutions have leave, travel, and resignation events. A blocked approval chain near a semester deadline is operationally catastrophic.

**Recommendation:** Model a `DelegateApprover` concept within the approval workflow. When a primary approver is unavailable (or times out after a configurable period), approval authority can be temporarily delegated. Escalation rules should be configurable per department.

---

## 11.6 Report Generation Performance

**Risk Level: Medium**

Accreditation reports aggregate data across multiple batches, semesters, courses, and POs. For a mature program with 5+ batches and 50+ courses per curriculum, a single PO attainment trend report may touch millions of rows.

**Challenge:** These reports are generated on-demand and must not degrade the OLTP system performance.

**Recommendation:** Separate OLTP (transactional writes) from OLAP (analytical reads) using CQRS and a read model. Publish attainment results as pre-computed projections to a reporting store. Large report generation should be asynchronous (job queue + notification when ready).

---

## 11.7 Audit Log Volume and Queryability

**Risk Level: Medium**

The audit log covers every entity mutation across all contexts. At scale (multiple departments, programs, daily faculty usage), audit log volume will be substantial. Accreditation auditors will need to query it by entity, date range, and user.

**Challenge:** Storing audit logs in the same PostgreSQL instance as operational data degrades write performance under load.

**Recommendation:** Stream audit events to a separate append-only store (e.g., dedicated schema or separate service). Implement a `AuditQueryService` that is decoupled from the main operational database.

---

## 11.8 Prerequisites Graph Integrity

**Risk Level: Low-Medium**

Course prerequisite management must prevent circular dependencies (BR-06). As curriculum versions evolve and courses are added, cycle detection must run every time a prerequisite edge is added.

**Challenge:** A naive cycle check per operation is O(V+E). For large programs with 60+ courses and complex prerequisite chains, this is acceptable but must be done transactionally.

**Recommendation:** Implement cycle detection as a domain service `PrerequisiteGraphValidator`. Use an adjacency list representation within the `Course` aggregate. Validate within the same transaction as the edge addition.

---

# 12. Missing Requirements in the FRD

These gaps were identified through domain analysis. They represent either implicit requirements not yet documented, edge cases not yet considered, or capabilities needed for a production-grade system.

## 12.1 Critical Missing Requirements

| # | Gap | Impact |
|---|---|---|
| M-01 | **Student Enrollment Management** — No model for which students are in which section/batch. Marks cannot be entered without student roster data. | Assessment module cannot function |
| M-02 | **Student Identity** — No fields, roles, or lifecycle defined for the Student role. The FRD mentions students view results but does not define how students are enrolled, identified, or managed. | Core gap |
| M-03 | **Grade/Letter Grade Mapping** — No mechanism to convert percentage marks to letter grades (A, A+, B, etc.) for student-facing result views. | Student experience gap |
| M-04 | **Attainment Calculation Formula Specification** — The FRD states "system calculates" but does not specify the formula. Direct attainment? Indirect? Split percentage? This is the most critical missing specification. | Cannot implement attainment correctly |
| M-05 | **Accreditation Body Configuration** — The system must presumably support different accreditation frameworks (ABET, NBA, NAAC, AACSB). Each has different PO templates, report formats, and evidence requirements. No mechanism is defined for configuring this. | Accreditation module is under-specified |

## 12.2 Functional Gaps

| # | Gap | Impact |
|---|---|---|
| M-06 | **Academic Calendar Management** — No definition of how terms/semesters are dated, when enrollment opens, or when marks entry begins/ends. | Workflow scheduling impossible |
| M-07 | **Bulk Import / Export** — No bulk operations for students, marks, or courses. At scale, manual data entry is impractical. | Operational bottleneck |
| M-08 | **Course Re-take / Repeat Policy** — What happens when a student fails and retakes a course? Which marks are used for attainment? | Attainment data integrity |
| M-09 | **Graduation Requirement Verification** — No mechanism to verify that a student meets credit requirements for graduation. | Expected institutional feature |
| M-10 | **Student Grade Appeal / Remark** — No formal mechanism for students to dispute marks before publication. | Governance gap |
| M-11 | **Indirect Assessment Methods** — The FRD does not address indirect assessment (surveys, exit interviews). PO attainment typically requires a blend of direct and indirect. | Attainment methodology incomplete |
| M-12 | **CO Rubric Definition** — Rubric-based assessment is common in OBE; no rubric model is defined. | Assessment granularity missing |
| M-13 | **Corrective Action Plans** — When attainment falls below threshold, what is the documented corrective action process? No model exists. | Accreditation requirement |

## 12.3 Non-Functional & Operational Gaps

| # | Gap | Impact |
|---|---|---|
| M-14 | **Multi-tenancy Architecture** — NFR mentions future multi-university support, but no tenant isolation model is specified. Adding it later is extremely costly. | Future scalability risk |
| M-15 | **Concurrency Control Strategy** — No specification of optimistic vs. pessimistic locking for marks entry, mapping updates, or approval actions. Concurrent edits can corrupt data. | Data integrity risk |
| M-16 | **Soft Delete vs. Hard Delete Policy** — "Archive" is used throughout but no explicit policy on whether archived data is ever permanently deleted. | Data retention compliance gap |
| M-17 | **Two-Factor Authentication** — Not mentioned in security requirements. Required for admin accounts in most institutional compliance policies. | Security gap |
| M-18 | **Session Management** — JWT refresh token strategy mentioned but no token lifetime, rotation policy, or revocation mechanism defined. | Security gap |
| M-19 | **Localization / Internationalization** — Not mentioned. Institutions in non-English regions will require UI localization. | Adoption barrier |
| M-20 | **File Attachments for Assessments** — No model for attaching assignment files, project submissions, or evidence documents to assessments. | Assessment module incomplete |
| M-21 | **External LMS Integration** — No integration model for Moodle, Canvas, or Google Classroom (marks import, roster sync). | Operational efficiency gap |
| M-22 | **API Rate Limiting** — Not specified in NFR. Without rate limiting, bulk export endpoints are DDoS vectors. | Security & stability gap |
| M-23 | **Data Retention Policy** — How long are marks, attainment results, and audit logs retained? Not specified. Accreditation bodies may require 10+ year retention. | Compliance gap |

---

# 13. Future-Proofing Recommendations

These recommendations address the 10-year horizon. They are architectural investments that should be made at the start, not retrofitted.

## 13.1 Adopt Event-Driven Architecture from Day One

Emit domain events for every significant state transition. Store them durably (not just in-memory). This enables:
- Rebuilding read models from the event stream
- Decoupling between bounded contexts without tight API coupling
- Replay capability for debugging and audit
- Future integration with external systems without modifying existing code

**Investment:** Design a `DomainEvent` base type and an event bus (e.g., PostgreSQL-backed outbox pattern before introducing a message broker). All bounded context interactions should go through events, not direct database joins.

---

## 13.2 Apply CQRS for Attainment and Reporting

The attainment and reporting modules are inherently read-heavy and analytically complex. Separating the write model (transactional, normalized) from the read model (denormalized projections, pre-computed views) will:
- Prevent report queries from impacting operational write performance
- Allow the read model to evolve independently (new report types, new aggregations)
- Enable async report generation without blocking the user

**Investment:** Define read models as first-class artifacts alongside write aggregates. Even if both are backed by PostgreSQL initially, the logical separation enables future migration to a dedicated analytics store.

---

## 13.3 Design for Multi-tenancy from the Schema Level

Even if the first deployment is single-tenant, the data model should include a `tenant_id` (or `organization_id`) on every table that holds institutional data. Retrofitting multi-tenancy onto an existing single-tenant schema is one of the most expensive migrations possible.

**Investment:** Add `organization_id` as a non-nullable foreign key on all Org, Curriculum, OBE, and Assessment entities. This costs almost nothing now and is worth everything later.

---

## 13.4 Model Accreditation Bodies as Configuration, Not Code

Different institutions use different accreditation frameworks (ABET, NBA, NAAC, AACSB, WASC, etc.). Each body has different PO templates, report structures, and evidence standards.

**Investment:** Introduce an `AccreditationBody` configuration entity that defines:
- PO template (count, codes, default statements)
- Mapping methodology (direct/indirect weight ratios)
- Required report sections
- Evidence artifact types

The platform's core logic does not change when a new accreditation framework is added — only the configuration changes.

---

## 13.5 Versioned API Contracts

APIs evolve. Over 10 years, the frontend, mobile clients, and institutional integrations will depend on stable API contracts.

**Investment:** Version the API from day one (`/api/v1/...`). Define breaking vs. non-breaking change policy. Use OpenAPI specification as the contract — generate client SDKs and documentation from it. Establish a deprecation timeline policy for retiring old versions.

---

## 13.6 Configurable Attainment Calculation Engine

The attainment calculation formula is likely to change as OBE methodology evolves and as different institutions have different preferences (direct/indirect split, CO aggregation method, absolute vs. relative threshold).

**Investment:** Implement the attainment calculator as a pluggable strategy pattern. The `AttainmentRun` stores which strategy was used and with which parameters. New calculation strategies can be introduced without modifying existing run records.

---

## 13.7 Introduce an Outbox Pattern for Domain Events

Direct cross-context event publishing within a database transaction is fragile. If the event publish fails after the transaction commits, state becomes inconsistent.

**Investment:** Implement the Transactional Outbox Pattern: domain events are written to an `outbox` table within the same transaction as the aggregate mutation. A background relay process reads and publishes pending events. This guarantees at-least-once delivery with no data loss.

---

## 13.8 Invest in Schema Migration Governance

Over 10 years, the database schema will change hundreds of times. Without disciplined migration governance, schema drift between environments becomes a deployment risk.

**Investment:** Use a migration framework (Alembic for FastAPI/SQLAlchemy) with mandatory code review on every migration. Tag migrations with the domain event or feature they support. Maintain a schema changelog that corresponds to the domain model changelog.

---

# 14. Recommended Modular Architecture

The platform is organized as a set of vertically-aligned modules, each corresponding to a bounded context. Each module owns its domain model, business logic, and data access. Modules communicate through domain events or explicit application service interfaces.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY / BFF                             │
│              (Auth, Rate Limiting, Routing, OpenAPI)                 │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
          ┌─────────────────────┼──────────────────────┐
          ▼                     ▼                      ▼
┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐
│   iam-module    │  │   org-module     │  │ curriculum-module  │
│                 │  │                  │  │                    │
│ User            │  │ Organization     │  │ Curriculum         │
│ Role            │  │ Department       │  │ Course             │
│ Permission      │  │ Program          │  │ Batch              │
│ AuthToken       │  │                  │  │ AcademicTerm       │
└────────┬────────┘  └────────┬─────────┘  └────────┬───────────┘
         │                   │                      │
         └──────────┬────────┘                      │
                    ▼                               ▼
          ┌─────────────────────────────────────────────────────┐
          │                   obe-module                         │
          │                                                      │
          │  ProgramOutcome   CourseOutcome   COPOMapping        │
          │  COCPMapping      COCAMapping     COKPMapping        │
          │  BloomLevel       DeliveryMethod  MappingWeight      │
          └──────────────────────────┬──────────────────────────┘
                                     │
               ┌─────────────────────┼──────────────────────┐
               ▼                     ▼                      ▼
   ┌───────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
   │ assessment-module │  │ attainment-module│  │ approval-module      │
   │                   │  │                  │  │                      │
   │ Assessment        │  │ AttainmentRun    │  │ ApprovalRequest      │
   │ StudentMark       │  │ COAttainment     │  │ ApprovalChain        │
   │ SectionOffering   │  │ POAttainment     │  │ DelegateApprover     │
   │ ResultPublication │  │ TrendAnalysis    │  │                      │
   └────────┬──────────┘  └──────────┬───────┘  └──────────────────────┘
            │                        │
            └──────────┬─────────────┘
                       ▼
          ┌──────────────────────────────────────────────────────┐
          │               accreditation-module                    │
          │                                                       │
          │  AccreditationBody   AccreditationReport             │
          │  EvidenceArtifact    ComplianceChecklist             │
          └──────────────────────────────────────────────────────┘
                       │
               ┌───────┴────────┐
               ▼                ▼
  ┌────────────────────┐  ┌──────────────────────┐
  │  reporting-module  │  │  notification-module  │
  │                    │  │                       │
  │ ReportDefinition   │  │ NotificationTemplate  │
  │ ReportRun          │  │ DeliveryChannel       │
  │ ExportFormat       │  │ NotificationLog       │
  └────────────────────┘  └──────────────────────┘
                       │
                       ▼
          ┌──────────────────────────────────────┐
          │            audit-module               │
          │                                       │
          │  AuditEvent   AuditQuery              │
          │  (Append-only, event-sourced)         │
          └──────────────────────────────────────┘
```

## Module Dependency Rules

| Rule | Description |
|---|---|
| **No circular dependencies** | Module A may depend on Module B only if B does not depend on A. |
| **No cross-module direct DB joins** | Modules never query each other's tables. Data is shared through application service interfaces or domain events. |
| **Shared Kernel is minimal** | Only `UserIdentity` (userId, email, roleRefs) and primitive value objects (Email, PermissionCode) live in the shared kernel. |
| **IAM has no domain dependencies** | IAM module knows nothing about OBE, curricula, or assessments. All scoping (e.g., "coordinator of program X") is handled in the IAM module's `UserRoleAssignment` with generic scope references. |
| **Audit has no upstream dependencies** | The audit module only subscribes to events; it never calls other modules. |

## Deployment Topology (Monolith-First)

Start as a well-structured modular monolith. The module boundaries defined above make future extraction to microservices possible without cross-cutting rewrites.

```
┌────────────────────────────────────────────────────────────┐
│                    Docker Deployment                        │
│                                                            │
│  ┌──────────────────────────────┐  ┌────────────────────┐ │
│  │    Next.js Frontend (BFF)    │  │   Nginx (Reverse   │ │
│  │    Port 3000                 │  │   Proxy + TLS)     │ │
│  └───────────────┬──────────────┘  └────────────────────┘ │
│                  │                                         │
│  ┌───────────────▼──────────────┐                         │
│  │  FastAPI Application Server  │                         │
│  │  (Modular Monolith)          │                         │
│  │  All modules in one process  │                         │
│  │  Internal event bus (sync)   │                         │
│  └───────────────┬──────────────┘                         │
│                  │                                         │
│  ┌───────────────▼──────────────┐  ┌────────────────────┐ │
│  │   PostgreSQL (Primary Store) │  │   Redis (Cache +   │ │
│  │   One schema per module      │  │   Session Store)   │ │
│  └──────────────────────────────┘  └────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────┐                         │
│  │   MinIO (File Storage)       │                         │
│  │   Logos, Report exports,     │                         │
│  │   Attachment uploads         │                         │
│  └──────────────────────────────┘                         │
└────────────────────────────────────────────────────────────┘
```

**Schema-per-module in PostgreSQL:**
- `iam.*` — users, roles, permissions
- `org.*` — organization, departments, programs
- `curriculum.*` — curricula, courses, batches
- `obe.*` — POs, COs, mappings
- `assessment.*` — assessments, marks
- `attainment.*` — attainment runs and results
- `audit.*` — append-only audit events
- `notification.*` — notification queue and log
- `reporting.*` — report definitions and run cache

This schema separation enforces bounded context isolation at the database level while remaining in a single PostgreSQL instance — the best of both worlds for a single-institution deployment.

---

*End of DDD Analysis Document — OBE Accreditation Management Platform v1.0*
