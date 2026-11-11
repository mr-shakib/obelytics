# AGENTS.md — Obelytics

## Project overview

OBE (Outcome-Based Education) accreditation management platform. Two sub-projects:

- `backend/` — FastAPI (Python 3.12), SQLAlchemy async (asyncpg), Alembic, PostgreSQL 16, Redis, MinIO
- `frontend/` — Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, shadcn (base-nova style), openapi-fetch, zustand, react-query

Infrastructure (Postgres, Redis, MinIO) runs via Docker Compose in `backend/`.

## Quick start

```powershell
# Terminal 1 — infrastructure
cd backend; docker compose up -d

# Terminal 2 — backend (activate venv first)
cd backend; .venv\Scripts\activate; uvicorn app.main:app --reload --port 8000

# Terminal 3 — frontend
cd frontend; npm run dev
```

Full setup guide: `SETUP.md`

## Commands

### Backend (run from `backend/` with venv activated)

| Command | Purpose |
|---|---|
| `uvicorn app.main:app --reload --port 8000` | Dev server |
| `pytest` | Run all tests (requires Docker running) |
| `pytest tests/integration/test_auth_flow.py::test_login_success -v` | Single test |
| `pytest --cov=app --cov-report=term-missing` | Tests with coverage |
| `ruff check .` | Lint |
| `ruff format .` | Format |
| `alembic upgrade head` | Apply migrations |
| `alembic revision --autogenerate -m "description"` | New migration |
| `python -m scripts.seed_reference_data` | Seed reference data |
| `python -m scripts.seed_superadmin` | Seed super admin |

### Frontend (run from `frontend/`)

| Command | Purpose |
|---|---|
| `npm run dev` | Dev server (port 3000) |
| `npm run build` | Production build |
| `npm run lint` | ESLint |
| `npm run typecheck` | TypeScript type-check (no emit) |
| `npm run generate:types` | Re-generate `types/api.d.ts` from live backend OpenAPI spec (backend must be running) |

## Architecture

### Backend structure

```
backend/app/
├── core/           # config, database, security, redis, storage, middleware
├── modules/        # domain modules (iam, org, curriculum, obe, assessment, attainment, approval, audit, notification, reporting, accreditation, ref_data, cqi, copilot, integrity, ai)
├── shared/         # shared infra (events/outbox)
└── workers/        # arq background worker (reports, integrity reading/audits)
```

- Entry point: `app/main.py` — creates FastAPI app, registers routers
- Config: `app/core/config.py` — pydantic-settings, reads `.env`
- DB: async SQLAlchemy with asyncpg; sync URL uses psycopg2 (for Alembic)
- API prefix: `/api/v1`
- 17 Postgres schemas: `config`, `iam`, `org`, `curriculum`, `obe`, `assessment`, `attainment`, `approval`, `notification`, `events`, `audit`, `accreditation`, `reporting`, `copilot`, `cqi`, `integrity`, `ai`

### Frontend structure

```
frontend/
├── app/
│   ├── (auth)/       # login/register pages
│   ├── (dashboard)/  # main app (sidebar layout)
│   ├── (student)/    # student-facing pages
│   ├── api/          # BFF route handlers (login, refresh, logout)
│   └── layout.tsx
├── lib/
│   ├── api/          # openapi-fetch client (client.ts, auth.ts)
│   ├── stores/       # zustand stores (auth-store, app-store, notification-store)
│   └── utils.ts
├── types/
│   ├── api.d.ts      # generated from backend OpenAPI spec
│   └── index.ts
└── components/       # shadcn components
```

- Path alias: `@/*` maps to project root
- BFF pattern: auth tokens flow through `app/api/auth/` route handlers; refresh token stored in HttpOnly cookie
- Client-side API calls use `lib/api/client.ts` (openapi-fetch with interceptors)
- `X-Program-Id` header sent on client requests for scoped access

## Testing

- Tests use a **separate `obelytics_test` database** (auto-created from main DB name + `_test` suffix)
- Docker must be running for tests
- pytest-asyncio with `asyncio_mode = "auto"` and session-scoped event loop
- Fixtures: `client` (HTTPX AsyncClient), `db_session`, `auth_headers` (Super Admin), `teacher_auth_headers`, `ml_auth_headers` (Module Leader)
- Each test gets a fresh engine with NullPool (prevents asyncpg cross-loop issues)
- Test structure: `tests/unit/`, `tests/integration/`, `tests/e2e/`

## Migrations

- Sequential naming: `0001_description.py` through `0057_...`
- Auto-generate from model changes: `alembic revision --autogenerate -m "what changed"`
- Always review generated file in `migrations/versions/` before applying
- Run from `backend/` with venv activated

## Key conventions

- Backend: ruff lint rules `E, F, I, N, W`; line length 100; Python 3.12 target
- Frontend: Next.js 16 has breaking changes — check `node_modules/next/dist/docs/` before writing Next.js code (see `frontend/AGENTS.md`)
- All API routes are under `/api/v1` prefix
- CORS must include `http://localhost:3000` for local dev
- Refresh tokens are HttpOnly cookies; access tokens are in-memory (zustand)

## AI Congress upgrade (Oct–Dec 2026)

Planned AI features (assessment integrity auditor, CQI agent, accreditation evidence writer, copilot v2, AI gateway) are specified in `docs/ai-congress/`. Read `docs/ai-congress/README.md` before working on any AI feature — it lists the rules every AI feature must follow (advisory only, no student data to external models, fixed tools, traceable, overridable, measured).

Every model call goes through the AI gateway (`backend/app/modules/ai/`): it picks the organization's provider per feature (local Ollama or a hosted OpenAI-compatible API), redacts personal data before external calls, and logs usage to `ai.calls`. Never call a model API directly from a feature. In tests, use `tests/ai_fakes.py` (`FakeBackend`, `use_fake_ai`) — no model server or worker needed.

The integrity auditor (`backend/app/modules/integrity/`) reads papers and runs audits as background jobs: in development they run in the API process (`INTEGRITY_JOB_RUNNER=inline`); in production the arq worker runs them. `scripts/integrity_gold_set.py` builds and scores the faculty gold set — keep its inputs and outputs in `private/`.

`docs/ai-congress/strategy/` is local-only and gitignored. Never commit it; this repo is public. Task status lives in `docs/ai-congress/strategy/00_TRACKER.md` (local).

## Never commit (this repo is public)

- Credentials: `*_credentials.md`, real `.env` files (only `*.example` files are committed), database backups
- Real student or faculty data: faculty lists, real rosters, real marks. Committed setup packages must stay synthetic (`@student.example.edu` emails, sequential IDs)
- Official university documents (e.g. syllabus `.docx` sources)
- `docs/ai-congress/strategy/`
- Put any real institutional data in `private/` (gitignored). When adding a new kind of sensitive file, add a `.gitignore` rule in the same change

## Environment

- Backend `.env` in `backend/` — defaults match Docker Compose (no edits needed for local dev)
- Frontend `.env.local` in `frontend/` — needs `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Non-standard ports: Postgres on **5434**, Redis on **6381** (not defaults)
