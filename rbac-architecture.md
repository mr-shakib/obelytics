# OBE Accreditation Management Platform
## RBAC Authorization Architecture v1.0

> **Based on:** FRD v1.0 + DDD Analysis v1.0 + DB Architecture v1.0  
> **Date:** 2026-06-04  
> No code generated. Architecture only.

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Permission Taxonomy](#2-permission-taxonomy)
3. [Permission Naming Convention](#3-permission-naming-convention)
4. [Full Permission Catalog](#4-full-permission-catalog)
5. [Permission Groups](#5-permission-groups)
6. [Permission Hierarchy](#6-permission-hierarchy)
7. [Role Definitions](#7-role-definitions)
8. [Role–Permission Matrix](#8-rolepermission-matrix)
9. [Scope Architecture](#9-scope-architecture)
10. [Access Control Strategy](#10-access-control-strategy)
11. [UI Visibility Control](#11-ui-visibility-control)
12. [Special Cases and Edge Rules](#12-special-cases-and-edge-rules)
13. [Future Scalability Recommendations](#13-future-scalability-recommendations)

---

# 1. Design Principles

These principles govern every decision in this RBAC design. Deviating from them requires formal architecture review.

| # | Principle | Rationale |
|---|---|---|
| R-01 | **Permissions, not roles, control behavior** | Application code checks permission codes, never role names. Role names change; permission codes are stable contracts. |
| R-02 | **Explicit over implicit** | No hidden inheritance chains. Every permission a role has is explicitly granted. What you see is what the role gets. |
| R-03 | **Two enforcement layers are mandatory** | Every protected operation requires both a permission check AND a scope/data check. Passing only one is insufficient. |
| R-04 | **SYSTEM permissions are immutable** | System-tier permissions are defined in code, never in the database. They cannot be created, renamed, or deleted by any user including Super Admin. |
| R-05 | **Scope lives in the assignment, not the permission** | `curriculum.create` is one permission. Whether a coordinator can create curricula for CSE or for ALL programs is determined by their role assignment's scope, not by separate permission codes. |
| R-06 | **The UI reflects permissions, never roles** | The frontend never checks `user.role === 'Program Coordinator'`. It checks `permissions.includes('co.approve')`. Role names are internal taxonomy only. |
| R-07 | **Deny by default** | If no permission check passes, access is denied. There is no implicit allow for any operation. |
| R-08 | **Audit every authorization decision** | Failed permission checks are audited at the same fidelity as successful ones. Security investigations require both. |
| R-09 | **Assignment-based scope is a second gate** | For Module Leaders and Section Teachers, faculty assignment records are a second gate beyond the permission check. Both gates must pass. |
| R-10 | **Custom roles cannot escalate to system tier** | A custom role can hold any DOMAIN-tier permissions but cannot be granted SYSTEM-tier permissions. This ceiling is enforced at the application level. |

---

# 2. Permission Taxonomy

## 2.1 Three-Dimensional Permission Space

Every permission exists in three dimensions:

```
PERMISSION = Resource Domain × Action × (Scope applied at assignment)

Example:
  co.approve             → resource=co, action=approve, scope=from role assignment
  marks.read.section     → resource=marks, action=read, contextual scope hint=section
  system.audit.read      → resource=system.audit, action=read, scope=always GLOBAL
```

## 2.2 Resource Domain Hierarchy

Resources are organized in a two-level hierarchy: **domain** and **sub-resource**.

```
Platform
│
├── system                     System-level operations
│   ├── organization           Org settings
│   ├── audit                  Audit log
│   ├── roles                  Role management
│   └── permissions            Permission management
│
├── department                 Department CRUD
├── program                    Program CRUD
├── user                       User management
│
├── config                     Reference data
│   ├── bloom                  Bloom domains and levels
│   ├── delivery_method        Teaching delivery methods
│   ├── course_type            Course type definitions
│   ├── assessment_type        Assessment type definitions
│   ├── cp                     Complex Problems
│   ├── ca                     Complex Activities
│   ├── kp                     Knowledge Profiles
│   └── mapping_weight         Mapping weight labels
│
├── curriculum                 Curriculum version management
├── course                     Course definitions
│   └── prerequisite           Prerequisite graph management
├── batch                      Student cohort management
│
├── academic_term              Operational running terms
├── section                    Section definitions
├── section_offering           Course delivery instances
└── faculty_assignment         Teacher-to-section assignments
│
├── po                         Program Outcomes
│
├── co                         Course Outcomes
│
├── mapping
│   ├── co_po                  CO↔PO mapping matrices
│   ├── co_cp                  CO↔Complex Problem mappings
│   ├── co_ca                  CO↔Complex Activity mappings
│   └── co_kp                  CO↔Knowledge Profile mappings
│
├── assessment                 Assessment configuration
├── marks                      Student marks entry and reading
├── result                     Result publication workflow
│
├── attainment                 Attainment calculation and publication
│
├── report                     Report generation by category
│   ├── curriculum
│   ├── co
│   ├── po
│   ├── attainment
│   ├── accreditation
│   ├── faculty
│   ├── batch
│   └── assessment
│
├── accreditation              Accreditation body and cycle management
│
└── student                    Student self-service (own data only)
```

## 2.3 Action Vocabulary

Actions are the verbs applied to resources. Every permission code uses exactly one action from this table.

| Action | Meaning | Notes |
|---|---|---|
| `create` | Instantiate a new record | |
| `read` | View, list, or search records | May have `.section` / `.all` / `.own` qualifier |
| `update` | Modify an existing record's fields | |
| `archive` | Move a record to archived state | Not physical delete |
| `version` | Create a new version derived from an existing record | Only for Curriculum |
| `manage` | Shorthand for create + read + update + archive | Used for config sub-resources |
| `configure` | Set configuration options (non-CRUD) | Used for assessment setup, attainment thresholds |
| `submit` | Initiate the approval workflow | Workflow action |
| `approve` | Advance a workflow step | Workflow action; role-suffix used where multiple levels exist |
| `reject` | Decline and return a workflow step | Workflow action |
| `publish` | Make data visible to downstream consumers | Irreversible; requires prior approval |
| `enter` | Input marks data | Specific to marks to distinguish from general `update` |
| `export` | Generate a downloadable file | Cross-cutting; applies to reports |
| `assign` | Link one entity to another | Used for role and faculty assignment |
| `revoke` | Remove an assignment | Complement of `assign` |
| `initiate` | Start a computation process | Specific to attainment runs |

## 2.4 Scope Vocabulary

Scope is **not part of the permission code** (except for contextual hints). Scope is part of the role assignment record.

| Scope Level | Stored In | Meaning |
|---|---|---|
| `GLOBAL` | `user_role_assignments.scope_type = GLOBAL` | Access to all records across the organization |
| `DEPARTMENT` | `scope_type = DEPARTMENT, scope_id = <dept_uuid>` | Access to records within one department |
| `PROGRAM` | `scope_type = PROGRAM, scope_id = <program_uuid>` | Access to records within one program |
| `OFFERING` | Derived from `faculty_assignments` | Access to records for assigned section offerings only |
| `SELF` | Derived from student identity linkage | Access to own data only |

**Scope elevation rule:** A broader scope always includes narrower scopes. A user with GLOBAL scope can access everything a PROGRAM-scoped user can. A user with two PROGRAM assignments can access data in either program.

**Contextual qualifier in permission codes:** Some permissions include a qualifier (`.section`, `.all`, `.own`) as a documentation hint about the *intended* narrowest scope. These qualifiers are informational in the permission code — they tell developers "this permission is designed for narrow access." The actual enforcement is still done through the scope resolution algorithm.

---

# 3. Permission Naming Convention

## 3.1 Format Specification

```
{resource_domain}[.{sub_resource}].{action}[.{contextual_qualifier}]
```

**Components:**

| Component | Format | Required | Examples |
|---|---|---|---|
| `resource_domain` | `snake_case`, singular | Always | `co`, `curriculum`, `system`, `mapping` |
| `sub_resource` | `snake_case`, singular | When resource has sub-types | `co_po`, `bloom`, `audit` |
| `action` | single verb from Action Vocabulary | Always | `create`, `approve`, `publish` |
| `contextual_qualifier` | `snake_case` scope hint | Only when action has multiple access levels | `section`, `all`, `own`, `ml`, `pc` |

**Tier prefix (stored in `iam.permissions.tier`, never in the code):**

| Tier | Meaning | Examples |
|---|---|---|
| `SYSTEM` | Defined in code; cannot be modified at runtime | `system.roles.create`, `system.audit.read` |
| `DOMAIN` | Standard domain permissions; pre-seeded but referenceable | `co.approve`, `curriculum.create` |
| `CUSTOM` | Created by authorized admin at runtime; soft-enforced | Any `custom.*` namespace |

## 3.2 Canonical Examples

```
✅ CORRECT
  system.audit.read           → Read audit logs (system resource, read action)
  co.approve                  → Approve course outcomes
  mapping.co_po.publish       → Publish CO-PO mapping matrix
  marks.read.section          → Read marks for assigned section (contextual qualifier)
  marks.read.all              → Read all marks (broader access)
  result.approve.ml           → Approve results at Module Leader step
  result.approve.pc           → Approve results at Program Coordinator step
  student.marks.read.own      → Student reads their own marks
  report.attainment.generate  → Generate attainment reports
  config.cp.manage            → Manage Complex Problems reference data

❌ INCORRECT
  CO_APPROVE                  → Not snake_case, not dot-separated
  co.canApprove               → Action is a verb phrase, not a verb
  approve.co                  → Resource comes first, always
  co.approve.program          → 'program' is a scope level, not a qualifier; scope goes in assignment
  coordinator.co.approve      → Role name does not belong in permission code
  co.*                        → Wildcards not used in permission codes
```

## 3.3 Reserved Namespaces

| Namespace | Reserved For |
|---|---|
| `system.*` | Super Admin only. Cannot be assigned to any custom role. |
| `student.*` | Student self-service permissions. Cannot be assigned to non-student roles. |
| `custom.*` | Coordinator-created custom permissions for custom roles. |

---

# 4. Full Permission Catalog

## Tier: SYSTEM

These permissions are defined in application code. They cannot be created, renamed, or deleted at runtime.

| Permission Code | Description | Assignable To |
|---|---|---|
| `system.organization.configure` | Edit organization name, logo, contact, regex | Super Admin only |
| `system.audit.read` | View complete audit log | Super Admin only |
| `system.roles.create` | Create new roles | Super Admin only |
| `system.roles.delete` | Delete non-system roles | Super Admin only |
| `system.permissions.grant` | Grant permissions to roles | Super Admin only |
| `system.permissions.revoke` | Revoke permissions from roles | Super Admin only |
| `system.users.impersonate` | Act as another user for support | Super Admin only |

## Tier: DOMAIN

Pre-seeded, stable permission codes used across all roles.

### Department & Program Management

| Permission Code | Description |
|---|---|
| `department.create` | Create new departments |
| `department.read` | View department details |
| `department.update` | Edit department information |
| `department.archive` | Archive a department |
| `department.head.assign` | Assign/change HOD |
| `program.create` | Create new academic programs |
| `program.read` | View program details |
| `program.update` | Edit program information |
| `program.archive` | Archive a program |

### User Management

| Permission Code | Description |
|---|---|
| `user.create` | Create new faculty/staff user accounts |
| `user.read` | View user profiles |
| `user.update` | Edit user information |
| `user.deactivate` | Deactivate a user account |
| `user.password.reset` | Reset a user's password |
| `user.role.assign` | Assign roles to users |
| `user.role.revoke` | Revoke role assignments |

### Configuration Management

| Permission Code | Description |
|---|---|
| `config.bloom.manage` | Create/update/archive Bloom domains and levels |
| `config.delivery_method.manage` | Manage delivery method reference data |
| `config.course_type.manage` | Manage course type reference data |
| `config.assessment_type.manage` | Manage assessment type reference data |
| `config.cp.manage` | Manage Complex Problem codes |
| `config.ca.manage` | Manage Complex Activity codes |
| `config.kp.manage` | Manage Knowledge Profile codes |
| `config.mapping_weight.configure` | Configure weight label names (Low/Medium/High) |

### Curriculum Management

| Permission Code | Description |
|---|---|
| `curriculum.create` | Create a new curriculum |
| `curriculum.read` | View curriculum structure |
| `curriculum.update` | Edit curriculum details and structure |
| `curriculum.archive` | Archive a curriculum version |
| `curriculum.version` | Create a new version from an existing curriculum |

### Course Management

| Permission Code | Description |
|---|---|
| `course.create` | Create new course definitions |
| `course.read` | View course details |
| `course.update` | Edit course information |
| `course.archive` | Archive a course |
| `course.prerequisite.manage` | Add/remove prerequisite edges |

### Batch Management

| Permission Code | Description |
|---|---|
| `batch.create` | Create student batches |
| `batch.read` | View batch information |
| `batch.update` | Edit batch details |
| `batch.archive` | Archive a batch |

### Academic Structure

| Permission Code | Description |
|---|---|
| `academic_term.create` | Create running academic terms (Spring 2026, etc.) |
| `academic_term.update` | Edit term dates and status |
| `section.create` | Create section definitions |
| `section.update` | Edit sections |
| `section_offering.create` | Create course section offerings |
| `section_offering.update` | Edit section offering status |
| `faculty_assignment.create` | Assign faculty to section offerings |
| `faculty_assignment.update` | Reassign or remove faculty |

### Program Outcomes

| Permission Code | Description |
|---|---|
| `po.create` | Create new Program Outcomes |
| `po.read` | View PO details |
| `po.update` | Edit PO statement and attributes |
| `po.archive` | Archive a PO (guarded by BR-02) |

### Course Outcomes

| Permission Code | Description |
|---|---|
| `co.create` | Create new Course Outcomes in Draft |
| `co.read` | View CO details and mappings |
| `co.update` | Edit CO statement, Bloom level, delivery methods |
| `co.submit` | Submit a CO for approval workflow |
| `co.approve` | Approve a CO submission |
| `co.reject` | Reject a CO submission (returns to Draft) |
| `co.publish` | Publish an approved CO |
| `co.archive` | Archive a CO (blocked after PUBLISHED) |

### CO Mappings

| Permission Code | Description |
|---|---|
| `mapping.co_po.create` | Create CO-PO mapping set for a course |
| `mapping.co_po.read` | View CO-PO mapping matrices |
| `mapping.co_po.update` | Edit CO-PO weight entries |
| `mapping.co_po.approve` | Approve CO-PO mapping set |
| `mapping.co_po.publish` | Publish CO-PO mapping set |
| `mapping.co_cp.manage` | Create/update CO-Complex Problem links |
| `mapping.co_cp.approve` | Approve CO-CP mappings |
| `mapping.co_ca.manage` | Create/update CO-Complex Activity links |
| `mapping.co_ca.approve` | Approve CO-CA mappings |
| `mapping.co_kp.manage` | Create/update CO-Knowledge Profile links |
| `mapping.co_kp.approve` | Approve CO-KP mappings |

### Assessment

| Permission Code | Description |
|---|---|
| `assessment.configure` | Create and configure assessments for a section offering |
| `assessment.read` | View assessment configuration |
| `assessment.publish_config` | Publish assessment configuration (enable marks entry) |

### Marks

| Permission Code | Description |
|---|---|
| `marks.enter` | Enter student marks for assessments |
| `marks.update` | Update marks before publication |
| `marks.read.section` | View marks for assigned section (teacher/ML view) |
| `marks.read.all` | View all marks within scope (coordinator view) |

### Result Publication

| Permission Code | Description |
|---|---|
| `result.submit` | Submit section results to approval chain |
| `result.approve.ml` | Perform Module Leader approval step |
| `result.reject.ml` | Reject at Module Leader step |
| `result.approve.pc` | Perform Program Coordinator approval step |
| `result.reject.pc` | Reject at Program Coordinator step |
| `result.publish` | Publish final approved results |
| `result.read.section` | View results for assigned section |
| `result.read.all` | View all results within scope |
| `result.read.own` | View own results (Student only) |

### Attainment

| Permission Code | Description |
|---|---|
| `attainment.configure` | Set threshold percentages and formula type |
| `attainment.initiate` | Trigger an attainment calculation run |
| `attainment.review` | Review computed attainment results |
| `attainment.publish` | Publish an attainment run |
| `attainment.read` | View attainment results and trend reports |

### Reports

| Permission Code | Description |
|---|---|
| `report.curriculum.generate` | Generate curriculum structure reports |
| `report.co.generate` | Generate CO and mapping reports |
| `report.po.generate` | Generate PO attainment reports |
| `report.attainment.generate` | Generate attainment calculation reports |
| `report.accreditation.generate` | Generate SAR and accreditation evidence reports |
| `report.faculty.generate` | Generate faculty assignment reports |
| `report.batch.generate` | Generate batch and cohort reports |
| `report.assessment.generate` | Generate assessment and marks reports |
| `report.export` | Download generated reports (PDF, Excel, CSV) |

### Accreditation

| Permission Code | Description |
|---|---|
| `accreditation.body.manage` | Create/configure accreditation body frameworks |
| `accreditation.cycle.create` | Create a new accreditation review cycle |
| `accreditation.cycle.manage` | Manage cycle status and timeline |
| `accreditation.report.generate` | Generate official accreditation submission reports |

## Tier: STUDENT (self-scoped)

Student permissions are structurally isolated. They can never be assigned to non-student roles.

| Permission Code | Description |
|---|---|
| `student.profile.read.own` | View own student profile |
| `student.curriculum.read.own` | View own program's curriculum |
| `student.course.read.own` | View enrolled course details |
| `student.result.read.own` | View own assessment results |
| `student.marks.read.own` | View own marks per assessment |
| `student.co.read.own` | View COs for enrolled courses |
| `student.po.read.own` | View program's POs |

---

# 5. Permission Groups

Permission Groups are named bundles of logically related permissions. They serve three purposes:

1. Simplify role configuration (assign a group rather than individual permissions)
2. Document the intent of a role (what capability cluster does it represent)
3. Serve as the unit of custom role composition

Groups are not stored in the database as a formal entity in v1 — they are documented conventions. In v2, a `permission_groups` table and `role_permission_groups` junction can formalize this.

| Group Name | Permissions Included | Typical Holder |
|---|---|---|
| **G01 · System Administration** | All `system.*` permissions | Super Admin |
| **G02 · Organization Setup** | `department.*`, `program.*` | Super Admin |
| **G03 · User Administration** | `user.*` | Super Admin |
| **G04 · Reference Data Management** | All `config.*` | Super Admin, Program Coordinator |
| **G05 · Curriculum Authoring** | `curriculum.*`, `course.*`, `course.prerequisite.*`, `batch.*` | Program Coordinator |
| **G06 · Academic Structure Management** | `academic_term.*`, `section.*`, `section_offering.*`, `faculty_assignment.*` | Program Coordinator |
| **G07 · PO Management** | `po.*` | Program Coordinator |
| **G08 · CO Authoring** | `co.create`, `co.read`, `co.update`, `co.submit` | Section Teacher |
| **G09 · CO Governance** | `co.approve`, `co.reject`, `co.publish`, `co.archive` | Module Leader, Program Coordinator |
| **G10 · Mapping Authoring** | `mapping.co_cp.manage`, `mapping.co_ca.manage`, `mapping.co_kp.manage` | Section Teacher |
| **G11 · Mapping Governance** | `mapping.co_po.*`, `mapping.co_cp.approve`, `mapping.co_ca.approve`, `mapping.co_kp.approve` | Module Leader, Program Coordinator |
| **G12 · Assessment Configuration** | `assessment.configure`, `assessment.read`, `assessment.publish_config` | Program Coordinator |
| **G13 · Marks Entry** | `marks.enter`, `marks.update`, `marks.read.section` | Section Teacher |
| **G14 · Marks Oversight** | `marks.read.all` | Module Leader, Program Coordinator |
| **G15 · Result Workflow — Teacher** | `result.submit`, `result.read.section` | Section Teacher |
| **G16 · Result Workflow — ML** | `result.approve.ml`, `result.reject.ml`, `result.read.all` (scoped) | Module Leader |
| **G17 · Result Workflow — Coordinator** | `result.approve.pc`, `result.reject.pc`, `result.publish`, `result.read.all` | Program Coordinator |
| **G18 · Attainment Management** | `attainment.*` | Program Coordinator |
| **G19 · Attainment Read-Only** | `attainment.read` | Module Leader, Section Teacher |
| **G20 · Report Generation** | All `report.*` | Program Coordinator |
| **G21 · Report Read-Only** | `report.co.generate`, `report.assessment.generate`, `report.export` | Section Teacher (scoped) |
| **G22 · Accreditation Management** | `accreditation.*` | Program Coordinator |
| **G23 · Student Self-Service** | All `student.*` | Student |

---

# 6. Permission Hierarchy

## 6.1 No Role Inheritance — Explicit Assignment Only

This system uses **flat explicit permission assignment**, not hierarchical role inheritance. There is no "Program Coordinator extends Module Leader" relationship.

**Why:** Inheritance chains produce hidden permissions. When a senior role is modified, it silently modifies all roles that inherit from it. In an accreditation context where permissions are audited, hidden changes are unacceptable.

Every permission a role holds is explicitly granted and appears in the `role_permissions` table. The audit trail shows exactly when each permission was added or removed and by whom.

## 6.2 Scope Elevation (Hierarchical by Scope Level, Not Role)

Scope levels do form a containment hierarchy:

```
GLOBAL ⊃ DEPARTMENT ⊃ PROGRAM ⊃ (OFFERING) ⊃ SELF
```

A user assigned with GLOBAL scope for `curriculum.read` can read all curricula across all programs. A user assigned with PROGRAM scope for `curriculum.read` can only read curricula belonging to that program.

**Multi-assignment elevation:** A user with two separate PROGRAM-scope assignments (CSE and EEE) can access data in either program. Scopes are OR'd together across assignments.

```
Effective access = UNION of all scopes where permission is held
```

## 6.3 Permission Tier Ceiling

```
SYSTEM tier  ───────────────────────── Super Admin role only
    │                                  (cannot be granted to any other role)
    │ ceiling: SYSTEM permissions
    ▼                                  
DOMAIN tier  ───────────────────────── All standard roles
    │                                  (pre-seeded, any role can hold these)
    │ ceiling: custom roles cannot hold system permissions
    ▼
CUSTOM tier  ───────────────────────── Custom roles only
                                       (org-admin-created, soft-enforced)
```

**Ceiling enforcement:** When an admin attempts to assign a `system.*` permission to any role other than the designated Super Admin role, the application must reject the assignment with a clear error. This check is in the application service layer, not enforced by a database constraint.

## 6.4 Permission Composition for Custom Roles

Custom roles are composed from existing DOMAIN-tier permission groups. The composition model:

```
Custom Role
  └── Selects from existing permission groups (G01–G22)
  └── Cannot include any SYSTEM-tier permission
  └── Cannot include any STUDENT-tier permission
  └── Inherits the scope mechanism of the groups selected
  └── Scope is set per user assignment, same as built-in roles
```

This means a future "Department Coordinator" custom role could be created by selecting G04 + G05 + G07 + G20 with DEPARTMENT scope — without any code change.

## 6.5 Effective Permission Resolution

```
Effective permissions for User U =
  UNION of all permissions
    across all active role assignments
    where each permission is scoped by its assignment's scope_type and scope_id
```

A user with two roles (Module Leader for CSE + Section Teacher for an EEE course) holds the union of permissions from both, each constrained by its respective scope.

---

# 7. Role Definitions

## 7.1 Super Admin

| Attribute | Value |
|---|---|
| **Purpose** | Platform-level administrator. Manages the institutional instance. |
| **Scope Level** | GLOBAL — no restrictions |
| **Is System Role** | YES — cannot be deleted |
| **Max Assignees** | No hard limit; should be minimal in practice (1–3 trusted administrators) |
| **Can Create Custom Roles** | YES |
| **Can Assign System Permissions** | YES |
| **Data Access** | All records across all departments and programs |

**Owned Permission Groups:** G01, G02, G03, G04, G05, G06, G07, G09, G11, G12, G14, G17, G18, G20, G22 + all DOMAIN permissions

**Key Restrictions:**
- Cannot modify their own role assignments (prevents self-privilege-escalation)
- Cannot delete another Super Admin account (preserves minimum one admin)
- All Super Admin actions are flagged in the audit log with elevated visibility

---

## 7.2 Program Coordinator

| Attribute | Value |
|---|---|
| **Purpose** | Full authority over a specific academic program. Manages curriculum, outcomes, and accreditation evidence. |
| **Scope Level** | PROGRAM — scoped per program assignment |
| **Is System Role** | YES |
| **Multi-Program Assignment** | Supported — one user can be coordinator of multiple programs (separate assignments) |
| **Data Access** | All records within assigned program(s) |

**Owned Permission Groups:** G04 (read-only for unowned config), G05, G06, G07, G08 (oversight), G09, G10 (oversight), G11, G12, G14, G17, G18, G19, G20, G21, G22

**Specific Permissions Beyond Groups:**
- `user.read` — Can view user profiles within program scope
- `po.create`, `po.update`, `po.archive` — Full PO lifecycle management
- `co.read`, `co.update`, `co.publish` — Full CO governance
- `faculty_assignment.create`, `faculty_assignment.update` — Assigns teachers to sections

**Key Restrictions:**
- Cannot create or archive departments/programs (Super Admin only)
- Cannot manage users outside their program scope
- Cannot grant system-tier permissions

---

## 7.3 Module Leader

| Attribute | Value |
|---|---|
| **Purpose** | Course-level authority. Reviews and governs COs and marks for assigned courses. |
| **Scope Level** | PROGRAM (assignment level) + OFFERING (data filter level) |
| **Is System Role** | YES |
| **Data Access** | Read-heavy; write-access only for assigned section offerings |

**Scope Note:** A Module Leader's role assignment is scoped to PROGRAM. However, their read/write access to COs, marks, and results is further filtered to section offerings where they appear in `faculty_assignments` with `role_in_course = 'MODULE_LEADER'`. This is a second gate beyond the role assignment scope.

**Owned Permission Groups:** G09 (CO governance, offering-scoped), G11 (mapping governance, offering-scoped), G14 (marks read, offering-scoped), G16, G19, G21

**Specific Permissions:**
- `po.read` — Read-only view of program outcomes
- `curriculum.read` — Read-only view of curriculum
- `course.read` — Read-only view of course definitions
- `co.read`, `co.update` — Can comment on and update COs for assigned courses only
- `co.approve`, `co.reject` — For assigned courses only
- `assessment.read` — View assessment configuration for assigned sections
- `marks.read.section` — View marks for assigned sections
- `result.read.all` — View all results for assigned courses (for coordination)
- `attainment.read` — View attainment results for assigned courses

**Key Restrictions:**
- Cannot create curricula, courses, or batches
- Cannot configure attainment thresholds
- Cannot publish CO-PO mapping sets (Coordinator only)
- Cannot approve results at PC level
- All write operations are offering-scoped (second gate via faculty_assignments)

---

## 7.4 Section Teacher

| Attribute | Value |
|---|---|
| **Purpose** | Responsible for course delivery. Creates COs in draft, enters marks, submits results. |
| **Scope Level** | PROGRAM (assignment level) + OFFERING (data filter level) |
| **Is System Role** | YES |
| **Data Access** | Write-access strictly limited to their assigned section offerings |

**Scope Note:** Same dual-gate mechanism as Module Leader. Section Teacher's actual data scope is bounded by `faculty_assignments` with `role_in_course = 'SECTION_TEACHER'`.

**Owned Permission Groups:** G08, G10, G13, G15, G19, G21

**Specific Permissions:**
- `po.read` — Read-only
- `curriculum.read` — Read-only
- `course.read` — Read-only
- `co.create` — Draft COs for assigned courses only
- `co.read` — View COs for assigned courses
- `co.update` — Edit draft COs they created
- `co.submit` — Submit COs to approval chain
- `mapping.co_cp.manage`, `mapping.co_ca.manage`, `mapping.co_kp.manage` — Author CP/CA/KP mappings
- `mapping.co_po.read` — Read-only view of CO-PO mapping
- `assessment.read` — View assessment configuration for their sections
- `marks.enter`, `marks.update` — Enter and update marks for their sections
- `marks.read.section` — View marks within their sections
- `result.submit` — Submit results to approval chain
- `result.read.section` — View results for their sections
- `attainment.read` — Read-only attainment view

**Key Restrictions:**
- Cannot approve COs (their own or others')
- Cannot approve or publish results
- Cannot modify published CO-PO mapping matrices
- Cannot configure attainment
- Cannot generate accreditation reports

---

## 7.5 Student

| Attribute | Value |
|---|---|
| **Purpose** | Self-service read-only access to own academic data. |
| **Scope Level** | SELF — bounded by student identity linkage |
| **Is System Role** | YES |
| **Data Access** | Own marks, own results, own enrolled curriculum, program POs and COs for enrolled courses |

**Identity linkage:** The `iam.users` record for a student is linked to `assessment.students` via an `iam.users.linked_student_id UUID` column (not yet in DB architecture — should be added). This linkage enables the SELF scope to resolve to the correct student record.

**Owned Permission Groups:** G23 (Student Self-Service only)

**All Permissions:**
- `student.profile.read.own`
- `student.curriculum.read.own`
- `student.course.read.own`
- `student.result.read.own`
- `student.marks.read.own`
- `student.co.read.own`
- `student.po.read.own`

**Key Restrictions:**
- Cannot view other students' data under any circumstance
- Cannot view marks that have not been published
- Cannot access any management, configuration, or approval features
- Student-tier permissions cannot be assigned to any other role

---

# 8. Role–Permission Matrix

## 8.1 By Permission Group

`✓` = Full access (at default scope for this role)
`◑` = Partial or scoped access (see notes)
`✗` = No access

| Permission Group | Super Admin | Program Coordinator | Module Leader | Section Teacher | Student |
|---|---|---|---|---|---|
| **G01 · System Administration** | ✓ | ✗ | ✗ | ✗ | ✗ |
| **G02 · Organization Setup** | ✓ | ✗ | ✗ | ✗ | ✗ |
| **G03 · User Administration** | ✓ | ◑ (read only, within program) | ✗ | ✗ | ✗ |
| **G04 · Reference Data Management** | ✓ | ◑ (read; manage select items) | ✗ | ✗ | ✗ |
| **G05 · Curriculum Authoring** | ✓ | ✓ | ◑ (read only) | ◑ (read only) | ◑ (own curriculum) |
| **G06 · Academic Structure Management** | ✓ | ✓ | ✗ | ✗ | ✗ |
| **G07 · PO Management** | ✓ | ✓ | ◑ (read only) | ◑ (read only) | ◑ (read own) |
| **G08 · CO Authoring** | ✓ | ✓ | ◑ (read + update assigned) | ✓ (assigned courses) | ◑ (read own) |
| **G09 · CO Governance** | ✓ | ✓ | ✓ (assigned only) | ✗ | ✗ |
| **G10 · Mapping Authoring** | ✓ | ✓ | ◑ (read only) | ✓ (assigned courses) | ✗ |
| **G11 · Mapping Governance** | ✓ | ✓ | ✓ (assigned only) | ✗ | ✗ |
| **G12 · Assessment Configuration** | ✓ | ✓ | ◑ (read only) | ◑ (read only) | ✗ |
| **G13 · Marks Entry** | ✓ | ✓ | ◑ (read only) | ✓ (assigned sections) | ✗ |
| **G14 · Marks Oversight** | ✓ | ✓ | ✓ (assigned courses) | ✗ | ✗ |
| **G15 · Result Workflow — Teacher** | ✓ | ✓ | ✗ | ✓ (assigned sections) | ✗ |
| **G16 · Result Workflow — ML** | ✓ | ✓ | ✓ (assigned courses) | ✗ | ✗ |
| **G17 · Result Workflow — Coordinator** | ✓ | ✓ | ✗ | ✗ | ✗ |
| **G18 · Attainment Management** | ✓ | ✓ | ✗ | ✗ | ✗ |
| **G19 · Attainment Read-Only** | ✓ | ✓ | ✓ (assigned courses) | ✓ (assigned courses) | ✗ |
| **G20 · Report Generation** | ✓ | ✓ | ◑ (CO + attainment only) | ◑ (CO + assessment only) | ✗ |
| **G21 · Report Read-Only / Export** | ✓ | ✓ | ✓ (scoped) | ✓ (scoped) | ✗ |
| **G22 · Accreditation Management** | ✓ | ✓ | ✗ | ✗ | ✗ |
| **G23 · Student Self-Service** | ✗ | ✗ | ✗ | ✗ | ✓ |

## 8.2 Critical Permission Detail Matrix

Key individual permissions that require precise cross-role comparison.

| Permission | Super Admin | Program Coordinator | Module Leader | Section Teacher | Student |
|---|---|---|---|---|---|
| `system.roles.create` | ✓ | ✗ | ✗ | ✗ | ✗ |
| `system.audit.read` | ✓ | ✗ | ✗ | ✗ | ✗ |
| `user.create` | ✓ | ✗ | ✗ | ✗ | ✗ |
| `user.role.assign` | ✓ | ✗ | ✗ | ✗ | ✗ |
| `curriculum.create` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `curriculum.version` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `po.create` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `po.archive` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `co.create` | ✓ | ✓ | ✗ | ✓ (assigned) | ✗ |
| `co.submit` | ✓ | ✓ | ✗ | ✓ (assigned) | ✗ |
| `co.approve` | ✓ | ✓ | ✓ (assigned) | ✗ | ✗ |
| `co.publish` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `mapping.co_po.update` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `mapping.co_po.publish` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `mapping.co_cp.manage` | ✓ | ✓ | ✗ | ✓ (assigned) | ✗ |
| `mapping.co_cp.approve` | ✓ | ✓ | ✓ (assigned) | ✗ | ✗ |
| `marks.enter` | ✓ | ✓ | ✗ | ✓ (assigned) | ✗ |
| `marks.read.all` | ✓ | ✓ | ✓ (assigned courses) | ✗ | ✗ |
| `result.submit` | ✓ | ✓ | ✗ | ✓ (assigned) | ✗ |
| `result.approve.ml` | ✓ | ✓ | ✓ (assigned) | ✗ | ✗ |
| `result.approve.pc` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `result.publish` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `result.read.own` | ✗ | ✗ | ✗ | ✗ | ✓ |
| `attainment.configure` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `attainment.publish` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `report.accreditation.generate` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `accreditation.cycle.create` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `student.marks.read.own` | ✗ | ✗ | ✗ | ✗ | ✓ |

## 8.3 Default Role Scope Summary

| Role | Default Scope Level | Scope Assigned By | Further Data Filter |
|---|---|---|---|
| Super Admin | GLOBAL | System initialization | None |
| Program Coordinator | PROGRAM (per assignment) | Super Admin | None |
| Module Leader | PROGRAM (per assignment) | Program Coordinator or Super Admin | `faculty_assignments.role_in_course = 'MODULE_LEADER'` |
| Section Teacher | PROGRAM (per assignment) | Program Coordinator or Super Admin | `faculty_assignments.role_in_course = 'SECTION_TEACHER'` |
| Student | SELF | Auto-assigned on enrollment | `student_enrollments.student_id = self` |

---

# 9. Scope Architecture

## 9.1 Scope Resolution Algorithm

The following algorithm runs on every protected operation. Both gates must pass independently.

```
FUNCTION checkAccess(userId, permissionCode, resourceContext):

  STEP 1 — Load user context from cache
    activeAssignments = cache.get("user:{userId}:assignments")
    IF cache miss:
      activeAssignments = db.query(
        user_role_assignments WHERE user_id = userId AND revoked_at IS NULL
      )
      cache.set("user:{userId}:assignments", activeAssignments, TTL=5min)

  STEP 2 — Permission gate (Gate 1)
    permittedAssignments = []
    FOR EACH assignment IN activeAssignments:
      rolePermissions = cache.get("role:{assignment.role_id}:permissions")
      IF permissionCode IN rolePermissions:
        permittedAssignments.append(assignment)
    
    IF permittedAssignments is empty:
      RETURN DENY (403 — no role grants this permission)

  STEP 3 — Scope gate (Gate 2)
    FOR EACH assignment IN permittedAssignments:
      
      IF assignment.scope_type = GLOBAL:
        RETURN ALLOW
      
      IF assignment.scope_type = DEPARTMENT:
        IF resourceContext.department_id = assignment.scope_id:
          RETURN ALLOW
      
      IF assignment.scope_type = PROGRAM:
        IF resourceContext.program_id = assignment.scope_id:
          
          IF permissionCode requires OFFERING-level check:
            [proceed to Step 4]
          ELSE:
            RETURN ALLOW
    
    RETURN DENY (403 — permission held but scope does not match resource)

  STEP 4 — Assignment gate (Gate 2b, for ML and Teacher operations)
    [Only reached for offering-scoped permissions]
    
    sectionOfferingId = resourceContext.section_offering_id
    
    expectedRole = resolveExpectedFacultyRole(permissionCode)
    [e.g., result.approve.ml → MODULE_LEADER, marks.enter → SECTION_TEACHER]
    
    isAssigned = db.query(
      faculty_assignments
      WHERE user_id = userId
        AND section_offering_id = sectionOfferingId
        AND role_in_course = expectedRole
        AND removed_at IS NULL
    )
    
    IF isAssigned:
      RETURN ALLOW
    ELSE:
      RETURN DENY (403 — not assigned to this offering)

  STEP 5 — Self gate (Gate 2c, for Student operations)
    [Only reached for student.*.own permissions]
    
    linkedStudentId = cache.get("user:{userId}:student_id")
    IF resourceContext.student_id = linkedStudentId:
      RETURN ALLOW
    ELSE:
      RETURN DENY (403 — not own data)
```

## 9.2 Offering-Scoped Permissions

The following permissions trigger the **Assignment Gate (Step 4)**:

| Permission Code | Required `role_in_course` |
|---|---|
| `co.create` | SECTION_TEACHER |
| `co.update` | SECTION_TEACHER or MODULE_LEADER |
| `co.submit` | SECTION_TEACHER |
| `co.approve` | MODULE_LEADER |
| `co.reject` | MODULE_LEADER |
| `mapping.co_cp.manage` | SECTION_TEACHER |
| `mapping.co_ca.manage` | SECTION_TEACHER |
| `mapping.co_kp.manage` | SECTION_TEACHER |
| `mapping.co_cp.approve` | MODULE_LEADER |
| `mapping.co_ca.approve` | MODULE_LEADER |
| `mapping.co_kp.approve` | MODULE_LEADER |
| `marks.enter` | SECTION_TEACHER |
| `marks.update` | SECTION_TEACHER |
| `marks.read.section` | SECTION_TEACHER or MODULE_LEADER |
| `result.submit` | SECTION_TEACHER |
| `result.approve.ml` | MODULE_LEADER |
| `result.reject.ml` | MODULE_LEADER |

**Note:** `co.approve` and `result.approve.ml` both check for MODULE_LEADER faculty assignment, not Program Coordinator. A Program Coordinator can also approve COs but through a different pathway — their PROGRAM scope assignment grants them access without the offering check.

## 9.3 Resource Context Object

Every authorization check receives a resource context. The service layer is responsible for resolving this before calling the authorization function.

```
ResourceContext {
  organization_id: UUID
  department_id: UUID (nullable)
  program_id: UUID (nullable)
  curriculum_id: UUID (nullable)
  course_id: UUID (nullable)
  section_offering_id: UUID (nullable)
  student_id: UUID (nullable)        -- for student-scoped resources
  owner_user_id: UUID (nullable)     -- for CO created_by checks
}
```

The service layer resolves these IDs from the target entity before calling `checkAccess`. For example, when checking whether a user can update a CO, the service first loads the CO to get its `curriculum_id` and `course_id`, then resolves the program from the curriculum, then calls `checkAccess`.

## 9.4 Permission Cache Architecture

```
Cache Keys (Redis):
  user:{userId}:assignments        → List of { role_id, scope_type, scope_id }
  role:{roleId}:permissions        → Set of permission codes
  user:{userId}:student_id         → Linked student UUID (for Student role)
  user:{userId}:manifest           → Full permission manifest (computed, for frontend)

Cache Invalidation Triggers:
  user_role_assignments INSERT      → Invalidate user:{userId}:assignments + manifest
  user_role_assignments revoked_at  → Invalidate user:{userId}:assignments + manifest
  role_permissions INSERT/DELETE    → Invalidate role:{roleId}:permissions
                                      + all user manifests for users with this role
  faculty_assignments changes       → No cache impact (checked live at Gate 2b)

TTL Strategy:
  user assignments cache: 5 minutes  (short, frequently changes)
  role permissions cache: 30 minutes (roles change infrequently)
  user manifest: 5 minutes           (derived, must stay fresh)
```

---

# 10. Access Control Strategy

## 10.1 Three Enforcement Layers

Authorization is enforced at three independent layers. Each layer is a complete check — they do not substitute for each other.

```
REQUEST
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: API GATEWAY / MIDDLEWARE                               │
│                                                                   │
│  • JWT validation (signature, expiry)                            │
│  • Extract user_id and organization_id from JWT claims           │
│  • Check if user is ACTIVE (not deactivated)                     │
│  • Rate limiting (per user, per endpoint)                        │
│                                                                   │
│  Failure: 401 Unauthorized (unauthenticated)                     │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: APPLICATION SERVICE — AUTHORIZATION                    │
│                                                                   │
│  • Check permission (Gate 1): does any role grant this code?     │
│  • Check scope (Gate 2): does the resource belong to user scope? │
│  • Check assignment (Gate 2b): for offering-scoped permissions   │
│  • Check self (Gate 2c): for student self-service permissions    │
│                                                                   │
│  Failure: 403 Forbidden (authenticated but not authorized)       │
│                                                                   │
│  Every 403 is written to audit.audit_events with action=DENIED   │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: DATA LAYER — QUERY FILTERS                             │
│                                                                   │
│  • All queries include scope-based WHERE clauses                 │
│  • Program Coordinator: WHERE program_id IN (:assigned_programs) │
│  • Module Leader/Teacher: WHERE section_offering_id IN (:offers) │
│  • Student: WHERE student_id = :self_student_id                  │
│                                                                   │
│  This layer defends against authorization logic bugs in Layer 2. │
│  Even if Layer 2 incorrectly allows access, the query returns    │
│  no data outside the user's scope.                               │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
RESPONSE
```

## 10.2 API Endpoint Authorization Contract

Every API endpoint declares its authorization requirements as a machine-readable annotation. This annotation is the single source of truth for what permission each endpoint requires.

```
ANNOTATION FORMAT (conceptual, not code):
  @requires(permission="co.approve", resource_context="co_by_id")

This annotation means:
  1. The middleware resolves the resource context using "co_by_id" resolver
     (loads CO from DB → extracts curriculum_id, course_id → resolves program_id)
  2. The authorization service checks permission "co.approve" against that context
  3. If Layer 2 passes, the handler executes
  4. The query in the handler additionally filters by user's scope
```

**Endpoints must never be added without an authorization annotation.** An unannotated endpoint is treated as DENY ALL by the middleware.

## 10.3 Authorization Audit Trail

Every authorization decision — both ALLOW and DENY — is recorded:

| Event | Audit Action | Logged Fields |
|---|---|---|
| Permission check passed | `ACCESS_GRANTED` | user_id, permission_code, resource_type, resource_id, scope used |
| Permission check failed (no permission) | `ACCESS_DENIED_PERMISSION` | user_id, permission_code, resource_type, resource_id |
| Scope check failed | `ACCESS_DENIED_SCOPE` | user_id, permission_code, resource_type, resource_id, user_scope, resource_scope |
| Assignment check failed | `ACCESS_DENIED_ASSIGNMENT` | user_id, permission_code, section_offering_id |
| JWT invalid / expired | `AUTH_FAILURE` | ip_address, user_agent |

DENY events are particularly valuable for security investigations. A pattern of `ACCESS_DENIED_PERMISSION` events for a specific user and resource type may indicate a privilege escalation attempt.

## 10.4 Approval Workflow Authorization

Approval steps carry their own role-specific authorization. The workflow engine checks not just "does this user have `result.approve.ml`" but also "is this user the designated approver for this specific request at the current step."

```
APPROVAL STEP AUTHORIZATION:
  1. Standard permission check (Layer 2)
  2. Retrieve the approval_request for this entity
  3. Check current_step_order and required_role_id for that step
  4. Verify the acting user holds the required role within the resource's scope
  5. Check delegate_approvers if primary approver is unavailable
  6. If all pass → record approval_step_record and advance workflow
```

This prevents a Module Leader from approving their own submitted results at the Teacher step, or approving at the Program Coordinator step (even if they somehow have `result.approve.pc` through a misconfiguration).

---

# 11. UI Visibility Control

## 11.1 Permission Manifest

On successful login, the server computes and returns a **permission manifest**. This is a flat object that the frontend caches for the session duration.

```
Permission Manifest Structure:

{
  "user_id": "uuid",
  "user_name": "Dr. Jane Smith",
  "permissions": [
    "curriculum.read",
    "curriculum.create",
    "curriculum.update",
    "co.create",
    "co.submit",
    ...
  ],
  "scope": {
    "programs": [
      { "id": "uuid-cse", "name": "B.Sc. in CSE", "acronym": "CSE" }
    ],
    "departments": [],
    "is_global": false
  },
  "offering_ids": [
    "uuid-offering-1", "uuid-offering-2"
  ]
}
```

**Rules for the permission manifest:**

- `permissions` is the flat union of all permissions across all the user's active role assignments, without scope info (scope is in the `scope` object separately).
- The manifest never contains role names — only permission codes. The frontend never knows the user's role by name from the manifest.
- `offering_ids` is pre-computed for Module Leaders and Section Teachers — the frontend uses this to pre-filter dropdowns without additional API calls.
- The manifest is recomputed on login and on role assignment changes. Short-lived cache (5 minutes) on the server; the frontend refreshes it on route navigation.

## 11.2 UI Visibility Decision Table

| UI Element | Visibility Condition | Permission Required |
|---|---|---|
| **Navigation: Curriculum** | Visible | `curriculum.read` |
| **Button: New Curriculum** | Visible | `curriculum.create` |
| **Button: Version Curriculum** | Visible | `curriculum.version` |
| **Navigation: Program Outcomes** | Visible | `po.read` |
| **Button: Add PO** | Visible | `po.create` |
| **Navigation: Course Outcomes** | Visible | `co.read` |
| **Button: Create CO** | Visible | `co.create` |
| **Button: Submit CO** | Visible AND CO in DRAFT state | `co.submit` |
| **Button: Approve CO** | Visible AND CO in UNDER_REVIEW state | `co.approve` |
| **Button: Publish CO** | Visible AND CO in APPROVED state | `co.publish` |
| **Navigation: Assessments** | Visible | `assessment.read` |
| **Form: Configure Assessment** | Visible | `assessment.configure` |
| **Form: Enter Marks** | Visible AND assessment in MARKS_OPEN state | `marks.enter` |
| **Button: Submit Results** | Visible | `result.submit` |
| **Button: Approve Results (ML)** | Visible AND result in PENDING_ML state | `result.approve.ml` |
| **Button: Approve Results (PC)** | Visible AND result in PENDING_PC state | `result.approve.pc` |
| **Navigation: Attainment** | Visible | `attainment.read` |
| **Button: Configure Thresholds** | Visible | `attainment.configure` |
| **Button: Initiate Calculation** | Visible | `attainment.initiate` |
| **Button: Publish Attainment** | Visible | `attainment.publish` |
| **Navigation: Reports** | Visible | Any `report.*.generate` |
| **Navigation: Audit Log** | Visible | `system.audit.read` |
| **Navigation: User Management** | Visible | `user.read` |
| **Button: Create User** | Visible | `user.create` |
| **Button: Assign Role** | Visible | `user.role.assign` |
| **Navigation: Accreditation** | Visible | `accreditation.cycle.create` OR `accreditation.report.generate` |
| **Student: My Results** | Visible | `student.result.read.own` |
| **Student: My Curriculum** | Visible | `student.curriculum.read.own` |

## 11.3 Program Selector (Scope-Aware Navigation)

Users with PROGRAM scope (Coordinator, ML, Teacher) see a program selector in the navigation. The selector options are limited to `manifest.scope.programs`.

```
GLOBAL scope user (Super Admin): All programs visible in selector
PROGRAM scope user: Only assigned programs visible in selector
OFFERING scope user: Programs filtered to programs containing their offerings
SELF scope user (Student): No program selector; views own program implicitly
```

The program selector sets an `active_program_id` context that is sent with every API request in a header. The API uses this to further pre-filter responses for better performance.

## 11.4 Field-Level Visibility

Some entities have fields that are only visible to specific roles:

| Entity | Field | Visible To | Hidden From |
|---|---|---|---|
| `student_marks` | `entered_by_user_id` | Coordinator, ML | Student |
| `course_outcomes` | `locked_at`, `created_by_user_id` | Coordinator, ML | Student, Teacher (when others' COs) |
| `attainment_runs` | `co_po_mapping_snapshot`, `assessment_weight_snapshot` | Coordinator | All others |
| `audit_events` | All fields | Super Admin | All others |
| `result_publications` | `ml_rejection_comment`, `pc_rejection_comment` | Coordinator, ML, Teacher (own) | Student |
| `users` | `password_credentials` | Nobody (never exposed via API) | All |

Field-level hiding is enforced at the serialization layer (response DTO construction), not at the database query level.

---

# 12. Special Cases and Edge Rules

## 12.1 Student Identity Linkage

A student who can log into the system has an `iam.users` record (for authentication) and an `assessment.students` record (for academic data). These are linked via `iam.users.linked_student_id`.

**Implication:** When a student authenticates, the permission manifest lookup also resolves `linked_student_id`. All `student.*.own` permission checks use this linked ID as the SELF scope anchor.

**A student user account is NEVER assigned any non-student role.** The system must enforce this at the role assignment layer: if the target user's account is linked to a student record, only `student.*` permissions may be assigned.

## 12.2 Faculty Who Are Also Students

In some institutions, graduate students act as teaching assistants. A person may have both an `iam.users` record linked to a student AND a faculty role. This is handled by:

- One `iam.users` record per person
- Two role assignments on the same user: one Student role + one Section Teacher role
- The permission check logic takes the union of all roles
- Data access is scoped correctly per role: student data via SELF scope, teaching data via OFFERING scope

## 12.3 Program Coordinator Self-Authoring COs

A Program Coordinator technically has `co.create` and `co.submit`. Can they create COs for their own program?

**Rule:** Yes, they can. The Coordinator holds full CO lifecycle permissions. However, if they create a CO, the workflow still requires a Module Leader to approve it (the Coordinator cannot approve their own CO submission through the same role). The approval request records who submitted and who approved — the same user appearing in both fields triggers a business rule warning in the audit log.

**Recommendation:** Configure the approval workflow to require a different user at each step. This is enforced through the `approval.approval_step_records` design — the application checks that the approver at step N is not the same user who submitted or approved step N-1.

## 12.4 Super Admin Bypass

Super Admin holds all domain permissions explicitly. There is no "bypass all checks" flag for Super Admin — they pass through the same three-layer authorization as every other user. This is intentional:

- It ensures Super Admin actions are fully audited through the same code path
- It prevents "super user bypass" vulnerabilities if the bypass condition is ever misapplied
- It makes the authorization code simpler (no special-case branches)

The only practical difference is that Super Admin's GLOBAL scope assignment means every scope check passes without needing to match program or department IDs.

## 12.5 Deactivated Users

When a user is deactivated (`iam.users.status = 'DEACTIVATED'`):

1. All active refresh tokens for that user are immediately revoked (`revoked_at = NOW()`)
2. JWT access tokens remain valid until their natural expiry (typically 15 minutes)
3. On the next API request with a valid JWT, Layer 1 checks user status — deactivated users receive 401

**Open Approval Requests:** If a deactivated user has pending approval requests assigned to them, the system must reassign those to an active delegate or escalate to the Coordinator. This reassignment logic is triggered by the `UserDeactivated` domain event.

## 12.6 Role Assignment with No Matching Scope

If a Program Coordinator is assigned to a program that is later archived:

- The role assignment record remains active
- The archived program's data still passes scope checks (archived data still belongs to the program)
- New creation operations in that program are blocked by the program's ARCHIVED status, not by the scope check
- The coordinator's assignment to an archived program does not grant access to any other program

## 12.7 Concurrent Role Modifications

If a user's role assignments change while they have an active session:

- Their JWT remains valid (no forced logout)
- Their permission manifest cache entry is invalidated immediately
- On the next manifest refresh (navigation or explicit refresh), the new permissions take effect
- In the 5-minute cache window, they may temporarily access permissions they should have lost, or be denied permissions they should have gained

**Mitigation for high-security operations:** For `attainment.publish` and `co.publish`, the application service performs a live (non-cached) permission check, bypassing the manifest cache. This prevents a recently-demoted user from completing an irreversible operation.

---

# 13. Future Scalability Recommendations

## 13.1 Adding a New Resource

When a new resource (e.g., `rubric`) is added to the platform:

**Step 1** — Define the permission codes following the naming convention:
```
rubric.create
rubric.read
rubric.update
rubric.archive
rubric.approve
rubric.publish
```

**Step 2** — Seed these as DOMAIN-tier permissions in `iam.permissions`.

**Step 3** — Assign the new permissions to the appropriate roles by inserting into `role_permissions`.

**Step 4** — Annotate the new API endpoints with the new permission codes.

**Step 5** — Add the new permissions to relevant permission groups (documentation update).

**Zero database migrations needed.** The schema is already designed to hold arbitrary permission codes. Adding a new resource requires only data inserts and application code changes.

## 13.2 Creating a Custom Role

The process for an authorized admin to create a custom role:

```
STEP 1: Admin navigates to Role Management
STEP 2: Admin names the custom role (e.g., "Department Assessment Coordinator")
STEP 3: Admin selects permission groups from the available DOMAIN-tier groups
STEP 4: Admin previews the effective permissions (full list rendered)
STEP 5: Admin confirms — role is created in iam.roles with is_system_role=FALSE
STEP 6: Admin assigns the role to a user with an appropriate scope
STEP 7: All steps are written to audit.audit_events
```

**Guardrails on custom role creation:**
- Cannot include SYSTEM-tier or STUDENT-tier permissions
- Cannot be named identically to an existing system role
- Requires `system.roles.create` permission (Super Admin only in v1)
- The role is annotated with created_by and created_at for audit trail

**Recommended expansion in v2:** Allow Program Coordinators to create custom roles within their program scope (with a ceiling that prevents them from granting more permissions than they themselves hold — the "can't grant what you don't have" rule).

## 13.3 Multi-Department Coordinator Role

For institutions where one person coordinates across departments:

**Current support:** A user can have multiple DEPARTMENT-scope role assignments. Each assignment grants the role's permissions within one department. The union of all assignments is the effective scope.

**No schema change needed.** The `user_role_assignments` table supports multiple active records per user already.

## 13.4 Multi-University (Multi-Tenant) RBAC Extension

When the platform expands to multi-university deployment:

**SYSTEM-tier permissions** remain global (platform admin across all universities).

**DOMAIN-tier permissions** gain an implicit ORGANIZATION scope — users of University A cannot see University B's data even if they hold identical permissions. The `organization_id` column on all tables + RLS enforces this.

**Cross-university roles** (e.g., a platform admin who manages two universities) use GLOBAL scope assignments with their organization_id set to NULL — indicating cross-organization authority. This is a new scope_type: `CROSS_ORG`.

**Impact on current design:** Zero. The `scope_type` column in `user_role_assignments` can add `CROSS_ORG` as a new enum value. All existing scope checks remain valid. Only Super Admins receive GLOBAL scope, and only platform-level administrators would receive CROSS_ORG scope.

## 13.5 Attribute-Based Access Control (ABAC) Extension

The current RBAC model may need to evolve toward ABAC for certain nuanced rules:

**Example scenarios that RBAC cannot elegantly handle:**
- "A teacher can only enter marks for assessments that are in MARKS_OPEN status"
- "A coordinator can only approve attainment if the result_publication status is PUBLISHED"
- "A module leader can only approve a CO if its Bloom level matches their designated domain"

These are **state-based access rules**, not role-based rules. In the current design, they are enforced by the application service layer as business rule checks, not by the RBAC layer.

**Recommended extension:** Add a `policy_engine` abstraction layer between the permission check and the business logic execution. The policy engine evaluates rules expressed as: `{role} CAN {action} {resource} WHEN {resource.field} = {value}`. This is lightweight ABAC without requiring a full-blown OPA or Casbin integration.

## 13.6 Permission Delegation (Future)

Currently, permissions cannot be delegated (a coordinator cannot temporarily grant a subset of their permissions to a teacher). This is intentional for v1 — delegation chains are complex to audit and easy to misuse.

**For v2:** Introduce a bounded delegation model:
- A user can delegate specific permissions to another user
- The delegation has a validity window (`valid_from`, `valid_to`)
- The delegated permissions are a strict subset of the delegator's own permissions (no escalation)
- Delegation is recorded in a `permission_delegations` table (separate from `user_role_assignments`)
- All actions taken under a delegation are flagged in the audit log with `delegator_user_id`

This covers the use case of a coordinator delegating report generation rights to an assistant during a busy accreditation period without granting full coordinator access.

## 13.7 Permission Auditing Maturity Levels

The platform should evolve through three RBAC audit maturity levels:

| Level | What is Audited | Current Status |
|---|---|---|
| **L1 — Action Auditing** | Who did what, when, on which entity | ✓ Designed in v1 |
| **L2 — Authorization Auditing** | Why was it allowed (which permission, which scope) | ✓ Designed in v1 |
| **L3 — Anomaly Detection** | Unusual access patterns (off-hours, bulk exports, privilege abuse) | Planned for v2 |

L3 requires analyzing the `audit.audit_events` stream for anomalies — a job for a background analytics process or an external SIEM integration, not the RBAC system itself.

---

*End of RBAC Authorization Architecture Document — OBE Accreditation Management Platform v1.0*
