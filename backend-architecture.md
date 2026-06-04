# OBE Accreditation Management Platform
## Backend Architecture Document v1.0

> **Stack:** FastAPI · PostgreSQL · SQLAlchemy 2.0 · Alembic · Redis · MinIO · Docker  
> **Based on:** FRD v1.0 · DDD Analysis v1.0 · DB Architecture v1.0 · RBAC Architecture v1.0  
> **Date:** 2026-06-04  
> No code generated. Architecture only.

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Module Structure](#2-module-structure)
3. [Service Layer Architecture](#3-service-layer-architecture)
4. [Repository Architecture](#4-repository-architecture)
5. [Authentication Architecture](#5-authentication-architecture)
6. [Authorization Architecture](#6-authorization-architecture)
7. [Event Architecture](#7-event-architecture)
8. [Caching Strategy](#8-caching-strategy)
9. [File Management Architecture](#9-file-management-architecture)
10. [Background Job Architecture](#10-background-job-architecture)
11. [Notification Architecture](#11-notification-architecture)
12. [Deployment Architecture](#12-deployment-architecture)

---

# 1. Project Structure

## 1.1 Repository Root

```
obelytics-backend/
│
├── app/                         ← FastAPI application package
│   ├── main.py                  ← App factory, lifespan, middleware registration
│   ├── api_router.py            ← Central router: includes all module routers
│   │
│   ├── core/                    ← Framework-level cross-cutting concerns
│   ├── shared/                  ← Shared kernel: base classes, events, schemas
│   ├── modules/                 ← One directory per DDD bounded context
│   └── workers/                 ← ARQ background job workers
│
├── migrations/                  ← Alembic migration scripts
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docker/
│   ├── Dockerfile               ← API container image
│   ├── Dockerfile.worker        ← Worker container image
│   ├── docker-compose.yml       ← Development environment
│   ├── docker-compose.prod.yml  ← Production overrides
│   └── nginx/
│       └── nginx.conf
│
├── scripts/
│   ├── seed_reference_data.py   ← Seeds config tables (bloom levels, etc.)
│   ├── create_superadmin.py     ← First-run admin bootstrapping
│   └── health_check.sh          ← Pre-deployment health validation
│
├── .env.example
├── pyproject.toml               ← Dependencies via Poetry
└── alembic.ini
```

## 1.2 Core Directory

```
app/core/
├── config.py                    ← Pydantic BaseSettings; reads from .env
├── database.py                  ← Async engine, session factory, connection pool
├── redis_client.py              ← Async Redis connection pool
├── minio_client.py              ← MinIO client initialization
├── security.py                  ← JWT encode/decode, bcrypt hashing
├── dependencies.py              ← Shared FastAPI Depends: db session, current user
├── exceptions.py                ← Global exception handlers registered on app
├── logging.py                   ← Structured JSON logger configuration
└── middleware/
    ├── correlation.py           ← Injects X-Correlation-ID on every request
    ├── organization.py          ← Resolves organization_id from JWT into request state
    ├── audit.py                 ← Writes access audit events to outbox post-response
    └── rate_limit.py            ← Per-user sliding window rate limiting via Redis
```

## 1.3 Shared Directory

```
app/shared/
├── domain/
│   ├── base_entity.py           ← Base: id (UUID), created_at, updated_at
│   ├── value_objects.py         ← Email, PermissionCode, MappingWeight, etc.
│   └── enums.py                 ← Status enums (WorkflowState, ScopeType, etc.)
│
├── events/
│   ├── base_event.py            ← DomainEvent base: event_id, occurred_at, org_id
│   ├── bus.py                   ← In-process synchronous event bus
│   ├── outbox.py                ← Transactional outbox writer
│   └── registry.py              ← Maps event types to handler functions
│
├── repository/
│   ├── base.py                  ← Generic async repository: get, list, create, update
│   └── unit_of_work.py          ← UoW: wraps AsyncSession, commits/rollbacks
│
└── schemas/
    ├── pagination.py            ← PaginatedResponse[T], PageParams
    ├── response.py              ← StandardResponse[T], ErrorResponse
    └── filters.py               ← Common filter params (status, search, date range)
```

## 1.4 Workers Directory

```
app/workers/
├── main.py                      ← ARQ worker entry point; registers all task functions
├── settings.py                  ← ARQ RedisSettings, job timeout configs
└── tasks/
    ├── attainment.py            ← calculate_attainment(run_id)
    ├── reports.py               ← generate_report(run_id)
    ├── notifications.py         ← send_email_notification(notification_id)
    ├── outbox_relay.py          ← process_outbox_events() — polling job
    └── cleanup.py               ← purge_expired_tokens(), archive_old_notifications()
```

## 1.5 Modules Directory (All Bounded Contexts)

```
app/modules/
├── ref_data/         ← config schema: bloom levels, delivery methods, CP/CA/KP
├── iam/              ← Identity: users, roles, permissions, auth tokens
├── org/              ← Organization, departments, programs
├── curriculum/       ← Curricula, courses, batches, sections, offerings, terms
├── obe/              ← POs, COs, all CO mappings (PO/CP/CA/KP)
├── assessment/       ← Assessments, student marks, result publications
├── attainment/       ← Attainment runs, CO/course/PO attainment results
├── approval/         ← Workflow definitions, approval requests, step records
├── notification/     ← Templates, in-app inbox, email queue
├── audit/            ← Audit event queries (append-only reads)
├── accreditation/    ← Bodies, cycles, reports
└── reporting/        ← Report definitions, report run orchestration
```

---

# 2. Module Structure

Every module follows an identical internal structure. This consistency is a hard architectural rule — it enables developers to navigate any module without guidance.

## 2.1 Standard Module Layout

```
app/modules/{module_name}/
│
├── __init__.py
│
├── router.py                    ← APIRouter with all HTTP endpoints for this module
│                                  (or router/ directory for large modules)
│
├── schemas/                     ← Pydantic models (request DTOs, response DTOs)
│   ├── requests.py              ← Input validation schemas
│   └── responses.py             ← Output serialization schemas
│
├── models.py                    ← SQLAlchemy ORM models (schema-qualified tables)
│
├── domain/
│   ├── entities.py              ← Pure domain entities: state machine logic,
│   │                              business rule checks, invariant enforcement
│   ├── value_objects.py         ← Module-specific value objects
│   └── events.py                ← Domain events emitted by this module
│
├── service.py                   ← Application service: use case orchestration
│                                  (or service/ directory for large modules)
│
├── repository.py                ← Data access: all SQL lives here
│                                  (or repository/ directory for large modules)
│
├── dependencies.py              ← FastAPI Depends for this module's services/repos
│
└── exceptions.py                ← Module-specific domain exceptions
```

## 2.2 Complex Module Layout (IAM and OBE)

For IAM and OBE, the module is large enough to warrant sub-directories:

```
app/modules/iam/
├── __init__.py
├── router/
│   ├── auth_router.py           ← /auth/login, /auth/refresh, /auth/logout
│   ├── user_router.py           ← /users CRUD
│   └── role_router.py           ← /roles, /permissions
├── schemas/
│   ├── auth.py                  ← LoginRequest, TokenResponse, RefreshRequest
│   ├── user.py                  ← CreateUserRequest, UserResponse, etc.
│   └── role.py                  ← CreateRoleRequest, PermissionManifest
├── models.py
├── domain/
│   ├── entities.py              ← User, Role, Permission entities
│   └── events.py                ← UserCreated, RoleAssigned, etc.
├── service/
│   ├── auth_service.py          ← login(), refresh_token(), logout()
│   ├── user_service.py          ← create_user(), deactivate_user()
│   └── permission_service.py    ← build_manifest(), check_permission()
├── repository/
│   ├── user_repository.py
│   ├── role_repository.py
│   └── token_repository.py
├── dependencies.py
└── exceptions.py
```

```
app/modules/obe/
├── __init__.py
├── router/
│   ├── po_router.py             ← /program-outcomes
│   ├── co_router.py             ← /course-outcomes
│   └── mapping_router.py        ← /mappings/co-po, /mappings/co-cp, etc.
├── schemas/
│   ├── po.py
│   ├── co.py
│   └── mapping.py
├── models.py
├── domain/
│   ├── entities.py              ← CourseOutcome with state machine transitions
│   ├── value_objects.py         ← MappingMatrix (CO×PO immutable snapshot)
│   └── events.py                ← COPublished, COLocked, MappingApproved, etc.
├── service/
│   ├── po_service.py
│   ├── co_service.py
│   └── mapping_service.py
├── repository/
│   ├── po_repository.py
│   ├── co_repository.py
│   └── mapping_repository.py
├── dependencies.py
└── exceptions.py
```

## 2.3 Module Internal Dependency Rule

```
router.py
  └── depends on: schemas/, dependencies.py
  └── calls: service.py ONLY

service.py
  └── depends on: domain/, repository.py, shared/events/
  └── calls: repository.py, event bus
  └── NEVER calls: router, other module services directly

repository.py
  └── depends on: models.py, shared/repository/base.py
  └── calls: SQLAlchemy AsyncSession ONLY
  └── NEVER calls: service.py, other modules

domain/entities.py
  └── depends on: domain/value_objects.py, shared/domain/
  └── NO dependencies on SQLAlchemy, FastAPI, or Redis
  └── Pure Python only
```

**Cross-module calls:** Modules never import each other's services or repositories directly. Cross-module data needs go through domain events or dedicated query services in the reporting module.

---

# 3. Service Layer Architecture

## 3.1 Role of the Application Service

The application service is the transaction script for a single use case. It is the only layer that:
- Orchestrates the full operation across multiple aggregates
- Owns the transaction boundary (via Unit of Work)
- Emits domain events after a successful commit
- Enforces cross-aggregate business rules via domain services

The application service does NOT:
- Contain SQL queries (delegated to repository)
- Know about HTTP request/response (no FastAPI imports)
- Write to Redis directly (goes through cache service abstraction)
- Store state between calls (fully stateless)

## 3.2 Full Request Lifecycle

```
HTTP Request
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ MIDDLEWARE CHAIN (executed in order)                          │
│                                                              │
│  1. CorrelationMiddleware     — assign trace_id to request   │
│  2. OrganizationMiddleware    — resolve org_id from JWT      │
│  3. RateLimitMiddleware       — check Redis rate bucket      │
│  4. AuditMiddleware           — register post-response hook  │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ ROUTER (router.py)                                           │
│                                                              │
│  • Route matching                                            │
│  • Pydantic request validation (auto, via schema)            │
│  • Resolves FastAPI dependencies                             │
│  • Calls service method                                      │
│  • Serializes response via Pydantic response schema          │
└──────────────────────────────────────────────────────────────┘
    │  via FastAPI Depends
    ▼
┌──────────────────────────────────────────────────────────────┐
│ DEPENDENCY RESOLUTION                                         │
│                                                              │
│  get_db() → AsyncSession (one per request)                   │
│  get_current_user() → CurrentUser (from JWT)                 │
│  get_{module}_service() → ApplicationService instance        │
│  require_permission("co.approve") → AuthorizationCheck       │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ APPLICATION SERVICE (service.py)                             │
│                                                              │
│  async with unit_of_work as uow:                             │
│    1. Load aggregate via repository                          │
│    2. Validate preconditions                                 │
│    3. Execute domain operation (state transition, etc.)      │
│    4. Persist changes via repository                         │
│    5. Stage domain events for emission                       │
│    6. uow.commit()  ← commit DB + flush outbox in one TX     │
│                                                              │
│  After commit:                                               │
│    7. Emit staged events to in-process event bus             │
│    8. Return result DTO                                      │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ REPOSITORY (repository.py)                                    │
│                                                              │
│  • Translates domain calls to SQLAlchemy queries             │
│  • Returns ORM model instances (treated as domain entities)  │
│  • Applies scope-based WHERE filters                         │
│  • Never holds open cursors across service calls             │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ DATABASE (PostgreSQL via asyncpg driver)                      │
└──────────────────────────────────────────────────────────────┘
    │
    ▼ (after commit)
┌──────────────────────────────────────────────────────────────┐
│ IN-PROCESS EVENT BUS                                          │
│                                                              │
│  • Receives staged events from service                       │
│  • Dispatches to registered handlers synchronously           │
│  • Handlers write to outbox for async processing             │
│  • Handlers invalidate cache entries                         │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
HTTP Response (serialized by Pydantic)
    │
    ▼ (after response sent)
┌──────────────────────────────────────────────────────────────┐
│ AUDIT MIDDLEWARE POST-HOOK                                    │
│                                                              │
│  • Writes audit event to audit.audit_events                  │
│  • Does NOT block the response                               │
└──────────────────────────────────────────────────────────────┘
```

## 3.3 Domain Service vs. Application Service

| Concern | Lives In | Example |
|---|---|---|
| Use case orchestration | Application Service | `publish_course_outcome()` |
| Transaction boundary | Application Service (via UoW) | `async with unit_of_work as uow` |
| State transition validation | Domain Entity | `co.publish()` raises if status != APPROVED |
| Business invariant enforcement | Domain Entity | CO lock guard, PO archival guard |
| Cross-aggregate domain logic | Domain Service | `PrerequisiteGraphValidator.check_cycle()` |
| Cross-aggregate data queries | Query Service (read model) | `AttainmentTrendQueryService.by_program()` |

## 3.4 Domain Services (not Application Services)

Domain services encapsulate logic that spans multiple aggregates but belongs to the domain model, not a specific entity.

| Domain Service | Module | Responsibility |
|---|---|---|
| `PrerequisiteGraphValidator` | curriculum | Detects cycles in the prerequisite edge graph before any edge is added |
| `AttainmentCalculationEngine` | attainment | Executes the CO→Course→PO attainment formula chain; takes snapshots as input |
| `MappingMatrixSnapshotBuilder` | obe | Captures the CO×PO matrix as an immutable JSONB snapshot for an attainment run |
| `ApprovalChainResolver` | approval | Determines the next approver for a workflow step given the current state |
| `PermissionManifestBuilder` | iam | Builds the full permission manifest for a user by resolving all role assignments |
| `WeightageValidator` | assessment | Validates that assessment weightages in a section offering sum to exactly 100% |

## 3.5 Query Services (CQRS Read Side)

For report generation and trend analysis, the standard repository → aggregate pattern is too slow. Query services bypass aggregates and issue optimized SQL directly.

| Query Service | Purpose | Pattern |
|---|---|---|
| `AttainmentTrendQueryService` | Cross-run PO attainment trends for a program | Direct SQL with window functions; read-only session |
| `COPOMappingMatrixQueryService` | Render the full CO×PO grid for a curriculum version | JOIN across obe schema tables; optimized for display |
| `BatchProgressQueryService` | Track completion progress for a batch | Aggregate marks and results across a batch's offerings |
| `AccreditationEvidenceQueryService` | Pull all attainment data for an accreditation cycle | Multi-join cross-semester aggregation |
| `FacultyWorkloadQueryService` | Teaching load summary per faculty member | JOIN across curriculum.faculty_assignments and section_offerings |

Query services use a **read-only SQLAlchemy session** (no Unit of Work, no write capabilities) and may query across schemas freely. In future, they can be pointed to a read replica without any application code change.

---

# 4. Repository Architecture

## 4.1 Base Repository

All module repositories inherit from the base repository in `shared/repository/base.py`. The base provides generic async operations against a typed SQLAlchemy model.

```
BaseRepository[ModelType, IDType]
│
├── get(id) → ModelType | None
├── get_or_raise(id) → ModelType          ← raises EntityNotFoundError
├── list(filters, pagination) → list[ModelType]
├── count(filters) → int
├── create(data) → ModelType
├── update(id, data) → ModelType
├── exists(id) → bool
└── flush()                               ← flush pending writes without commit
```

All operations receive the `AsyncSession` through constructor injection, not as a global. This makes testing with an injected mock session trivial.

## 4.2 Unit of Work

The Unit of Work wraps a database transaction and provides access to all repositories within a single transactional scope.

```
UnitOfWork
│
├── session: AsyncSession                 ← single session for this UoW scope
├── outbox: OutboxWriter                  ← writes events to domain_events table
│
├── Repositories (property access):
│   ├── users: UserRepository
│   ├── roles: RoleRepository
│   ├── curricula: CurriculumRepository
│   ├── course_outcomes: CourseOutcomeRepository
│   ├── co_po_mapping_sets: COMappingRepository
│   ├── assessments: AssessmentRepository
│   ├── student_marks: StudentMarkRepository
│   ├── attainment_runs: AttainmentRunRepository
│   ├── approval_requests: ApprovalRequestRepository
│   └── ... (all aggregate repositories)
│
├── commit() → flushes outbox + commits session atomically
├── rollback() → rolls back entire transaction
└── __aexit__() → auto-rollback on exception
```

**Atomic outbox commit:** The Unit of Work's `commit()` writes domain events to the `domain_events` outbox table within the same database transaction as the aggregate changes. If the commit fails, no events are written. If the commit succeeds, the outbox events are guaranteed to exist. The outbox relay worker processes them asynchronously.

## 4.3 Module Repository Design

Each module repository extends the base and adds module-specific query methods.

```
CourseOutcomeRepository extends BaseRepository[CourseOutcome]
│
├── (from base) get, get_or_raise, list, count, create, update
│
├── Module-specific queries:
│   ├── find_by_curriculum_and_course(curriculum_id, course_id, filters)
│   ├── find_by_status(curriculum_id, status_list)
│   ├── find_published_for_course(curriculum_id, course_id)
│   ├── find_locked_by_attainment_run(run_id)
│   ├── count_by_curriculum(curriculum_id)
│   └── exists_with_code(curriculum_id, course_id, code)
│
└── Scope-aware queries: all list methods accept ScopeFilter
    which is constructed from the current user's permission manifest
```

## 4.4 Scope Filter Pattern

Repository queries never directly read the user from context. Instead, the application service constructs a `ScopeFilter` object from the authorization context and passes it to the repository.

```
ScopeFilter
├── organization_id: UUID                 ← always set
├── program_ids: list[UUID] | None        ← None means no restriction (GLOBAL scope)
├── section_offering_ids: list[UUID]|None ← None means no restriction
└── student_id: UUID | None               ← set only for SELF scope
```

The repository applies the scope filter as additional WHERE clauses on every list query. This is Layer 3 data authorization — defense-in-depth.

## 4.5 Query Specification Pattern

For complex filtering on list endpoints (filtering by multiple fields, date ranges, status lists), the repository uses a Specification pattern rather than accepting ad-hoc keyword arguments.

```
CourseOutcomeFilter (specification)
├── curriculum_id: UUID | None
├── course_id: UUID | None
├── status: list[WorkflowState] | None
├── bloom_level_id: UUID | None
├── search: str | None                    ← ILIKE on statement
└── created_after: datetime | None
```

Repositories accept a filter specification + pagination params + scope filter. This keeps the repository interface stable as new filter options are added.

## 4.6 Database Session Lifecycle

```
Request arrives
    │
    ▼ FastAPI Depends: get_db()
AsyncSession created (from connection pool)
    │
    ▼ Passed to Unit of Work
UoW wraps session in transaction (BEGIN)
    │
    ▼ Service executes via UoW repositories
Reads and writes via session
    │
    ├── Success path: uow.commit() → COMMIT
    └── Exception path: auto rollback → ROLLBACK
    │
    ▼ FastAPI Depends cleanup
AsyncSession returned to connection pool
```

**Connection pool configuration:**
- `pool_size`: 10 (connections kept open)
- `max_overflow`: 20 (additional connections under burst)
- `pool_timeout`: 30 seconds (wait time before raising error)
- `pool_recycle`: 1800 seconds (recycle connections to prevent stale state)
- Driver: `asyncpg` (not psycopg2 — asyncpg is 3× faster for async workloads)

## 4.7 Multi-Schema SQLAlchemy Configuration

All SQLAlchemy models declare their PostgreSQL schema explicitly. Alembic's `env.py` imports all models before autogenerate to ensure all schemas are reflected.

```
ORM Model Pattern:
  class CourseOutcome(Base):
      __tablename__ = "course_outcomes"
      __table_args__ = {"schema": "obe"}
```

Alembic migration files contain both the schema name and table name, ensuring migrations run against the correct PostgreSQL schema regardless of the current `search_path`.

---

# 5. Authentication Architecture

## 5.1 Token Strategy

| Token | Lifetime | Storage | Purpose |
|---|---|---|---|
| Access Token (JWT) | 15 minutes | Client memory / Authorization header | Authenticate each API request |
| Refresh Token | 7 days | HttpOnly Secure cookie (configurable) | Obtain new access tokens without re-login |

**Why short access token TTL:** Deactivated user accounts take effect within 15 minutes at most, without requiring token blacklisting infrastructure. High-security operations (publish, approve) do live user status checks regardless.

## 5.2 JWT Payload Structure

```
Access Token Payload:
{
  "sub": "user-uuid",
  "org": "org-uuid",
  "jti": "token-uuid",           ← unique token identifier
  "iat": 1748000000,
  "exp": 1748000900,             ← 15 minutes
  "type": "access"
}
```

The JWT payload intentionally carries minimal claims. Roles and permissions are NOT embedded in the token — they are resolved from cache (Redis) on each request. This allows permission changes to take effect within 5 minutes (cache TTL) without token revocation.

## 5.3 Authentication Flow

```
LOGIN FLOW
  POST /api/v1/auth/login
  Request: { email, password }

  AuthService.login():
    1. UserRepository.find_by_email(email, org_id)  → User | None
    2. IF not found OR status != ACTIVE → raise InvalidCredentials
    3. CredentialRepository.get_by_user(user_id)    → PasswordCredential
    4. verify_password(password, hash)              → bool
    5. IF failed → raise InvalidCredentials (no hint whether user/password was wrong)
    6. Generate access_token (JWT, 15m)
    7. Generate refresh_token (opaque random bytes, 64 chars)
    8. Hash refresh_token → store in iam.refresh_tokens with user_id, expires_at
    9. Build permission manifest → cache under user:{id}:manifest (5min TTL)
    10. Emit UserLoggedIn domain event (for audit)

  Response:
    Body: { access_token, token_type: "bearer", expires_in: 900 }
    Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Strict; Path=/auth/refresh

─────────────────────────────────────────────────────────────────

REFRESH FLOW
  POST /api/v1/auth/refresh
  Cookie: refresh_token=<token>

  AuthService.refresh():
    1. Extract refresh_token from cookie
    2. Hash the token → look up in iam.refresh_tokens
    3. IF not found OR revoked_at IS NOT NULL OR expires_at < NOW():
       → raise InvalidToken
    4. Token family check: IF a previously-used token from this family is replayed
       → revoke ALL tokens for this user (compromise detected), raise InvalidToken
    5. Revoke old refresh_token (set revoked_at = NOW())
    6. Generate new access_token
    7. Generate new refresh_token → store, set old as revoked
    8. Return new tokens

─────────────────────────────────────────────────────────────────

LOGOUT FLOW
  POST /api/v1/auth/logout
  Authorization: Bearer <access_token>

  AuthService.logout():
    1. Identify user from JWT
    2. Revoke the specific refresh_token presented (or all, if "logout everywhere")
    3. Clear the manifest cache: user:{id}:manifest
    4. Emit UserLoggedOut domain event

─────────────────────────────────────────────────────────────────

PASSWORD RESET FLOW
  POST /api/v1/auth/password-reset-request   → generates token, sends email
  POST /api/v1/auth/password-reset-confirm   → validates token, sets new password

  Token: random 64-byte hex, hashed with SHA-256 before storage
  TTL: 1 hour
  Single-use: token marked as used after first successful reset
```

## 5.4 JWT Validation Dependency

```
FastAPI Dependency Chain for Protected Endpoints:

  HTTPBearer() → raw token string
      │
      ▼
  decode_access_token(token)
      ├── Verify signature (HS256 or RS256)
      ├── Check exp, iat, type="access"
      └── Returns JWT payload
      │
      ▼
  get_current_user(payload)
      ├── Load user from cache or DB by sub (user_id)
      ├── Check user.status == ACTIVE
      ├── Inject user into request state
      └── Returns CurrentUser object

  CurrentUser {
    id: UUID
    organization_id: UUID
    email: str
    is_active: bool
  }
```

## 5.5 Password Policy

Enforced at the application service layer before bcrypt hashing:

| Rule | Requirement |
|---|---|
| Minimum length | 10 characters |
| Complexity | At least 1 uppercase, 1 lowercase, 1 digit, 1 special character |
| Bcrypt rounds | 12 (configurable, increase over time as hardware improves) |
| History | Last 5 passwords cannot be reused (stored as bcrypt hashes in credential history) |
| Rotation | Forced rotation is configurable per organization |

---

# 6. Authorization Architecture

## 6.1 Three-Layer Enforcement

Authorization is enforced at three independent layers. Passing Layer 2 does not skip Layer 3. All three must cooperate.

```
Layer 1: HTTP Middleware (JWTValidationMiddleware)
  → Validates JWT signature and expiry on every request
  → Rejects 401 before any service code runs

Layer 2: FastAPI Dependency (require_permission)
  → Checks permission code against user's manifest
  → Resolves resource context
  → Runs scope + assignment gates
  → Rejects 403 before service function runs

Layer 3: Repository WHERE filters (ScopeFilter)
  → All list/read queries include scope-based WHERE clauses
  → Defense-in-depth: even if Layer 2 has a bug, data stays scoped
  → Returns empty results rather than 403 for browsing APIs
```

## 6.2 Permission Manifest Dependency

```
require_permission("co.approve") creates a FastAPI Depends:

  get_permission_manifest(current_user):
    1. Try cache.get("user:{id}:manifest")
    2. IF cache miss:
       a. Load user_role_assignments (active) from DB
       b. For each assignment, load role_permissions from cache or DB
       c. Union all permission codes
       d. Collect program_ids, department_ids from assignments
       e. Load offering_ids from faculty_assignments (for ML/Teacher)
       f. Build manifest = PermissionManifest(permissions, scope, offering_ids)
       g. cache.set("user:{id}:manifest", manifest, TTL=300)
    3. Return manifest

  check_permission("co.approve", manifest, resource_context):
    → Implements the three-gate algorithm from RBAC Architecture §9.1
    → Returns AuthorizationResult(allowed, applied_scope)
    → On DENY: raise PermissionDeniedError (→ 403)
```

## 6.3 Resource Context Resolution

The resource context must be resolved before the permission check can evaluate scope. The resolution strategy depends on what the endpoint is accessing.

```
ResourceContextResolvers:

  "co_by_id"     → load CO from DB → extract curriculum_id, course_id
                   → resolve program_id from curriculum
                   → extract section_offering_ids for this course/curriculum

  "assessment_by_id" → load assessment → extract section_offering_id
                       → resolve course_id, curriculum_id, batch_id, program_id

  "program_scoped"   → program_id is a path/query parameter directly

  "offering_scoped"  → section_offering_id is a path parameter
                       → check faculty_assignments gate
```

Resolvers are registered alongside the permission annotation. The middleware resolves the context once and caches it in request state.

## 6.4 Authorization Caching

```
Redis Key Structure:

  user:{user_id}:manifest              ← Full PermissionManifest JSON
  user:{user_id}:assignments           ← List of { role_id, scope_type, scope_id }
  role:{role_id}:permissions           ← Set of permission code strings
  user:{user_id}:offering_ids          ← List of section_offering_ids (ML/Teacher)

TTL:
  manifest:     300 seconds (5 minutes)
  assignments:  300 seconds
  permissions:  1800 seconds (30 minutes — roles change rarely)
  offering_ids: 600 seconds (10 minutes)

Invalidation triggers:
  UserRoleAssigned event   → DEL user:{id}:manifest, user:{id}:assignments
  UserRoleRevoked event    → DEL user:{id}:manifest, user:{id}:assignments
  PermissionGranted event  → DEL role:{id}:permissions + all affected manifests
  FacultyAssigned event    → DEL user:{id}:offering_ids, user:{id}:manifest
```

## 6.5 High-Security Operation Gate

For irreversible operations (`attainment.publish`, `co.publish`, `result.publish`), the authorization service bypasses the cache and performs a **live database check**:

```
live_permission_check(user_id, permission_code):
  → Direct DB query: no Redis cache read
  → Validates user.status = 'ACTIVE' in real time
  → Validates role assignment is not revoked
  → Returns within the same DB transaction as the operation itself
```

This prevents a recently-deactivated or de-roled user from completing a publication in the window between their cache expiry and their next login.

---

# 7. Event Architecture

## 7.1 Event Flow Overview

```
Application Service
    │
    ├─ (within transaction) OutboxWriter.stage(event)
    │       └── Writes to domain_events table (same DB, same TX)
    │
    ├─ uow.commit()  ← TX commits; domain_events rows are now persistent
    │
    └─ InProcessEventBus.emit(event)
            ├── CacheInvalidationHandler → invalidates Redis keys
            ├── ApprovalWorkflowHandler → creates/advances approval_requests
            └── NotificationTriggerHandler → creates in_app_notifications + email queue entries

(Async / decoupled)
OutboxRelayWorker (ARQ job, every 5 seconds)
    ├── Reads unprocessed rows from domain_events
    ├── For each event:
    │   ├── Dispatches to registered async handlers
    │   │   ├── AuditEventHandler → writes to audit.audit_events
    │   │   └── ExternalIntegrationHandler → future: webhook, LMS sync
    │   └── Marks row as processed
    └── Handles retries with exponential backoff (max 3 attempts)
```

## 7.2 Domain Event Base Structure

Every domain event carries a standard envelope:

```
DomainEvent (base):
  event_id: UUID                  ← unique per event instance
  event_type: str                 ← e.g., "obe.CourseOutcomePublished"
  occurred_at: datetime (UTC)
  organization_id: UUID
  actor_user_id: UUID
  aggregate_type: str             ← e.g., "CourseOutcome"
  aggregate_id: UUID
  payload: dict                   ← event-specific data (serialized as JSON)
  correlation_id: str             ← from request X-Correlation-ID header
```

## 7.3 Outbox Table Structure

The `domain_events` outbox table lives in its own schema (`events`) within PostgreSQL:

```
events.domain_events
  id: UUID PK
  event_type: VARCHAR
  occurred_at: TIMESTAMPTZ
  organization_id: UUID
  aggregate_type: VARCHAR
  aggregate_id: UUID
  payload: JSONB
  correlation_id: VARCHAR
  status: VARCHAR              ← PENDING, PROCESSED, FAILED
  processed_at: TIMESTAMPTZ
  retry_count: SMALLINT
  last_error: TEXT
  created_at: TIMESTAMPTZ

Indexes:
  (status, occurred_at) WHERE status = 'PENDING'   ← relay worker query
  (aggregate_type, aggregate_id)                     ← event history for entity
```

## 7.4 In-Process vs. Outbox Handlers

| Handler Type | Execution | Failure Behavior | Use For |
|---|---|---|---|
| **In-Process** (EventBus) | Synchronous, within same request | Ignored (logged); does not fail the request | Cache invalidation, in-app notification creation |
| **Outbox Relay** (ARQ worker) | Async, separate process | Retried with backoff; moved to FAILED after max retries | Audit event writing, email queuing, external integrations |

In-process handlers are lightweight and side-effect tolerant. Outbox relay handlers are for durable side effects that must not be lost.

## 7.5 Domain Events Catalog

The complete set of domain events emitted by the platform (from DDD Analysis §6), grouped by module:

| Module | Events (abbreviated) |
|---|---|
| IAM | UserCreated, UserDeactivated, RoleAssigned, RoleRevoked, PasswordReset, UserLoggedIn |
| Org | DepartmentCreated, DepartmentArchived, ProgramCreated |
| Curriculum | CurriculumCreated, CurriculumActivated, CurriculumVersioned, CourseCreated, BatchCreated |
| OBE | CourseOutcomeDrafted, CourseOutcomeSubmitted, CourseOutcomeApproved, CourseOutcomePublished, CourseOutcomeLocked, COPOMappingPublished |
| Assessment | AssessmentConfigured, MarksEntered, ResultSubmittedByTeacher, ResultApprovedByML, ResultApprovedByPC, ResultPublished |
| Attainment | AttainmentRunInitiated, AttainmentCalculated, AttainmentPublished |
| Approval | ApprovalRequestCreated, ApprovalStepActioned, ApprovalChainCompleted |

## 7.6 Event Handler Registry

Handlers are registered at application startup in `shared/events/registry.py`:

```
Event Handler Registration:

  CourseOutcomeSubmitted →
    [in-process] CacheInvalidationHandler.on_co_submitted
    [in-process] NotificationTriggerHandler.on_co_submitted   → creates in_app_notification for ML
    [outbox]     AuditEventHandler.on_co_submitted             → writes audit row

  ResultPublished →
    [in-process] CacheInvalidationHandler.on_result_published
    [in-process] NotificationTriggerHandler.on_result_published → notifies students (in-app)
    [outbox]     AttainmentTriggerHandler.on_result_published   → enqueues attainment pre-check
    [outbox]     AuditEventHandler.on_result_published

  AttainmentPublished →
    [in-process] COLockHandler.on_attainment_published          → sets CO status to LOCKED
    [in-process] CacheInvalidationHandler.on_attainment_published
    [outbox]     AuditEventHandler.on_attainment_published
    [outbox]     AccreditationUpdateHandler.on_attainment_published → updates cycle evidence
```

---

# 8. Caching Strategy

## 8.1 Cache Topology

```
Redis Instance
│
├── Namespace: auth:*              ← Authentication data
│   ├── user:{id}:manifest         TTL: 300s
│   ├── user:{id}:assignments      TTL: 300s
│   ├── role:{id}:permissions      TTL: 1800s
│   └── user:{id}:offering_ids     TTL: 600s
│
├── Namespace: data:*              ← Application data cache
│   ├── co_po_matrix:{curriculum_id}:{course_id}    TTL: 900s
│   ├── po_list:{program_id}                         TTL: 600s
│   ├── active_terms:{org_id}                        TTL: 300s
│   ├── ref_data:{org_id}:{type}                     TTL: 3600s (config rarely changes)
│   └── offering_roster:{offering_id}                TTL: 600s
│
├── Namespace: report:*            ← Generated report results
│   └── report_run:{run_id}:status  TTL: 86400s (24h) or until consumed
│
├── Namespace: ratelimit:*         ← Rate limiting counters
│   └── rl:{user_id}:{endpoint_class}  TTL: 60s (sliding window)
│
└── Namespace: job:*               ← Background job tracking
    └── job:{job_id}:status         TTL: 3600s
```

## 8.2 Cache-Aside Pattern

The standard read-through pattern used across all cached data:

```
CacheService.get_or_compute(key, compute_fn, ttl):
  1. result = redis.get(key)
  2. IF result is not None:
       return deserialize(result)
  3. result = await compute_fn()          ← DB query or computation
  4. redis.setex(key, ttl, serialize(result))
  5. return result
```

The `CacheService` abstraction wraps Redis and handles serialization (JSON), deserialization, and TTL management. All caching in the application goes through this service — no direct Redis calls in business logic.

## 8.3 Cache Invalidation Strategy

**Event-driven invalidation:** Cache entries are invalidated by in-process event handlers, not by the code that made the change. This decouples invalidation from write logic.

```
Invalidation Map:

  UserRoleAssigned(user_id) →
    DEL user:{user_id}:manifest
    DEL user:{user_id}:assignments

  PermissionGranted(role_id) →
    DEL role:{role_id}:permissions
    DEL user:*:manifest WHERE user holds this role   ← pattern delete via SCAN

  FacultyAssigned(user_id, offering_id) →
    DEL user:{user_id}:offering_ids
    DEL user:{user_id}:manifest
    DEL offering_roster:{offering_id}

  COPOMappingPublished(curriculum_id, course_id) →
    DEL co_po_matrix:{curriculum_id}:{course_id}

  ProgramOutcomeUpdated(program_id) →
    DEL po_list:{program_id}

  ConfigDataUpdated(org_id, type) →
    DEL ref_data:{org_id}:{type}
```

**Pattern delete safety:** Pattern deletes (`DEL user:*:manifest`) use Redis SCAN (not KEYS) to avoid blocking. In high-load scenarios, defer pattern deletes to the outbox relay worker.

## 8.4 Reference Data Caching

Reference data (bloom levels, delivery methods, course types, CP/CA/KP codes) is heavily read and rarely written. It is cached at the organization level with a 1-hour TTL. On any config update, the cache entry is immediately invalidated.

The frontend can also cache reference data client-side using standard HTTP `Cache-Control` headers set by the API (30-minute browser cache). The API endpoint uses an `ETag` based on the latest `updated_at` timestamp of the config record set.

## 8.5 Report Caching

Generated reports are not cached in Redis — they are stored in MinIO after generation. The `report_runs` table tracks the job status and the MinIO `file_key` once complete. The API returns the download URL by generating a pre-signed MinIO URL from the stored key.

Re-generation of the same report (same definition + same parameters) within a short window issues a new ARQ job but checks first if a `COMPLETED` run with identical parameters exists within the last 24 hours. If so, the existing file_key is returned without re-running.

---

# 9. File Management Architecture

## 9.1 MinIO Bucket Organization

```
MinIO
└── Bucket: obelytics-{env}          ← one bucket per environment
    │
    ├── org/{org_id}/
    │   └── logo/                    ← Organization logo files
    │       └── logo_{timestamp}.{ext}
    │
    ├── reports/{org_id}/{year}/{month}/
    │   └── {report_run_id}.{pdf|xlsx|csv}
    │
    ├── accreditation/{org_id}/{cycle_id}/
    │   └── {report_type}_{timestamp}.pdf
    │
    └── attachments/{org_id}/{offering_id}/    ← Future: assessment submissions
        └── {student_id}/{filename}
```

**Bucket policy:** The bucket is private. All access is via server-generated pre-signed URLs. No public objects.

## 9.2 File Upload Flow (Server-Side Pre-Signed)

```
CLIENT                    API SERVER               MINIO
  │                           │                      │
  │  POST /files/upload-url   │                      │
  │  { purpose, filename,     │                      │
  │    content_type, size }   │                      │
  │──────────────────────────►│                      │
  │                           │                      │
  │                           │ Validates:           │
  │                           │  - permission check  │
  │                           │  - file type allowed │
  │                           │  - size <= limit     │
  │                           │                      │
  │                           │ generate_presigned_  │
  │                           │ put_url(object_key,  │
  │                           │ expires=300)         │
  │                           │─────────────────────►│
  │                           │◄─────────────────────│
  │                           │  pre-signed PUT URL  │
  │                           │                      │
  │ { upload_url, object_key }│                      │
  │◄──────────────────────────│                      │
  │                           │                      │
  │  PUT upload_url           │                      │
  │  (file bytes directly)    │                      │
  │──────────────────────────────────────────────────►
  │                           │                      │
  │  POST /files/confirm      │                      │
  │  { object_key }           │                      │
  │──────────────────────────►│                      │
  │                           │ stat_object(key)     │
  │                           │─────────────────────►│
  │                           │◄─────────────────────│
  │                           │  metadata confirmed  │
  │                           │                      │
  │                           │ Stores file_key in DB│
  │                           │ entity.logo_file_key │
  │                           │                      │
  │ { file_id, file_key }     │                      │
  │◄──────────────────────────│                      │
```

**Why client-to-MinIO direct upload:** Files never pass through the FastAPI server, keeping the API responsive and preventing memory spikes from large file buffering.

## 9.3 File Download Flow

```
CLIENT                    API SERVER               MINIO
  │                           │                      │
  │  GET /org/logo            │                      │
  │──────────────────────────►│                      │
  │                           │ Permission check     │
  │                           │ Load entity.logo_key │
  │                           │                      │
  │                           │ generate_presigned_  │
  │                           │ get_url(key, expires=│
  │                           │ 3600)                │
  │                           │─────────────────────►│
  │                           │◄─────────────────────│
  │                           │                      │
  │ 302 Redirect → presigned  │                      │
  │◄──────────────────────────│                      │
  │                           │                      │
  │  GET presigned_url (direct)                      │
  │──────────────────────────────────────────────────►
  │◄──────────────────────────────────────────────────
  │  file bytes                                      │
```

For report downloads, the pre-signed URL TTL is 15 minutes (reports may be large; the user needs time to initiate the download). For logos, TTL is 1 hour.

## 9.4 File Service Interface

```
FileService (abstraction over MinIO client):
├── generate_upload_url(purpose, object_key, content_type, size_limit) → PresignedUploadResult
├── confirm_upload(object_key) → FileMetadata
├── generate_download_url(object_key, ttl_seconds) → str (URL)
├── delete_object(object_key) → None
├── object_exists(object_key) → bool
└── generate_object_key(purpose, org_id, **context) → str

Allowed file types by purpose:
  org_logo:      [image/jpeg, image/png, image/webp]  max 5MB
  report:        [application/pdf, application/vnd.xlsx, text/csv]  max 50MB
  accreditation: [application/pdf]  max 100MB
```

## 9.5 Report Generation and Storage

Reports are generated by the `reports` ARQ worker task:

```
generate_report(report_run_id):
  1. Load report_run from DB → get report_definition + parameters
  2. Execute QueryService to fetch data (read-only DB session)
  3. Render to requested format:
     - PDF: ReportKit/WeasyPrint template rendering
     - Excel: openpyxl workbook construction
     - CSV: csv module streaming write
  4. Upload file to MinIO → file_key
  5. Update report_run: status=COMPLETED, file_key=file_key, completed_at=NOW()
  6. Emit ReportGenerated event → notification to requesting user
```

---

# 10. Background Job Architecture

## 10.1 ARQ (Async Redis Queue)

ARQ is chosen over Celery for this stack because:
- Native async/await support (no sync-in-async workarounds)
- Uses Redis directly (already a dependency)
- Simpler configuration for single-service deployments
- Compatible with FastAPI's async ecosystem

## 10.2 Worker Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Worker Process (ARQ)                         │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Attainment │  │   Reports    │  │   Notification Email │  │
│  │  Worker     │  │   Worker     │  │   Worker             │  │
│  │  Queue      │  │   Queue      │  │   Queue              │  │
│  └─────────────┘  └──────────────┘  └──────────────────────┘  │
│         ▲               ▲                    ▲                  │
│         │               │                    │                  │
│  ┌──────┴───────────────┴────────────────────┴────────────┐   │
│  │                  Redis Job Queue                         │   │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         Scheduled / Cron-like Tasks                       │   │
│  │  - outbox_relay (every 5 seconds)                        │   │
│  │  - purge_expired_tokens (daily)                          │   │
│  │  - archive_old_notifications (weekly)                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

## 10.3 Job Catalog

| Job Function | Queue | Trigger | Timeout | Retry |
|---|---|---|---|---|
| `calculate_attainment(run_id)` | `attainment` | AttainmentInitiated event | 10 min | 2 retries |
| `generate_report(run_id)` | `reports` | ReportRunQueued event | 15 min | 1 retry |
| `send_email_notification(notification_id)` | `notifications` | EmailQueued event | 1 min | 3 retries (backoff) |
| `process_outbox_events()` | `system` | Cron every 5s | 30s | No retry; next cycle handles |
| `purge_expired_tokens()` | `system` | Cron daily at 02:00 | 5 min | No retry |
| `archive_old_notifications()` | `system` | Cron weekly | 10 min | No retry |

## 10.4 Attainment Job Flow

```
AttainmentService.initiate_run(section_offering_id, config_id):
  1. Create AttainmentRun record (status=INITIATED)
  2. Commit to DB
  3. Emit AttainmentRunInitiated event
     → OutboxHandler enqueues: calculate_attainment(run_id)

ARQ Task: calculate_attainment(run_id):
  1. Load AttainmentRun from DB
  2. Load AttainmentConfiguration (thresholds, formula type)
  3. Build snapshots:
     a. MappingMatrixSnapshotBuilder → co_po_mapping_snapshot (JSONB)
     b. Load all assessments + co_weights → assessment_weight_snapshot (JSONB)
  4. AttainmentCalculationEngine.calculate(run_id, snapshots):
     a. Aggregate student marks per CO per assessment
     b. Apply assessment CO weights → CO-level mark
     c. Compare against threshold → CO attainment %
     d. Aggregate COs → Course attainment
     e. Apply CO-PO weights → PO contribution per CO
     f. Aggregate PO contributions → PO attainment %
  5. Write results:
     - co_attainment_results (one per CO)
     - course_attainment_results (one per run)
     - po_attainment_results (one per PO mapped)
  6. Update run: status=CALCULATED, calculated_at=NOW()
  7. Update run: co_po_mapping_snapshot, assessment_weight_snapshot stored
  8. Emit AttainmentCalculated event → notifies coordinator for review
```

## 10.5 Report Job Flow

```
ReportingService.request_report(report_def_id, parameters, format, user_id):
  1. Create ReportRun (status=QUEUED)
  2. Commit to DB
  3. Enqueue ARQ job: generate_report(run_id)
  4. Return report_run_id immediately (async — do not wait)

ARQ Task: generate_report(run_id):
  1. Load ReportRun + ReportDefinition
  2. Resolve QueryService by report category
  3. Execute query with parameters → dataset
  4. Select renderer:
     - PDF: Jinja2 template → HTML → WeasyPrint → PDF bytes
     - Excel: openpyxl workbook → bytes
     - CSV: StringIO → bytes
  5. Upload to MinIO → file_key
  6. Update ReportRun: status=COMPLETED, file_key=key
  7. Emit ReportGenerated event → in-process handler creates in_app_notification

GET /reports/{run_id}/download:
  1. Load ReportRun
  2. Assert status=COMPLETED
  3. Assert requesting user == run.requested_by_user_id OR has report.export permission
  4. Generate pre-signed download URL (15 min TTL)
  5. Return { download_url }
```

## 10.6 Job Status Tracking

The API exposes job status endpoints for long-running jobs:

```
GET /reports/{run_id}          → { status, queued_at, completed_at, download_url? }
GET /attainment/runs/{run_id}  → { status, initiated_at, calculated_at }
```

The frontend polls these endpoints using exponential backoff:
- Poll at 2s, 4s, 8s, 16s, 30s, 60s intervals
- Stop polling when status is COMPLETED or FAILED
- Alternative: WebSocket subscription on the `/ws/jobs/{run_id}` channel (v2 feature)

---

# 11. Notification Architecture

## 11.1 Two-Channel Delivery

```
Domain Event (e.g., COPublished)
    │
    ▼
NotificationTriggerHandler
    │
    ├── Determine recipients from event context
    │     (e.g., CourseOutcomeSubmitted → notify all MODULE_LEADERs for the course)
    │
    ├── Load NotificationTemplate for (event_type, channel) from cache or DB
    │
    ├── Render template (substitute {{co_code}}, {{course_name}}, etc.)
    │
    ├── For IN_APP channel:
    │     └── INSERT into notification.in_app_notifications
    │          (immediate, synchronous, within same request cycle)
    │
    └── For EMAIL channel:
          └── INSERT into notification.notification_queue
               (deferred, processed by email worker)
```

## 11.2 In-App Notification Architecture

```
WRITE: NotificationTriggerHandler (in-process event handler)
  → Inserts in_app_notifications record (is_read=false)

READ: GET /notifications
  → Queries notification.in_app_notifications WHERE recipient_user_id = :self AND is_read = false
  → Returns paginated list with entity_type + entity_id for deep-linking

MARK READ: PATCH /notifications/{id}/read
  → Sets is_read=true, read_at=NOW()

BADGE COUNT: GET /notifications/unread-count
  → Cached in Redis: notification:{user_id}:unread_count (TTL=30s)
  → Incremented on new in-app notification insert (in-process handler)
  → Decremented on mark-as-read (or expire + recount on mismatch)

REAL-TIME (v2):
  → WebSocket connection at /ws/notifications
  → Server pushes new notification objects on INSERT
  → Eliminates polling; requires connection management
```

## 11.3 Email Delivery Architecture

```
notification.notification_queue table
  → Populated by NotificationTriggerHandler
  → status: PENDING | SENT | FAILED

ARQ Task: send_email_notification(notification_id)
  1. Load record from notification_queue
  2. Validate recipient user is still ACTIVE
  3. Connect to SMTP or HTTP email provider (SendGrid / AWS SES)
  4. Send email with rendered subject + body
  5. On success: UPDATE status=SENT, sent_at=NOW()
  6. On failure:
     - IF retry_count < max_retries: UPDATE retry_count++, schedule retry with backoff
     - IF retry_count >= max_retries: UPDATE status=FAILED, log to audit

Retry schedule: 30s, 5min, 30min (exponential backoff, 3 attempts max)
```

## 11.4 Notification Events → Recipients Mapping

| Triggering Event | Recipients | Channel |
|---|---|---|
| `CourseOutcomeSubmitted` | All Module Leaders for the course | IN_APP + EMAIL |
| `CourseOutcomeApproved` | Teacher who submitted the CO | IN_APP |
| `CourseOutcomeRejected` | Teacher who submitted the CO | IN_APP + EMAIL |
| `CourseOutcomePublished` | All Section Teachers for the course | IN_APP |
| `ResultSubmittedByTeacher` | Module Leader for the section | IN_APP |
| `ResultApprovedByML` | Program Coordinator | IN_APP |
| `ResultRejectedByML` | Section Teacher who submitted | IN_APP + EMAIL |
| `ResultPublished` | All enrolled students (in-app only) | IN_APP |
| `AttainmentCalculated` | Program Coordinator | IN_APP |
| `AttainmentPublished` | All Module Leaders in the program | IN_APP |
| `ReportGenerated` | User who requested the report | IN_APP |
| `UserCreated` | The new user (with login instructions) | EMAIL |
| `PasswordReset` | The requesting user | EMAIL |
| `ApprovalRequestCreated` | The assigned approver | IN_APP + EMAIL |

## 11.5 Notification Template System

Templates use Jinja2-style `{{variable}}` placeholders. Template context variables are extracted from the domain event payload.

```
Template for CourseOutcomeSubmitted (EMAIL):
  Subject: "Action Required: CO {{co_code}} submitted for {{course_name}}"
  Body: """
  Dear {{approver_name}},

  {{teacher_name}} has submitted Course Outcome {{co_code}} for
  {{course_name}} ({{curriculum_name}}) for your review.

  CO Statement: {{co_statement}}

  Please log in to Obelytics to review and approve.
  """
```

Templates are stored in `notification.notification_templates` and cached in Redis (1-hour TTL). Organizations can customize them.

---

# 12. Deployment Architecture

## 12.1 Container Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Docker Compose Network                           │
│                                                                         │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────────────┐ │
│  │    Nginx     │   │  FastAPI API  │   │   FastAPI Worker (ARQ)     │ │
│  │  (Reverse    │──►│  (Gunicorn + │   │   (ARQ worker process)     │ │
│  │   Proxy +    │   │  4× Uvicorn  │   │                            │ │
│  │   TLS)       │   │  workers)     │   │   Tasks:                   │ │
│  │              │   │               │   │   - attainment calculation  │ │
│  │  Port: 443   │   │  Port: 8000   │   │   - report generation      │ │
│  │  Port: 80    │   │               │   │   - email delivery         │ │
│  │  (redirect)  │   │               │   │   - outbox relay           │ │
│  └──────┬───────┘   └──────┬────────┘   └─────────┬──────────────────┘ │
│         │                  │                       │                    │
│         │     ┌────────────┼───────────────────────┤                   │
│         │     │            │                       │                   │
│         ▼     ▼            ▼                       ▼                   │
│  ┌────────────────┐   ┌────────────┐   ┌──────────────────────────┐   │
│  │  PostgreSQL    │   │   Redis    │   │         MinIO             │   │
│  │  (Primary)     │   │            │   │   (Object Storage)        │   │
│  │  Port: 5432    │   │  Port: 6379│   │   Port: 9000 (API)        │   │
│  │                │   │            │   │   Port: 9001 (Console)    │   │
│  │  Schemas:      │   │  Namespaces│   │                           │   │
│  │  - iam         │   │  - auth:   │   │   Bucket: obelytics-prod  │   │
│  │  - org         │   │  - data:   │   │                           │   │
│  │  - curriculum  │   │  - rl:     │   │                           │   │
│  │  - obe         │   │  - job:    │   │                           │   │
│  │  - assessment  │   │            │   │                           │   │
│  │  - attainment  │   │            │   │                           │   │
│  │  - ...         │   │            │   │                           │   │
│  └────────────────┘   └────────────┘   └──────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

## 12.2 Docker Service Definitions

```
Service: nginx
  Image: nginx:1.27-alpine
  Ports: 80, 443
  Volumes:
    - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ssl_certs:/etc/nginx/certs:ro
    - static_files:/var/www/static:ro
  Depends on: api (health check)
  Restart: always

─────────────────────────────────────────────────────

Service: api
  Build: ./docker/Dockerfile
  Command: gunicorn app.main:app
           --worker-class uvicorn.workers.UvicornWorker
           --workers 4
           --bind 0.0.0.0:8000
           --timeout 60
           --graceful-timeout 30
           --max-requests 1000          ← worker recycling (prevent memory leaks)
           --max-requests-jitter 100
  Environment:
    DATABASE_URL: postgresql+asyncpg://...
    REDIS_URL: redis://redis:6379/0
    MINIO_ENDPOINT: minio:9000
    SECRET_KEY: <from_secrets>
    ENVIRONMENT: production
  Depends on: postgres, redis, minio (health checks)
  Health check: GET /health/ready (every 30s)
  Restart: always
  Deploy:
    Resources:
      limits: { cpus: '2.0', memory: '1G' }
      reservations: { cpus: '0.5', memory: '256M' }

─────────────────────────────────────────────────────

Service: worker
  Build: ./docker/Dockerfile.worker
  Command: python -m arq app.workers.main.WorkerSettings
  Environment: (same as api)
  Depends on: postgres, redis
  Restart: always
  Deploy:
    Resources:
      limits: { cpus: '2.0', memory: '1G' }

─────────────────────────────────────────────────────

Service: postgres
  Image: postgres:16-alpine
  Environment:
    POSTGRES_DB: obelytics
    POSTGRES_USER: obelytics
    POSTGRES_PASSWORD: <from_secrets>
  Volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./scripts/init_schemas.sql:/docker-entrypoint-initdb.d/01_schemas.sql
  Health check: pg_isready (every 10s)
  Command: postgres -c max_connections=200
                    -c shared_buffers=256MB
                    -c effective_cache_size=1GB
                    -c work_mem=4MB
  Restart: always

─────────────────────────────────────────────────────

Service: redis
  Image: redis:7.2-alpine
  Command: redis-server --maxmemory 512mb
                        --maxmemory-policy allkeys-lru
                        --save 60 1000
                        --requirepass <from_secrets>
  Volumes:
    - redis_data:/data
  Health check: redis-cli ping (every 10s)
  Restart: always

─────────────────────────────────────────────────────

Service: minio
  Image: minio/minio:RELEASE.2025-01-20T14-49-07Z
  Command: server /data --console-address ":9001"
  Environment:
    MINIO_ROOT_USER: <from_secrets>
    MINIO_ROOT_PASSWORD: <from_secrets>
  Volumes:
    - minio_data:/data
  Health check: curl -f http://localhost:9000/minio/health/live (every 30s)
  Ports:
    - "9001:9001"   ← Console (admin only, not exposed via nginx)
  Restart: always
```

## 12.3 Nginx Configuration Design

```
Nginx responsibilities:
  ├── TLS termination (SSL certificates from Let's Encrypt or self-signed)
  ├── HTTP → HTTPS redirect (301)
  ├── Reverse proxy to FastAPI API
  ├── Rate limiting at edge (complement to Redis rate limiting)
  ├── Gzip compression for API responses
  ├── Static file serving (if any)
  └── Security headers:
        Strict-Transport-Security
        X-Frame-Options: DENY
        X-Content-Type-Options: nosniff
        Content-Security-Policy
        Referrer-Policy

Upstream configuration:
  upstream api {
    server api:8000;
    keepalive 32;                   ← persistent connections to FastAPI
  }

  Rate limiting zones:
    limit_req_zone $binary_remote_addr  zone=global:10m  rate=100r/m;
    limit_req_zone $http_authorization  zone=peruser:10m rate=60r/m;

  Location blocks:
    /api/v1/auth/login    → limit_req zone=global burst=10;
    /api/v1/              → limit_req zone=peruser burst=30;
    /health/              → no rate limit; no auth required
```

## 12.4 Application Configuration (Pydantic Settings)

Environment-specific configuration via `core/config.py`:

```
Settings (read from environment variables / .env file):

  Application:
    APP_NAME: str = "Obelytics"
    ENVIRONMENT: str = "development"   ← development | staging | production
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str                    ← HS256 signing key (min 32 bytes)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

  Database:
    DATABASE_URL: str                  ← asyncpg DSN
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800

  Redis:
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = 50

  MinIO:
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "obelytics"
    MINIO_SECURE: bool = True          ← False for local dev

  Email:
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAIL_FROM: str = "noreply@obelytics.app"

  Worker:
    ARQ_REDIS_URL: str                 ← may differ from app Redis
    WORKER_CONCURRENCY: int = 10

  Rate Limiting:
    RATE_LIMIT_DEFAULT: int = 100       ← requests per minute
    RATE_LIMIT_HEAVY: int = 10          ← for attainment, reports
```

## 12.5 FastAPI Application Factory (lifespan pattern)

```
App Initialization (conceptual, no code):

  lifespan(app):
    STARTUP:
      1. Validate configuration (fail fast if required env vars missing)
      2. Create SQLAlchemy async engine + verify DB connectivity
      3. Create Redis connection pool + verify connectivity
      4. Initialize MinIO client + verify bucket exists
      5. Run Alembic migration check (warn if pending migrations)
      6. Register domain event handlers (EventHandlerRegistry)
      7. Log: startup complete, PID, worker count, environment

    SHUTDOWN:
      1. Complete in-flight requests (graceful timeout: 30s)
      2. Close SQLAlchemy connection pool
      3. Close Redis connection pool
      4. Log: shutdown complete

  Middleware chain (registered in order):
    1. CORSMiddleware (origins from config)
    2. TrustedHostMiddleware (allowed hosts)
    3. CorrelationIDMiddleware
    4. OrganizationContextMiddleware
    5. RateLimitMiddleware
    6. AuditMiddleware (post-response hook)

  Exception handlers registered:
    EntityNotFoundError     → 404 { code, message, entity_type, entity_id }
    PermissionDeniedError   → 403 { code, message, required_permission }
    BusinessRuleViolation   → 422 { code, message, rule_id, details }
    ValidationError         → 422 { code, errors[] }
    TokenExpiredError       → 401 { code, message }
    ConflictError           → 409 { code, message }
    UnhandledException      → 500 { code: "INTERNAL_ERROR" } + log full traceback

  Routers included:
    /api/v1/auth         ← iam.router.auth_router
    /api/v1/users        ← iam.router.user_router
    /api/v1/roles        ← iam.router.role_router
    /api/v1/org          ← org.router
    /api/v1/departments  ← org.router
    /api/v1/programs     ← org.router
    /api/v1/config       ← ref_data.router
    /api/v1/curricula    ← curriculum.router
    /api/v1/courses      ← curriculum.router
    /api/v1/batches      ← curriculum.router
    /api/v1/terms        ← curriculum.router
    /api/v1/offerings    ← curriculum.router
    /api/v1/pos          ← obe.router.po_router
    /api/v1/cos          ← obe.router.co_router
    /api/v1/mappings     ← obe.router.mapping_router
    /api/v1/assessments  ← assessment.router
    /api/v1/marks        ← assessment.router
    /api/v1/results      ← assessment.router
    /api/v1/attainment   ← attainment.router
    /api/v1/approvals    ← approval.router
    /api/v1/notifications← notification.router
    /api/v1/reports      ← reporting.router
    /api/v1/accreditation← accreditation.router
    /api/v1/audit        ← audit.router
    /health              ← health check router (no auth, no versioning)
```

## 12.6 Health Check Endpoints

```
GET /health/live
  → Always returns 200 { status: "ok" }
  → Used by Docker and load balancer for liveness probe
  → Fails only if the Python process has crashed

GET /health/ready
  → Checks: DB (SELECT 1), Redis (PING), MinIO (bucket stat)
  → Returns 200 { status: "ready", checks: { db: "ok", redis: "ok", minio: "ok" } }
  → Returns 503 { status: "degraded", checks: { ... } } if any check fails
  → Used by load balancer: remove from rotation if 503

GET /health/info
  → Returns: { version, environment, uptime_seconds, python_version }
  → No auth required
  → Used by ops team and monitoring dashboards
```

## 12.7 Migration Strategy

Alembic migrations are the only mechanism for database schema changes. No manual DDL in production.

```
Migration Workflow:
  1. Developer changes SQLAlchemy models in module models.py
  2. Developer runs: alembic revision --autogenerate -m "add_co_locked_at_column"
  3. Generated migration is reviewed (NEVER apply without review)
  4. Migration added to PR — code review includes migration review
  5. On PR merge to main: CI runs alembic check (fails if model != DB)
  6. On deployment: alembic upgrade head runs before new API containers start
     (handled by a one-off "migration" container in docker-compose.prod.yml)
  7. Rollback: alembic downgrade -1 (each migration must have a valid downgrade)

Migration safety rules:
  - Never drop columns without a 2-step deployment (first: add nullable, second: use, third: remove)
  - Never add NOT NULL columns without a default or concurrent backfill
  - Never rename columns (add new + migrate data + remove old)
  - All migrations run in transactions (PostgreSQL DDL is transactional)
```

## 12.8 Observability Stack

```
Structured Logging (JSON):
  All log entries include:
    { timestamp, level, logger, message,
      correlation_id, user_id, org_id,
      module, operation, duration_ms,
      error_type, error_message (if applicable) }
  
  Shipped to: stdout → Docker log driver → ELK / Loki / CloudWatch

Metrics (Prometheus):
  GET /metrics  → Prometheus scrape endpoint
  Exported metrics:
    - http_request_duration_seconds (histogram, by method + endpoint + status)
    - http_requests_total (counter, by method + endpoint + status)
    - db_pool_size, db_pool_checked_out (gauge)
    - redis_cache_hits_total, redis_cache_misses_total (counter)
    - arq_jobs_completed_total, arq_jobs_failed_total (counter, by task)
    - active_users_gauge (gauge, from auth cache)

Tracing (OpenTelemetry):
  - Instrumented via opentelemetry-instrumentation-fastapi
  - Traces span: HTTP handler → service → repository → DB query
  - Correlation ID is propagated as trace ID
  - Export to Jaeger or OTLP endpoint

Alerting Rules (Prometheus Alertmanager):
  - API error rate > 5% for 5 minutes → alert
  - DB pool exhaustion (checked_out > 90% of pool_size) → alert
  - ARQ job failure rate > 10% → alert
  - Response P99 > 2000ms → alert
  - Pending outbox events > 100 for 60 seconds → alert
```

## 12.9 Security Hardening

| Layer | Measure |
|---|---|
| **Network** | MinIO and PostgreSQL ports not exposed outside Docker network |
| **Network** | MinIO console (9001) not proxied by Nginx; admin access via SSH tunnel only |
| **Application** | `SECRET_KEY` and all credentials injected via environment variables; never in code or git |
| **Application** | SQL injection prevented by SQLAlchemy parameterized queries exclusively |
| **Application** | File upload: content_type and size validated server-side before pre-signed URL generation |
| **Application** | All user inputs pass through Pydantic validation before reaching service layer |
| **HTTP** | CORS restricted to known frontend origin(s) in production |
| **HTTP** | Security headers enforced by Nginx (HSTS, X-Frame-Options, CSP) |
| **HTTP** | TLS 1.2+ only; TLS 1.0/1.1 disabled in Nginx |
| **Auth** | Bcrypt with cost factor 12 for password hashing |
| **Auth** | Refresh token family detection for theft detection |
| **Auth** | HttpOnly + Secure + SameSite=Strict cookies for refresh tokens |
| **Audit** | All 403 events logged with full context (user, permission, resource) |
| **Database** | Application DB role: no DROP, no TRUNCATE, no CREATE |
| **Database** | Audit schema: application role has INSERT only (no UPDATE, no DELETE) |
| **Container** | Non-root user inside containers |
| **Container** | Read-only filesystem for API and Worker containers |
| **Secrets** | Docker Secrets or environment variable injection; never baked into images |

---

*End of Backend Architecture Document — OBE Accreditation Management Platform v1.0*
