# OBE Accreditation Management Platform
## Frontend Architecture — v1.0

> **Framework:** Next.js 15 (App Router)  
> **Based on:** System Blueprint v1.0 + API Contract v1.0  
> **Date:** 2026-06-05

---

## Table of Contents

1. [Technology Stack](#1-technology-stack)
2. [Project Structure](#2-project-structure)
3. [Routing & Page Architecture](#3-routing--page-architecture)
4. [Authentication Flow](#4-authentication-flow)
5. [Permission-Driven UI](#5-permission-driven-ui)
6. [State Management](#6-state-management)
7. [API Client Architecture](#7-api-client-architecture)
8. [Component Architecture](#8-component-architecture)
9. [Data Fetching Strategy](#9-data-fetching-strategy)
10. [Form Architecture](#10-form-architecture)
11. [Layout System](#11-layout-system)
12. [Build & Deployment](#12-build--deployment)

---

# 1. Technology Stack

| Concern | Library | Reason |
|---|---|---|
| Framework | Next.js 15 (App Router) | SSR for initial load, Server Components for data fetching |
| Language | TypeScript (strict mode) | Type safety across API contract |
| Styling | Tailwind CSS 4 | Utility-first, consistent design |
| Component Library | shadcn/ui | Unstyled primitives built on Radix UI; full ownership |
| Icons | Lucide React | Consistent iconography |
| Global State | Zustand | Minimal, testable stores; no boilerplate |
| Server State | TanStack Query v5 | Caching, refetching, optimistic updates, pagination |
| Forms | React Hook Form + Zod | Performance, schema-driven validation |
| API Client | openapi-fetch (typed from OpenAPI spec) | End-to-end type safety from FastAPI → frontend |
| Tables | TanStack Table v8 | Virtualized, sortable, filterable data tables |
| Date Handling | date-fns | Lightweight, tree-shakeable |
| Toast Notifications | Sonner | Simple, accessible |
| Charts | Recharts | CO/PO attainment trend charts |
| PDF Preview | react-pdf | Accreditation report preview |
| Testing | Vitest + React Testing Library + Playwright | Unit, integration, E2E |

**No** class-based components. **No** Redux. **No** global CSS files (Tailwind only).

---

# 2. Project Structure

```
obelytics-frontend/
│
├── app/                              ← Next.js App Router root
│   ├── (auth)/                       ← Route group: unauthenticated pages
│   │   ├── login/page.tsx
│   │   ├── forgot-password/page.tsx
│   │   └── reset-password/page.tsx
│   │
│   ├── (dashboard)/                  ← Route group: authenticated app
│   │   ├── layout.tsx                ← Dashboard shell: sidebar + header
│   │   │
│   │   ├── page.tsx                  ← Dashboard home (role-aware)
│   │   │
│   │   ├── organization/
│   │   │   └── page.tsx              ← Org settings (Super Admin)
│   │   │
│   │   ├── departments/
│   │   │   ├── page.tsx              ← Department list
│   │   │   └── [id]/page.tsx         ← Department detail + HOD history
│   │   │
│   │   ├── programs/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   │
│   │   ├── users/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   │
│   │   ├── roles/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   │
│   │   ├── ref-data/
│   │   │   └── page.tsx              ← Tabbed reference data manager
│   │   │
│   │   ├── curricula/
│   │   │   ├── page.tsx              ← Curriculum list
│   │   │   └── [id]/
│   │   │       ├── page.tsx          ← Curriculum overview + term structure
│   │   │       ├── courses/page.tsx  ← Course slot manager
│   │   │       └── version/page.tsx  ← Create new version wizard
│   │   │
│   │   ├── courses/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx         ← Course + prerequisites graph
│   │   │
│   │   ├── batches/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   │
│   │   ├── academic-terms/
│   │   │   └── page.tsx
│   │   │
│   │   ├── section-offerings/
│   │   │   ├── page.tsx
│   │   │   └── [id]/
│   │   │       ├── page.tsx          ← Offering overview
│   │   │       ├── faculty/page.tsx  ← Faculty assignments
│   │   │       ├── students/page.tsx ← Enrollment roster
│   │   │       └── assessments/page.tsx
│   │   │
│   │   ├── program-outcomes/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   │
│   │   ├── course-outcomes/
│   │   │   ├── page.tsx              ← CO list (filtered by curriculum+course)
│   │   │   └── [id]/
│   │   │       ├── page.tsx          ← CO detail + approval status
│   │   │       └── mappings/page.tsx ← CP/CA/KP mapping editor
│   │   │
│   │   ├── mappings/
│   │   │   └── co-po/
│   │   │       ├── page.tsx          ← Mapping set list
│   │   │       └── [id]/page.tsx     ← Interactive matrix editor
│   │   │
│   │   ├── assessments/
│   │   │   ├── page.tsx
│   │   │   └── [id]/
│   │   │       ├── page.tsx          ← Assessment config + CO weights
│   │   │       └── marks/page.tsx    ← Marks entry table
│   │   │
│   │   ├── results/
│   │   │   └── [offering_id]/page.tsx ← Result publication workflow
│   │   │
│   │   ├── attainment/
│   │   │   ├── page.tsx              ← Attainment run list
│   │   │   ├── [id]/page.tsx         ← Run detail: CO + PO results
│   │   │   └── trends/page.tsx       ← PO trend charts
│   │   │
│   │   ├── approvals/
│   │   │   └── page.tsx              ← Approval inbox
│   │   │
│   │   ├── reports/
│   │   │   ├── page.tsx              ← Report catalog + run history
│   │   │   └── [run_id]/page.tsx     ← Run status + download
│   │   │
│   │   ├── accreditation/
│   │   │   ├── page.tsx
│   │   │   └── [cycle_id]/page.tsx
│   │   │
│   │   ├── audit/
│   │   │   └── page.tsx              ← Audit log viewer (Super Admin)
│   │   │
│   │   └── notifications/
│   │       └── page.tsx              ← Full notification inbox
│   │
│   ├── (student)/                    ← Route group: student portal
│   │   ├── layout.tsx                ← Minimal layout (no admin sidebar)
│   │   ├── my-curriculum/page.tsx
│   │   ├── my-courses/page.tsx
│   │   ├── my-results/page.tsx
│   │   └── my-profile/page.tsx
│   │
│   ├── api/                          ← Next.js Route Handlers (BFF)
│   │   └── auth/
│   │       └── refresh/route.ts      ← Handles token refresh (cookie access)
│   │
│   ├── globals.css                   ← Tailwind base import only
│   ├── layout.tsx                    ← Root layout: providers, fonts
│   └── not-found.tsx
│
├── components/
│   ├── ui/                           ← shadcn/ui primitives (auto-generated)
│   ├── layout/                       ← Shell, sidebar, header, breadcrumb
│   ├── shared/                       ← Cross-module reusable components
│   └── modules/                      ← Module-specific components
│       ├── obe/
│       ├── assessment/
│       └── attainment/
│
├── lib/
│   ├── api/                          ← Typed API client
│   ├── auth/                         ← Auth utilities
│   ├── permissions/                  ← Permission check hooks
│   ├── stores/                       ← Zustand stores
│   └── utils.ts                      ← cn(), formatDate(), etc.
│
├── hooks/                            ← Custom React hooks
├── types/                            ← Shared TypeScript types
├── public/                           ← Static assets
│
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

# 3. Routing & Page Architecture

## 3.1 Route Groups

| Group | Path Prefix | Who Accesses | Auth Required |
|---|---|---|---|
| `(auth)` | `/login`, `/forgot-password`, etc. | Anyone | No — redirects to dashboard if already authed |
| `(dashboard)` | All admin/faculty paths | All non-student roles | Yes — redirects to `/login` |
| `(student)` | `/my-*` paths | Students only | Yes — redirects to `/login` |

## 3.2 Route Protection Middleware

`middleware.ts` at the root intercepts all requests:

```
Middleware logic:
  1. Read access_token from memory (not possible from middleware)
     OR read a non-httponly "session" cookie that indicates auth status
  2. IF accessing (auth) routes AND session exists → redirect to /
  3. IF accessing (dashboard) or (student) routes AND no session → redirect to /login
  4. IF accessing (dashboard) routes AND user is Student → redirect to /my-curriculum
  5. IF accessing (student) routes AND user is not Student → redirect to /

Note: The access_token itself is NOT in a cookie (it's in memory).
      Middleware uses a lightweight "auth-status" cookie (not the token) to decide routing.
      Actual API calls validate the real JWT.
```

## 3.3 Page Data Fetching Model

Each page uses the **Server Component + Client Component split**:

```
page.tsx (Server Component)
  └── Fetches initial data server-side (faster TTFB, no loading flash)
  └── Passes data as props to Client Component
  └── Client Component owns mutation state, user interactions, refetching

Example: course-outcomes/page.tsx
  Server: Fetch CO list server-side → pass to COListClient
  Client: COListClient uses TanStack Query to refetch on mutations
```

For pages requiring real-time feedback (marks entry, approval inbox), use Client Components with TanStack Query directly.

---

# 4. Authentication Flow

## 4.1 Token Storage

| Token | Storage | Rationale |
|---|---|---|
| Access Token (JWT, 15 min) | In-memory only (Zustand `authStore`) | Cannot be stolen via XSS; lost on page refresh (acceptable) |
| Refresh Token (7 days) | HttpOnly Secure cookie | Set by server; inaccessible to JS; sent automatically |

**On page refresh:** Access token is gone. The app automatically calls `POST /api/auth/refresh` (the Next.js Route Handler, which has access to the HttpOnly cookie) to get a new access token before rendering protected content.

## 4.2 Auth Initialization

```
app/layout.tsx renders AuthProvider

AuthProvider behavior on mount:
  1. Check authStore → if access_token exists → already initialized, render children
  2. Call POST /api/auth/refresh (Next.js route handler)
     → Route handler reads httpOnly cookie, calls backend /auth/refresh
     → Returns new access_token
  3. IF success:
     a. Store access_token in authStore
     b. Call GET /me → store user + permission manifest in authStore
     c. Render app
  4. IF failure (no cookie, cookie expired, revoked):
     a. Clear authStore
     b. Redirect to /login

This completes in < 300ms on warm connections.
Silent re-auth happens every 14 minutes (access token expires at 15 min).
```

## 4.3 Login Flow

```
LoginPage → LoginForm (client component)
  1. User submits { email, password }
  2. POST /auth/login
  3. Server sets refresh_token HttpOnly cookie
  4. Response body contains access_token
  5. Store access_token in authStore.accessToken
  6. GET /me → store user + manifest in authStore
  7. Router.push('/') → dashboard
```

## 4.4 Logout Flow

```
  1. POST /auth/logout (revokes refresh token server-side)
  2. Clear authStore (access token gone from memory)
  3. Router.push('/login')
  4. HttpOnly cookie cleared by server (Set-Cookie: refresh_token=; Max-Age=0)
```

---

# 5. Permission-Driven UI

## 5.1 Permission Manifest in Zustand

```typescript
// authStore shape (conceptual)
{
  accessToken: string | null,
  user: {
    id: string, email: string, first_name: string, last_name: string,
    faculty_type: string, department: { id, name } | null
  } | null,
  manifest: {
    permissions: string[],             // ["co.approve", "curriculum.read", ...]
    scope: {
      programs: { id: string, name: string, acronym: string }[],
      is_global: boolean
    },
    offering_ids: string[]             // pre-computed for ML/Teacher
  } | null
}
```

## 5.2 Permission Check Hook

```typescript
// hooks/usePermission.ts (conceptual)
usePermission(permissionCode: string): boolean
  → reads authStore.manifest.permissions
  → returns true if permissionCode is in the array

useHasAnyPermission(codes: string[]): boolean
  → returns true if ANY code is in permissions

// Usage in components:
const canApprove = usePermission('co.approve')
// Conditionally render:
{canApprove && <Button>Approve CO</Button>}
```

**Rule:** Components NEVER check role names. They ONLY check permission codes.

## 5.3 Navigation Visibility

The sidebar navigation is generated dynamically from a navigation config that pairs each nav item with its required permission:

```typescript
// lib/navigation.ts (conceptual structure)
const NAV_CONFIG = [
  { label: 'Dashboard',         href: '/',                  permission: null },
  { label: 'Organization',      href: '/organization',      permission: 'system.organization.configure' },
  { label: 'Departments',       href: '/departments',       permission: 'department.read' },
  { label: 'Programs',          href: '/programs',          permission: 'program.read' },
  { label: 'Users',             href: '/users',             permission: 'user.read' },
  { label: 'Roles',             href: '/roles',             permission: 'system.roles.create' },
  { label: 'Reference Data',    href: '/ref-data',          permission: 'config.bloom.manage' },
  { label: 'Curricula',         href: '/curricula',         permission: 'curriculum.read' },
  { label: 'Courses',           href: '/courses',           permission: 'course.read' },
  { label: 'Batches',           href: '/batches',           permission: 'batch.read' },
  { label: 'Academic Terms',    href: '/academic-terms',    permission: 'curriculum.read' },
  { label: 'Offerings',         href: '/section-offerings', permission: 'curriculum.read' },
  { label: 'Program Outcomes',  href: '/program-outcomes',  permission: 'po.read' },
  { label: 'Course Outcomes',   href: '/course-outcomes',   permission: 'co.read' },
  { label: 'CO-PO Mapping',     href: '/mappings/co-po',    permission: 'mapping.co_po.read' },
  { label: 'Assessments',       href: '/assessments',       permission: 'assessment.read' },
  { label: 'Results',           href: '/results',           permission: 'result.read.section' },
  { label: 'Attainment',        href: '/attainment',        permission: 'attainment.read' },
  { label: 'Approvals',         href: '/approvals',         permission: null },  // always shown
  { label: 'Reports',           href: '/reports',           permission: 'report.export' },
  { label: 'Accreditation',     href: '/accreditation',     permission: 'accreditation.cycle.manage' },
  { label: 'Audit Log',         href: '/audit',             permission: 'system.audit.read' },
]
```

The sidebar renders only items where `permission === null` OR `usePermission(permission) === true`.

## 5.4 Program Selector

Users with PROGRAM scope (Coordinator, ML, Teacher) see a program selector dropdown in the header. It is populated from `manifest.scope.programs`. The selected program is stored in Zustand `appStore.activeProgramId` and sent with every API request as the `X-Program-Id` header.

Students do not see a program selector. Their program is derived from their enrollment server-side.

## 5.5 Action Button Guards

Every state-changing action button requires TWO checks before rendering:

```
1. Permission check: usePermission('co.approve') === true
2. Entity state check: co.status === 'UNDER_REVIEW'

Both must be true. Show button only when both pass.
```

This prevents showing an "Approve" button when the CO has already been approved.

---

# 6. State Management

## 6.1 Zustand Stores

Three stores cover all global state. Everything else is local React state or TanStack Query cache.

### authStore

```typescript
// Owns: authentication state, user identity, permission manifest
{
  accessToken: string | null
  user: UserProfile | null
  manifest: PermissionManifest | null
  isInitialized: boolean    // true after first auth check completes
  isAuthenticated: boolean  // derived: accessToken !== null

  // Actions
  setAuth(token, user, manifest): void
  clearAuth(): void
  refreshManifest(): Promise<void>  // re-fetch /me after role changes
}
```

### appStore

```typescript
// Owns: UI-level application preferences
{
  activeProgramId: string | null   // Program selector state
  sidebarCollapsed: boolean
  theme: 'light' | 'dark'

  // Actions
  setActiveProgram(id: string | null): void
  toggleSidebar(): void
}
```

### notificationStore

```typescript
// Owns: in-app notification badge count
{
  unreadCount: number

  // Actions
  setUnreadCount(count: number): void
  decrementUnread(): void
  incrementUnread(): void
}
```

**Rule:** No server state in Zustand. Server state lives in TanStack Query cache only.

---

# 7. API Client Architecture

## 7.1 Type-Safe Client Generation

The FastAPI backend exposes an OpenAPI JSON spec at `/openapi.json`. The frontend generates a typed client from this spec:

```
Tool: openapi-typescript → generates types/api.d.ts
Tool: openapi-fetch → typed HTTP client using the generated types

Generation command (runs in CI or on demand):
  npx openapi-typescript http://localhost:8000/openapi.json -o types/api.d.ts
```

This gives end-to-end type safety: if the backend renames a field, TypeScript compilation fails on the frontend.

## 7.2 Client Setup

```typescript
// lib/api/client.ts (conceptual)

Base client configured with:
  - baseUrl: process.env.NEXT_PUBLIC_API_URL + '/api/v1'
  - Request interceptor:
      Reads authStore.accessToken → adds Authorization: Bearer <token>
      Reads appStore.activeProgramId → adds X-Program-Id header if set
  - Response interceptor:
      On 401: attempt token refresh → retry original request once
      On 401 after retry: clearAuth() → redirect to /login
      On 403: toast("You don't have permission for this action")
      On 409: re-throw as BusinessRuleError for component-level handling
      On 500: toast("Something went wrong") → log to observability
```

## 7.3 Module API Functions

Each module has its own API functions file that wraps the typed client:

```
lib/api/
├── auth.ts          → login(), refresh(), logout(), getMe()
├── users.ts         → listUsers(), createUser(), updateUser(), assignRole()
├── curricula.ts     → listCurricula(), createCurriculum(), versionCurriculum()
├── courses.ts       → listCourses(), createCourse(), addPrerequisite()
├── course-outcomes.ts → listCOs(), createCO(), submitCO(), approveCO()
├── mappings.ts      → getMappingSet(), updateEntries(), publishMapping()
├── assessments.ts   → listAssessments(), configureAssessment(), openMarks()
├── marks.ts         → bulkEnterMarks(), updateMark(), getMarksByAssessment()
├── results.ts       → getResult(), submitResult(), approveML(), approvePC(), publish()
├── attainment.ts    → getConfig(), initiateRun(), getRun(), publishRun(), getTrend()
├── reports.ts       → listDefinitions(), requestRun(), getRunStatus(), getDownloadUrl()
└── notifications.ts → getInbox(), getUnreadCount(), markRead()
```

---

# 8. Component Architecture

## 8.1 Three-Tier Component Model

```
Tier 1: UI Primitives (components/ui/)
  → shadcn/ui generated components: Button, Input, Select, Dialog, Table, etc.
  → Never contain business logic
  → Fully reusable anywhere

Tier 2: Shared Components (components/shared/)
  → Business-aware but cross-module: DataTable, StatusBadge, PermissionGate,
     ProgramSelector, PageHeader, ConfirmDialog, FileDownloadButton
  → Know about permissions and entity states
  → Do not call API directly

Tier 3: Module Components (components/modules/{module}/)
  → Specific to one domain: COListTable, MappingMatrix, MarksEntryGrid,
     AttainmentResultCard, ApprovalInboxItem
  → May call API hooks
  → Encapsulate module-specific display logic
```

## 8.2 Key Shared Components

### PermissionGate

```typescript
// Renders children only if user has the required permission
// Usage: <PermissionGate permission="co.approve"><ApproveButton /></PermissionGate>
// Optional fallback for unauthorized state
<PermissionGate permission="co.approve" fallback={<span>View only</span>}>
  <Button>Approve CO</Button>
</PermissionGate>
```

### DataTable (built on TanStack Table)

```
Props: columns[], data[], pagination, filters, onRowClick?, loading
Features:
  - Server-side pagination (page, size passed to API)
  - Column sorting (sort param passed to API)
  - Search/filter bar
  - Row selection for bulk actions
  - Responsive: collapses columns on mobile
```

### StatusBadge

```typescript
// Renders colored pill for entity status values
// <StatusBadge status="PUBLISHED" /> → green pill
// <StatusBadge status="DRAFT" /> → gray pill
// Knows all status values from all entity types
```

### WorkflowTimeline

```
Shows approval chain state:
  [Teacher] →submitted→ [Module Leader] →approved→ [Coordinator] →published→
  Each step shows: actor name, timestamp, comments (if any)
  Used on: CO detail page, result publication page
```

## 8.3 Module-Specific Components

### MappingMatrix (CO-PO)

```
Visual grid: rows = COs, columns = POs
Each cell: dropdown or toggle for weight (empty / 1 / 2 / 3)
Read-only mode when mapping is PUBLISHED
Highlights cells by bloom domain color
Shows row/column totals for distribution analysis
Sticky headers for large matrices (12 POs × 6+ COs)
On cell change: debounced PATCH to /mappings/co-po/{id}/entries
```

### MarksEntryGrid

```
Spreadsheet-like table:
  Rows = enrolled students
  Columns = assessments (configured for this offering)
  Each cell = numeric input with validation (0 to total_marks, or absent checkbox)

Features:
  - Tab navigation between cells (like Excel)
  - Bulk paste from clipboard
  - Auto-save on blur (debounced PATCH /marks/{id})
  - Cells locked (read-only) after result publication
  - Missing mark indicator (red outline)
  - Running totals column (weighted sum)
```

### AttainmentResultCard

```
Shows per-CO or per-PO attainment:
  - Gauge chart (0-100%)
  - Threshold line indicator
  - is_threshold_met badge
  - Students attempted / attained counts

Used in: attainment run detail page
```

### COStatusStepper

```
Horizontal stepper showing CO lifecycle:
  DRAFT → SUBMITTED → UNDER_REVIEW → APPROVED → PUBLISHED → LOCKED
  Current state highlighted. Completed states checkmarked.
  Next action button shown below stepper (Submit / Approve / Publish)
  Action button only shown if user has permission AND state allows it
```

---

# 9. Data Fetching Strategy

## 9.1 TanStack Query Setup

```typescript
// Configured in app/layout.tsx via QueryClientProvider
QueryClient settings:
  staleTime: 60_000      // 1 minute before data is considered stale
  gcTime: 300_000        // 5 minutes before unused data is garbage collected
  retry: 2               // 2 retries on network failure
  refetchOnWindowFocus: false  // Reduces unnecessary requests for academic data
```

## 9.2 Query Key Convention

Query keys are structured for precise invalidation:

```typescript
// Query key factory pattern:
queryKeys = {
  curricula: {
    all: ['curricula'],
    list: (filters) => ['curricula', 'list', filters],
    detail: (id) => ['curricula', id]
  },
  courseOutcomes: {
    all: ['course-outcomes'],
    list: (curriculumId, courseId) => ['course-outcomes', 'list', curriculumId, courseId],
    detail: (id) => ['course-outcomes', id]
  },
  marks: {
    byAssessment: (assessmentId) => ['marks', 'assessment', assessmentId],
    byEnrollment: (enrollmentId) => ['marks', 'enrollment', enrollmentId]
  }
}
```

## 9.3 Mutation + Invalidation Pattern

Every mutation invalidates the relevant query cache entry:

```typescript
// Example: Submit CO
useMutation({
  mutationFn: (id) => api.submitCO(id),
  onSuccess: (data) => {
    // Invalidate CO detail and list
    queryClient.invalidateQueries({ queryKey: queryKeys.courseOutcomes.detail(data.id) })
    queryClient.invalidateQueries({ queryKey: queryKeys.courseOutcomes.all })
    // Invalidate approval inbox
    queryClient.invalidateQueries({ queryKey: ['approvals', 'inbox'] })
    toast.success('CO submitted for approval')
  },
  onError: (error) => {
    toast.error(error.message)
  }
})
```

## 9.4 Async Job Polling

For long-running async jobs (report generation, attainment calculation):

```typescript
// Polling with TanStack Query:
useQuery({
  queryKey: ['attainment', 'run', runId],
  queryFn: () => api.getAttainmentRun(runId),
  refetchInterval: (data) => {
    if (data?.status === 'CALCULATED' || data?.status === 'PUBLISHED') return false
    return 3000  // poll every 3 seconds while INITIATED
  },
  // Exponential backoff: 3s → 6s → 12s → 30s → stop at 60s
})
```

---

# 10. Form Architecture

## 10.1 Pattern

All forms use **React Hook Form + Zod**. No form uses uncontrolled inputs or manual state management.

```
Schema → Zod validation schema (mirrors backend Pydantic model exactly)
Form   → React Hook Form (useForm with zodResolver)
UI     → shadcn/ui FormField, FormItem, FormLabel, FormMessage components
Submit → useMutation from TanStack Query

Error display:
  - Field errors: shown inline below each field (from Zod)
  - API 422 errors: mapped to field errors by field name
  - API 409 errors: shown in a form-level alert
  - API 403 errors: redirect or toast (handled by API client interceptor)
```

## 10.2 Complex Forms

### CO Creation Form

```
Fields: curriculum_id (dropdown), course_id (dropdown filtered by curriculum),
        code (text, auto-suggested as CO{n+1}),
        statement (textarea, 500 char max),
        bloom_level_id (grouped dropdown by bloom domain)
Validation:
  - CO code: uppercase alphanumeric, unique per curriculum+course (async check)
  - Statement: min 20 chars
```

### Marks Entry

Marks entry does NOT use React Hook Form. It uses a custom `useMarksGrid` hook that manages a 2D cell state (students × assessments) with debounced auto-save. This is a data-entry grid, not a traditional form.

### CO-PO Mapping Matrix

The mapping matrix is a custom interactive grid component (not a form). Each cell change triggers an optimistic update in TanStack Query cache and a debounced API call.

---

# 11. Layout System

## 11.1 Dashboard Layout

```
┌────────────────────────────────────────────────────────────────┐
│  HEADER                                                         │
│  [Logo] [Program Selector ▼]          [🔔 3] [User Menu ▼]     │
├─────────────┬──────────────────────────────────────────────────┤
│  SIDEBAR    │  MAIN CONTENT AREA                                │
│             │                                                   │
│  Navigation │  [Breadcrumb]                                     │
│  items      │  [Page Header + Action Buttons]                   │
│  filtered   │                                                   │
│  by         │  Page-specific content                            │
│  permission │                                                   │
│             │                                                   │
│  [Collapse] │                                                   │
└─────────────┴──────────────────────────────────────────────────┘
```

## 11.2 Student Portal Layout

```
┌────────────────────────────────────────────────────────────────┐
│  HEADER                                                         │
│  [Logo] [Student: John Doe]               [🔔] [Logout]        │
├────────────────────────────────────────────────────────────────┤
│  TOP NAV TABS                                                   │
│  [My Curriculum] [My Courses] [My Results] [My Profile]        │
├────────────────────────────────────────────────────────────────┤
│  CONTENT                                                        │
└────────────────────────────────────────────────────────────────┘
```

## 11.3 Notification Badge

The notification bell in the header polls `GET /notifications/unread-count` every 60 seconds and updates the `notificationStore.unreadCount`. This drives the badge number shown on the bell icon.

---

# 12. Build & Deployment

## 12.1 Environment Variables

```bash
# .env.local (development)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=Obelytics

# .env.production
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_APP_NAME=Obelytics
```

`NEXT_PUBLIC_*` variables are inlined at build time. The refresh token Route Handler runs on the Next.js server and can access the HttpOnly cookie.

## 12.2 Docker Container

```dockerfile
# Multi-stage build
Stage 1 (deps):    npm ci --only=production
Stage 2 (builder): npm run build
Stage 3 (runner):  Minimal node:20-alpine, copy .next/standalone
```

The frontend runs as a Node.js server (not static export) to support:
- Server Components with data fetching
- Route Handlers for token refresh
- Middleware for route protection

## 12.3 Nginx Integration

Nginx routes:
- `/api/*` → FastAPI backend (port 8000)
- `/*` → Next.js frontend (port 3000)
- Static assets from Next.js served with aggressive cache headers

## 12.4 OpenAPI Type Generation in CI

```yaml
# CI step (runs before TypeScript compilation)
- name: Generate API types
  run: |
    npx openapi-typescript ${{ env.API_URL }}/openapi.json -o types/api.d.ts
    
- name: Type check
  run: npx tsc --noEmit
```

This ensures the frontend fails to build if the API contract changes incompatibly.

---

*End of Frontend Architecture — OBE Accreditation Management Platform v1.0*
