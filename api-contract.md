# OBE Accreditation Management Platform
## API Contract — v1.0

> **Base URL:** `/api/v1`  
> **Auth:** All endpoints require `Authorization: Bearer <access_token>` unless marked **Public**  
> **Scope:** All responses are automatically filtered to the user's assigned scope  
> **Errors:** All errors return `{ code, message, details? }`  
> **Pagination:** List endpoints accept `?page=1&size=20`; return `{ items[], total, page, size }`

---

## Module 1 — Auth & IAM

### Authentication

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| POST | `/auth/login` | Public | — | Authenticate; returns access + refresh token |
| POST | `/auth/refresh` | Cookie | — | Rotate refresh token; returns new access token |
| POST | `/auth/logout` | JWT | — | Revoke refresh token |
| POST | `/auth/password-reset-request` | Public | — | Send password reset email |
| POST | `/auth/password-reset-confirm` | Public | — | Set new password using reset token |

**POST /auth/login**
```
Request:  { email: string, password: string }
Response: { access_token: string, token_type: "bearer", expires_in: 900 }
Cookie:   Set-Cookie: refresh_token=<value>; HttpOnly; Secure; SameSite=Strict
Errors:   401 (invalid credentials), 422 (validation)
```

**POST /auth/refresh**
```
Request:  Cookie: refresh_token=<value>
Response: { access_token: string, token_type: "bearer", expires_in: 900 }
Cookie:   Set-Cookie: refresh_token=<new_value>; HttpOnly; Secure
Errors:   401 (invalid/expired/revoked token)
```

---

### Permission Manifest

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/me` | JWT | — | Current user profile + permission manifest |
| GET | `/me/permissions` | JWT | — | Flat permission manifest only |

**GET /me**
```
Response: {
  id, email, first_name, last_name, faculty_type, title, designation,
  department: { id, name },
  permissions: string[],
  scope: { programs: [{ id, name, acronym }], is_global: bool },
  offering_ids: string[]
}
```

---

### Users

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/users` | JWT | `user.read` | List users (scoped by org/program) |
| POST | `/users` | JWT | `user.create` | Create faculty/staff user |
| GET | `/users/{id}` | JWT | `user.read` | Get user detail |
| PATCH | `/users/{id}` | JWT | `user.update` | Update user information |
| POST | `/users/{id}/deactivate` | JWT | `user.deactivate` | Deactivate user account |
| POST | `/users/{id}/reactivate` | JWT | `user.deactivate` | Reactivate user account |
| POST | `/users/{id}/reset-password` | JWT | `user.password.reset` | Reset user password |
| GET | `/users/{id}/roles` | JWT | `user.read` | List user's role assignments |
| POST | `/users/{id}/roles` | JWT | `user.role.assign` | Assign role to user |
| DELETE | `/users/{id}/roles/{assignment_id}` | JWT | `user.role.revoke` | Revoke role assignment |

**POST /users (Create User)**
```
Request: {
  first_name: string, last_name: string, email: string,
  faculty_type: "PERMANENT"|"ADJUNCT"|"VISITING"|"CONTRACTUAL",
  title?: string, contact_number?: string,
  department_id?: uuid, designation?: string,
  password_option: "MANUAL"|"AUTO_GENERATE",
  password?: string  (required if MANUAL)
}
Response: { id, email, first_name, last_name, status, created_at }
Errors: 409 (email already exists), 422 (validation)
```

**POST /users/{id}/roles (Assign Role)**
```
Request: { role_id: uuid, scope_type: "GLOBAL"|"DEPARTMENT"|"PROGRAM", scope_id?: uuid }
Response: { id, user_id, role_id, scope_type, scope_id, assigned_at }
Errors: 404 (user/role not found), 409 (already assigned)
```

---

### Roles & Permissions

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/roles` | JWT | `user.read` | List all active roles |
| POST | `/roles` | JWT | `system.roles.create` | Create custom role |
| GET | `/roles/{id}` | JWT | `user.read` | Get role with its permissions |
| PATCH | `/roles/{id}` | JWT | `system.roles.create` | Update role name/description |
| DELETE | `/roles/{id}` | JWT | `system.roles.delete` | Delete non-system role |
| GET | `/roles/{id}/permissions` | JWT | `user.read` | List permissions in role |
| POST | `/roles/{id}/permissions` | JWT | `system.permissions.grant` | Grant permission to role |
| DELETE | `/roles/{id}/permissions/{permission_id}` | JWT | `system.permissions.revoke` | Revoke permission from role |
| GET | `/permissions` | JWT | `user.read` | List all available permissions |

---

## Module 2 — Organization

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/organization` | JWT | — | Get organization details |
| PATCH | `/organization` | JWT | `system.organization.configure` | Update organization settings |
| POST | `/organization/logo` | JWT | `system.organization.configure` | Get upload URL for logo |

**PATCH /organization**
```
Request: {
  name?, short_name?, description?, vision?, mission?,
  website?, address_street?, address_city?, address_country?,
  contact_email?, contact_phone?, email_validation_regex?
}
Response: Full organization object
```

---

### Departments

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/departments` | JWT | `department.read` | List departments |
| POST | `/departments` | JWT | `department.create` | Create department |
| GET | `/departments/{id}` | JWT | `department.read` | Get department detail |
| PATCH | `/departments/{id}` | JWT | `department.update` | Update department |
| POST | `/departments/{id}/archive` | JWT | `department.archive` | Archive department |
| GET | `/departments/{id}/head-history` | JWT | `department.read` | HOD history |
| POST | `/departments/{id}/head` | JWT | `department.head.assign` | Assign new HOD |

---

### Programs

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/programs` | JWT | `program.read` | List programs |
| POST | `/programs` | JWT | `program.create` | Create program |
| GET | `/programs/{id}` | JWT | `program.read` | Get program detail |
| PATCH | `/programs/{id}` | JWT | `program.update` | Update program |
| POST | `/programs/{id}/archive` | JWT | `program.archive` | Archive program |

---

## Module 3 — Reference Data

All reference data endpoints follow the same pattern. `{type}` = `bloom-domains`, `bloom-levels`, `delivery-methods`, `course-types`, `assessment-types`, `complex-problems`, `complex-activities`, `knowledge-profiles`, `mapping-weights`

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/ref-data/{type}` | JWT | — | List active reference items |
| POST | `/ref-data/{type}` | JWT | `config.{type}.manage` | Create item |
| PATCH | `/ref-data/{type}/{id}` | JWT | `config.{type}.manage` | Update item |
| POST | `/ref-data/{type}/{id}/deactivate` | JWT | `config.{type}.manage` | Deactivate item |

**GET /ref-data/bloom-levels** (example)
```
Query: ?bloom_domain_id=uuid (optional filter)
Response: { items: [{ id, code, name, order_index, bloom_domain: { id, name } }] }
Cache-Control: max-age=3600
ETag: <hash_of_updated_at>
```

---

## Module 4 — Curriculum

### Curricula

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/curricula` | JWT | `curriculum.read` | List curricula (program-scoped) |
| POST | `/curricula` | JWT | `curriculum.create` | Create curriculum |
| GET | `/curricula/{id}` | JWT | `curriculum.read` | Get full curriculum structure |
| PATCH | `/curricula/{id}` | JWT | `curriculum.update` | Update curriculum metadata |
| POST | `/curricula/{id}/activate` | JWT | `curriculum.update` | Set status to ACTIVE |
| POST | `/curricula/{id}/version` | JWT | `curriculum.version` | Create new version from this curriculum |
| POST | `/curricula/{id}/archive` | JWT | `curriculum.archive` | Archive curriculum |

**GET /curricula/{id}**
```
Response: {
  id, name, code, effective_year, version_number, status, program: { id, title, acronym },
  parent_curriculum_id?,
  terms: [{
    id, term_number, name, total_credit_hours,
    courses: [{ slot_id, is_elective, course: { id, code, title, credits } }]
  }]
}
```

**POST /curricula/{id}/version**
```
Request:  { effective_year: number, code: string }
Response: { id, version_number, status: "DRAFT", parent_curriculum_id }
Note:     New curriculum inherits term/course structure; COs are NOT copied (start fresh)
```

### Curriculum Term Definitions

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| POST | `/curricula/{id}/terms` | JWT | `curriculum.update` | Add term slot |
| PATCH | `/curricula/{id}/terms/{term_id}` | JWT | `curriculum.update` | Update term |
| POST | `/curricula/{id}/terms/{term_id}/courses` | JWT | `curriculum.update` | Place course in term |
| DELETE | `/curricula/{id}/terms/{term_id}/courses/{slot_id}` | JWT | `curriculum.update` | Remove course from term |

---

### Courses

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/courses` | JWT | `course.read` | List courses |
| POST | `/courses` | JWT | `course.create` | Create course |
| GET | `/courses/{id}` | JWT | `course.read` | Get course detail |
| PATCH | `/courses/{id}` | JWT | `course.update` | Update course |
| POST | `/courses/{id}/archive` | JWT | `course.archive` | Archive course |
| GET | `/courses/{id}/prerequisites` | JWT | `course.read` | Get prerequisites |
| POST | `/courses/{id}/prerequisites` | JWT | `course.prerequisite.manage` | Add prerequisite |
| DELETE | `/courses/{id}/prerequisites/{prereq_id}` | JWT | `course.prerequisite.manage` | Remove prerequisite |

**POST /courses/{id}/prerequisites**
```
Request:  { prerequisite_course_id: uuid }
Response: { id, course_id, prerequisite_course: { id, code, title } }
Errors:   409 (cycle detected), 409 (already exists), 422
```

---

### Batches

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/batches` | JWT | `batch.read` | List batches |
| POST | `/batches` | JWT | `batch.create` | Create batch |
| GET | `/batches/{id}` | JWT | `batch.read` | Get batch detail |
| PATCH | `/batches/{id}` | JWT | `batch.update` | Update batch |

---

### Academic Terms & Sections

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/academic-terms` | JWT | `curriculum.read` | List academic terms |
| POST | `/academic-terms` | JWT | `academic_term.create` | Create academic term |
| PATCH | `/academic-terms/{id}` | JWT | `academic_term.update` | Update term |
| GET | `/sections` | JWT | `curriculum.read` | List sections |
| POST | `/sections` | JWT | `section.create` | Create section |

---

### Section Offerings

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/section-offerings` | JWT | `curriculum.read` | List offerings (scoped) |
| POST | `/section-offerings` | JWT | `section_offering.create` | Create offering |
| GET | `/section-offerings/{id}` | JWT | `curriculum.read` | Get offering detail |
| PATCH | `/section-offerings/{id}` | JWT | `section_offering.update` | Update status |
| GET | `/section-offerings/{id}/faculty` | JWT | `curriculum.read` | List assigned faculty |
| POST | `/section-offerings/{id}/faculty` | JWT | `faculty_assignment.create` | Assign faculty |
| DELETE | `/section-offerings/{id}/faculty/{assignment_id}` | JWT | `faculty_assignment.update` | Remove faculty |

**GET /section-offerings (key query params)**
```
?batch_id=uuid&academic_term_id=uuid&course_id=uuid&status=ACTIVE
Response items include: { id, course, batch, academic_term, section, status, faculty: [] }
```

---

## Module 5 — OBE

### Program Outcomes

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/program-outcomes` | JWT | `po.read` | List POs for program |
| POST | `/program-outcomes` | JWT | `po.create` | Create PO |
| GET | `/program-outcomes/{id}` | JWT | `po.read` | Get PO detail |
| PATCH | `/program-outcomes/{id}` | JWT | `po.update` | Update PO |
| POST | `/program-outcomes/{id}/archive` | JWT | `po.archive` | Archive PO (guarded by BR-02) |
| POST | `/program-outcomes/{id}/knowledge-profiles` | JWT | `po.update` | Link KP to PO |
| DELETE | `/program-outcomes/{id}/knowledge-profiles/{kp_id}` | JWT | `po.update` | Remove KP from PO |

**GET /program-outcomes (key params)**
```
?program_id=uuid (required), ?status=ACTIVE
Response items: { id, code, statement, po_type, bloom_domain, order_index, knowledge_profiles: [] }
```

**POST /program-outcomes/{id}/archive**
```
Response: 204 No Content
Errors:   409 (PO referenced by published CO-PO mapping — BR-02 violation)
```

---

### Course Outcomes

| Method | Path | Auth | Permission | Scope Gate | Description |
|---|---|---|---|---|---|
| GET | `/course-outcomes` | JWT | `co.read` | Program | List COs |
| POST | `/course-outcomes` | JWT | `co.create` | Offering (Teacher) | Create CO in Draft |
| GET | `/course-outcomes/{id}` | JWT | `co.read` | Program | Get CO detail |
| PATCH | `/course-outcomes/{id}` | JWT | `co.update` | Offering (Teacher/ML) | Update CO (Draft only) |
| POST | `/course-outcomes/{id}/submit` | JWT | `co.submit` | Offering (Teacher) | Submit for approval |
| POST | `/course-outcomes/{id}/approve` | JWT | `co.approve` | Offering (ML) or Program (PC) | Approve CO |
| POST | `/course-outcomes/{id}/reject` | JWT | `co.reject` | Offering (ML) or Program (PC) | Reject; returns to Draft |
| POST | `/course-outcomes/{id}/publish` | JWT | `co.publish` | Program (PC only) | Publish CO |
| GET | `/course-outcomes/{id}/delivery-methods` | JWT | `co.read` | Program | List CO delivery methods |
| POST | `/course-outcomes/{id}/delivery-methods` | JWT | `co.update` | Offering (Teacher) | Add delivery method |
| DELETE | `/course-outcomes/{id}/delivery-methods/{dm_id}` | JWT | `co.update` | Offering (Teacher) | Remove delivery method |

**POST /course-outcomes**
```
Request: {
  curriculum_id: uuid, course_id: uuid,
  code: string, statement: string, bloom_level_id: uuid
}
Response: { id, code, statement, status: "DRAFT", curriculum_id, course_id, bloom_level }
Errors:   409 (CO code exists for this curriculum+course), 403 (not assigned to offering)
```

**POST /course-outcomes/{id}/approve**
```
Request:  { comments?: string }
Response: { id, status: "APPROVED", approval_request: { id, current_step_order } }
Errors:   409 (CO not in SUBMITTED/UNDER_REVIEW status), 403 (scope gate failed)
```

**GET /course-outcomes (key params)**
```
?curriculum_id=uuid&course_id=uuid&status=PUBLISHED
Response items: {
  id, code, statement, status, bloom_level,
  delivery_methods: [], locked_at?,
  approval_request?: { id, status, current_step_order }
}
```

---

### CO Mappings

#### CO-PO Mapping

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/mappings/co-po` | JWT | `mapping.co_po.read` | List mapping sets |
| POST | `/mappings/co-po` | JWT | `mapping.co_po.create` | Create mapping set for course |
| GET | `/mappings/co-po/{id}` | JWT | `mapping.co_po.read` | Get mapping matrix |
| PUT | `/mappings/co-po/{id}/entries` | JWT | `mapping.co_po.update` | Replace all mapping entries |
| PATCH | `/mappings/co-po/{id}/entries` | JWT | `mapping.co_po.update` | Update specific entries |
| POST | `/mappings/co-po/{id}/publish` | JWT | `mapping.co_po.publish` | Publish matrix (locks entries) |

**GET /mappings/co-po/{id}**
```
Response: {
  id, curriculum_id, course_id, status,
  matrix: [
    {
      co: { id, code, statement },
      mappings: [
        { po: { id, code }, weight: 1|2|3|null }
      ]
    }
  ]
}
```

**PUT /mappings/co-po/{id}/entries**
```
Request: {
  entries: [
    { course_outcome_id: uuid, program_outcome_id: uuid, weight: 1|2|3 }
  ]
}
Note: Replaces all existing entries. Weight must be 1, 2, or 3. Omit entry = no mapping.
Errors: 409 (mapping set is PUBLISHED — read-only)
```

#### CO-CP, CO-CA, CO-KP Mappings

| Method | Path | Auth | Permission | Scope Gate | Description |
|---|---|---|---|---|---|
| GET | `/mappings/co-cp` | JWT | `co.read` | Program | List CO-CP links |
| POST | `/mappings/co-cp` | JWT | `mapping.co_cp.manage` | Offering (Teacher) | Create CO-CP link |
| DELETE | `/mappings/co-cp/{id}` | JWT | `mapping.co_cp.manage` | Offering (Teacher) | Remove CO-CP link |
| POST | `/mappings/co-cp/{id}/approve` | JWT | `mapping.co_cp.approve` | Offering (ML)/Program (PC) | Approve CO-CP link |

*(Same pattern for `/mappings/co-ca` and `/mappings/co-kp`)*

---

## Module 6 — Assessment

### Students

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/students` | JWT | `user.read` | List students (program-scoped) |
| POST | `/students` | JWT | `user.create` | Create student record |
| GET | `/students/{id}` | JWT | `user.read` | Get student detail |
| PATCH | `/students/{id}` | JWT | `user.update` | Update student |
| GET | `/students/{id}/enrollments` | JWT | `user.read` | List student's enrollments |
| POST | `/enrollments` | JWT | `section_offering.update` | Enroll student in section offering |
| DELETE | `/enrollments/{id}` | JWT | `section_offering.update` | Drop enrollment |

---

### Assessments

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/assessments` | JWT | `assessment.read` | List assessments for offering |
| POST | `/assessments` | JWT | `assessment.configure` | Create assessment |
| GET | `/assessments/{id}` | JWT | `assessment.read` | Get assessment detail |
| PATCH | `/assessments/{id}` | JWT | `assessment.configure` | Update assessment (CONFIGURED only) |
| DELETE | `/assessments/{id}` | JWT | `assessment.configure` | Delete assessment (CONFIGURED only) |
| GET | `/assessments/{id}/co-weights` | JWT | `assessment.read` | List CO weight mappings |
| POST | `/assessments/{id}/co-weights` | JWT | `assessment.configure` | Add CO weight |
| PUT | `/assessments/{id}/co-weights` | JWT | `assessment.configure` | Replace all CO weights |
| POST | `/assessments/{id}/open-marks` | JWT | `assessment.publish_config` | Set status to MARKS_OPEN |

**POST /assessments**
```
Request: {
  section_offering_id: uuid, assessment_type_id: uuid,
  name: string, total_marks: number, weightage_percent: number
}
Response: { id, name, total_marks, weightage_percent, status: "CONFIGURED" }
Errors:   422 (weightage would exceed 100% for this offering)
```

**PUT /assessments/{id}/co-weights**
```
Request: {
  weights: [
    { course_outcome_id: uuid, contribution_percent: number }
  ]
}
Note: CO must be PUBLISHED. Sum of contribution_percent validated at application layer.
```

---

### Marks

| Method | Path | Auth | Permission | Scope Gate | Description |
|---|---|---|---|---|---|
| GET | `/marks` | JWT | `marks.read.section` or `marks.read.all` | Offering | List marks |
| POST | `/marks/bulk` | JWT | `marks.enter` | Offering (Teacher) | Bulk enter marks |
| PATCH | `/marks/{id}` | JWT | `marks.update` | Offering (Teacher) | Update single mark |
| GET | `/marks/by-assessment/{assessment_id}` | JWT | `marks.read.section` | Offering | All marks for assessment |

**POST /marks/bulk**
```
Request: {
  assessment_id: uuid,
  marks: [
    { student_enrollment_id: uuid, marks_obtained: number|null, is_absent: boolean }
  ]
}
Response: { created: number, updated: number, errors: [] }
Errors:   409 (assessment not in MARKS_OPEN status), 403 (offering gate)
```

---

### Result Publication

| Method | Path | Auth | Permission | Scope Gate | Description |
|---|---|---|---|---|---|
| GET | `/results/{offering_id}` | JWT | `result.read.section` | Offering | Get result publication status |
| POST | `/results/{offering_id}/submit` | JWT | `result.submit` | Offering (Teacher) | Submit for ML approval |
| POST | `/results/{offering_id}/approve-ml` | JWT | `result.approve.ml` | Offering (ML) | ML approval step |
| POST | `/results/{offering_id}/reject-ml` | JWT | `result.reject.ml` | Offering (ML) | ML rejection; returns to DRAFT |
| POST | `/results/{offering_id}/approve-pc` | JWT | `result.approve.pc` | Program (PC) | PC approval step |
| POST | `/results/{offering_id}/reject-pc` | JWT | `result.reject.pc` | Program (PC) | PC rejection; returns to DRAFT |
| POST | `/results/{offering_id}/publish` | JWT | `result.publish` | Program (PC) | Publish results (irreversible) |

**POST /results/{offering_id}/reject-ml**
```
Request:  { comment: string (required) }
Response: { id, status: "DRAFT", ml_rejection_comment }
Effect:   result_publications.status = DRAFT; teacher notified via notification
```

**POST /results/{offering_id}/publish (HIGH-SECURITY)**
```
Request:  {} (no body required)
Response: { id, status: "PUBLISHED", published_at }
Effect:   student_marks become READ-ONLY; students notified
Auth:     Live (non-cached) permission check performed
Errors:   409 (status not PC_APPROVED)
```

---

## Module 7 — Attainment

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/attainment/config/{offering_id}` | JWT | `attainment.read` | Get threshold config |
| POST | `/attainment/config` | JWT | `attainment.configure` | Create/update threshold config |
| GET | `/attainment/runs` | JWT | `attainment.read` | List runs for offering |
| POST | `/attainment/runs` | JWT | `attainment.initiate` | Initiate new run (async) |
| GET | `/attainment/runs/{id}` | JWT | `attainment.read` | Get run + results |
| POST | `/attainment/runs/{id}/publish` | JWT | `attainment.publish` | Publish run (irreversible) |
| GET | `/attainment/trend/po` | JWT | `attainment.read` | PO attainment trend (cross-run) |
| GET | `/attainment/trend/co` | JWT | `attainment.read` | CO attainment trend (cross-run) |

**POST /attainment/config**
```
Request: {
  section_offering_id: uuid,
  co_threshold_percent: number, course_threshold_percent: number,
  po_threshold_percent: number,
  direct_method_weight: number (default 100),
  indirect_method_weight: number (default 0)
}
Validation: direct + indirect must = 100
```

**POST /attainment/runs**
```
Request:  { section_offering_id: uuid }
Response: { run_id: uuid, status: "INITIATED", message: "Calculation queued" }
Note:     Async — poll GET /attainment/runs/{id} for status
Errors:   409 (no attainment config), 409 (results not published)
```

**GET /attainment/runs/{id}**
```
Response: {
  id, status, run_number, formula_type,
  initiated_at, calculated_at?, published_at?,
  co_results: [{ co: { id, code }, attainment_percent, students_attained, is_threshold_met }],
  course_result: { attainment_percent, is_threshold_met },
  po_results: [{ po: { id, code }, attainment_percent, weighted_co_contribution, is_threshold_met }]
}
```

**GET /attainment/trend/po (key params)**
```
?program_id=uuid&po_id=uuid (optional)&from_year=2024&to_year=2026
Response: [
  {
    po: { id, code, statement },
    data_points: [{ academic_term: string, attainment_percent: number, is_threshold_met: boolean }]
  }
]
```

---

## Module 8 — Approval

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/approvals/inbox` | JWT | — | Pending approvals for current user |
| GET | `/approvals/requests` | JWT | — | All requests (initiated by or assigned to user) |
| GET | `/approvals/requests/{id}` | JWT | — | Get request detail with step history |
| POST | `/approvals/requests/{id}/act` | JWT | — | Approve / reject / request revision |
| GET | `/approvals/delegates` | JWT | — | List active delegations |
| POST | `/approvals/delegates` | JWT | — | Create delegation |
| DELETE | `/approvals/delegates/{id}` | JWT | — | Remove delegation |

**POST /approvals/requests/{id}/act**
```
Request:  { action: "APPROVED"|"REJECTED"|"REVISION_REQUESTED", comments?: string }
Response: { id, status, current_step_order, completed_at? }
Note:     Actioning user must be the designated approver for the current step
```

---

## Module 9 — Notifications

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/notifications` | JWT | — | In-app inbox (paginated) |
| GET | `/notifications/unread-count` | JWT | — | Count of unread notifications |
| PATCH | `/notifications/{id}/read` | JWT | — | Mark single notification as read |
| POST | `/notifications/read-all` | JWT | — | Mark all as read |
| GET | `/notification-templates` | JWT | `system.organization.configure` | List templates |
| PATCH | `/notification-templates/{id}` | JWT | `system.organization.configure` | Update template |

**GET /notifications**
```
Query: ?is_read=false&page=1&size=20
Response items: {
  id, title, body, entity_type?, entity_id?, is_read, read_at?, created_at
}
```

---

## Module 10 — Audit

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/audit` | JWT | `system.audit.read` | Query audit log |
| GET | `/audit/{entity_type}/{entity_id}` | JWT | `system.audit.read` | Entity change history |

**GET /audit (key params)**
```
?entity_type=course_outcomes&entity_id=uuid
&actor_user_id=uuid&action=PUBLISH
&from=2026-01-01T00:00:00Z&to=2026-06-01T00:00:00Z
&page=1&size=50

Response items: {
  id, action, entity_type, entity_id, entity_display_name,
  actor_email, actor_role_snapshot,
  old_value?: object, new_value?: object,
  ip_address?, occurred_at
}
```

---

## Module 11 — Accreditation

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/accreditation/bodies` | JWT | `accreditation.body.manage` | List accreditation bodies |
| POST | `/accreditation/bodies` | JWT | `accreditation.body.manage` | Create body |
| PATCH | `/accreditation/bodies/{id}` | JWT | `accreditation.body.manage` | Update body |
| GET | `/accreditation/cycles` | JWT | `accreditation.cycle.manage` | List cycles |
| POST | `/accreditation/cycles` | JWT | `accreditation.cycle.create` | Create cycle |
| GET | `/accreditation/cycles/{id}` | JWT | `accreditation.cycle.manage` | Get cycle detail |
| PATCH | `/accreditation/cycles/{id}` | JWT | `accreditation.cycle.manage` | Update cycle status |
| GET | `/accreditation/cycles/{id}/reports` | JWT | `accreditation.report.generate` | List generated reports |
| POST | `/accreditation/cycles/{id}/reports` | JWT | `accreditation.report.generate` | Generate report (async) |

---

## Module 12 — Reporting

| Method | Path | Auth | Permission | Description |
|---|---|---|---|---|
| GET | `/reports/definitions` | JWT | — | List available report types |
| POST | `/reports/runs` | JWT | `report.{category}.generate` | Request report generation (async) |
| GET | `/reports/runs` | JWT | — | List user's report run history |
| GET | `/reports/runs/{id}` | JWT | — | Poll run status |
| GET | `/reports/runs/{id}/download` | JWT | — | Get pre-signed download URL |

**POST /reports/runs**
```
Request: {
  report_definition_id: uuid,
  parameters: {
    program_id?: uuid, batch_id?: uuid,
    academic_term_id?: uuid, curriculum_id?: uuid,
    from_date?: date, to_date?: date
  },
  export_format: "PDF"|"EXCEL"|"CSV"
}
Response: { run_id: uuid, status: "QUEUED" }
Note:     Poll GET /reports/runs/{run_id} until status = COMPLETED or FAILED
```

**GET /reports/runs/{id}/download**
```
Response: { download_url: string, expires_at: datetime }
Note:     URL is pre-signed MinIO URL, valid 15 minutes
Errors:   404 (run not found), 409 (status not COMPLETED), 403 (not owner or admin)
```

---

## Standard Error Responses

| HTTP Code | When Used |
|---|---|
| 400 | Malformed request (JSON parse error) |
| 401 | Missing, invalid, or expired JWT |
| 403 | Valid JWT but permission check failed |
| 404 | Entity not found (or not within scope) |
| 409 | Business rule violation (state conflict, duplicate, constraint) |
| 422 | Validation error (field-level; returns `errors[]` array) |
| 500 | Internal server error (logged, never exposes internals) |

**Error Response Shape**
```json
{
  "code": "PERMISSION_DENIED",
  "message": "You do not have permission to perform this action",
  "details": {
    "required_permission": "co.approve",
    "user_id": "uuid"
  }
}
```

**Business Rule Error Example**
```json
{
  "code": "BUSINESS_RULE_VIOLATION",
  "message": "Program Outcome cannot be archived while referenced by active CO-PO mappings",
  "details": {
    "rule_id": "BR-02",
    "blocking_mapping_ids": ["uuid1", "uuid2"]
  }
}
```

---

## Health Endpoints (No Auth)

| Method | Path | Description |
|---|---|---|
| GET | `/health/live` | Liveness probe — always 200 if process is running |
| GET | `/health/ready` | Readiness probe — checks DB, Redis, MinIO |
| GET | `/health/info` | Version, uptime, environment |

```
GET /health/ready
200: { status: "ready", checks: { db: "ok", redis: "ok", minio: "ok" }, uptime_seconds: 3600 }
503: { status: "degraded", checks: { db: "ok", redis: "FAILED", minio: "ok" } }
```
