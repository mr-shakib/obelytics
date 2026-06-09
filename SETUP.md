# Obelytics — Full Stack Setup Guide

Complete instructions for getting the entire platform running on a fresh machine.

---

## Stack Overview

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 15 (App Router), TypeScript, Tailwind CSS |
| **Backend** | FastAPI, Python 3.12, SQLAlchemy (async), Alembic |
| **Database** | PostgreSQL 16 — 13 schemas, 51 tables |
| **Cache / Queue** | Redis 7.2 |
| **File Storage** | MinIO (S3-compatible) |
| **Container** | Docker Compose |

---

## Prerequisites

Install these before anything else:

| Tool | Version | Download |
|---|---|---|
| **Python** | 3.12+ | [python.org](https://python.org) — check "Add to PATH" on Windows |
| **Node.js** | 20+ | [nodejs.org](https://nodejs.org) (LTS recommended) |
| **Docker Desktop** | Latest | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop) |
| **Git** | Any | [git-scm.com](https://git-scm.com) |

Verify everything is installed:

```powershell
python --version    # Python 3.12.x
node --version      # v20.x or higher
npm --version       # 10.x or higher
docker --version    # Docker version 27.x
git --version
```

---

## 1. Clone the Repository

```powershell
git clone <repo-url>
cd obelytics
```

The project has two sub-projects:

```
obelytics/
├── backend/     ← FastAPI API server
└── frontend/    ← Next.js admin dashboard
```

---

## 2. Infrastructure — Docker Compose

All infrastructure (Postgres, Redis, MinIO) runs in Docker. The `docker-compose.yml` lives inside `backend/`.

### Start all services

```powershell
cd backend
docker compose up -d
```

### Verify everything is healthy

```powershell
docker compose ps
```

All three services should show `(healthy)` — usually takes ~15 seconds.

### Services and ports

| Service | Image | Host Port | Container Port |
|---|---|---|---|
| PostgreSQL 16 | `postgres:16-alpine` | `5434` | `5432` |
| Redis 7.2 | `redis:7.2-alpine` | `6381` | `6379` |
| MinIO | `minio/minio:latest` | `9000` (API), `9001` (console) | same |

### Default credentials

| Service | Username / DB | Password |
|---|---|---|
| PostgreSQL | `obelytics` / `obelytics` | `obelytics_dev` |
| Redis | — | `redis_dev` |
| MinIO | `minioadmin` | `minioadmin` |

### Useful Docker commands

```powershell
docker compose up -d          # start (detached)
docker compose down           # stop — keeps all data volumes
docker compose down -v        # stop AND delete all data (full reset)
docker compose logs -f        # tail all logs
docker compose logs postgres  # logs for a specific service
docker compose restart        # restart all services
```

### Full `docker-compose.yml` reference

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: obelytics
      POSTGRES_USER: obelytics
      POSTGRES_PASSWORD: obelytics_dev
    ports:
      - "5434:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U obelytics"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7.2-alpine
    command: redis-server --requirepass redis_dev
    ports:
      - "6381:6379"
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

---

## 3. Backend Setup

All commands below run from the `backend/` directory.

```powershell
cd backend
```

### 3a. Create the Python virtual environment

```powershell
python -m venv .venv

# Activate — Windows
.venv\Scripts\activate

# Activate — macOS / Linux
# source .venv/bin/activate
```

You should see `(.venv)` in your prompt.

### 3b. Install dependencies

```powershell
pip install -r requirements-dev.txt
```

### 3c. Configure environment variables

```powershell
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux
```

The defaults in `.env.example` match the Docker Compose configuration exactly — **no edits needed for local development**.

Full `.env` reference:

```env
# Application
ENV=development
DEBUG=true
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
POSTGRES_DB=obelytics
POSTGRES_USER=obelytics
POSTGRES_PASSWORD=obelytics_dev

# Redis
REDIS_HOST=localhost
REDIS_PORT=6381
REDIS_PASSWORD=redis_dev

# MinIO (file storage)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

# CORS — must include the frontend URL
ALLOWED_ORIGINS=["http://localhost:3000"]

# Email (Resend — https://resend.com — optional for local dev)
RESEND_API_KEY=re_your_api_key
EMAIL_FROM=Obelytics <noreply@yourdomain.com>
```

Generate a strong `SECRET_KEY` for production:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3d. Run database migrations

```powershell
alembic upgrade head
```

This creates all 13 Postgres schemas and 51 tables across 14 migration files (`0001` → `0014`).

Verify the migration ran cleanly:

```powershell
alembic current
# Should print the latest revision hash with "(head)"
```

See the full migration history:

```powershell
alembic history
```

### 3e. Seed reference data and the first admin user

Load built-in reference data (permissions, assessment types, course types, etc.):

```powershell
python -m scripts.seed_reference_data
```

Create the first super-admin user:

```powershell
python -m scripts.seed_superadmin
```

Default credentials created:

| Field | Value |
|---|---|
| Email | `admin@obelytics.local` |
| Password | `Admin@123` |

**Create a second superadmin** (pass the `--org-id` printed on first run):

```powershell
python -m scripts.seed_superadmin --email you@example.com --password "YourPassword123" --org-id <printed-org-id>
```

**Use a custom password on first run:**

```powershell
python -m scripts.seed_superadmin --password "MyStrongPassword123"
```

> If the superadmin already exists the script skips creation silently. To change an existing password, use the change-password API endpoint after logging in.

### 3f. Start the API server

```powershell
uvicorn app.main:app --reload --port 8000
```

| URL | Purpose |
|---|---|
| `http://localhost:8000` | API root |
| `http://localhost:8000/api/docs` | Swagger UI (interactive API explorer) |
| `http://localhost:8000/api/redoc` | ReDoc documentation |
| `http://localhost:8000/health/live` | Liveness check |
| `http://localhost:8000/health/ready` | Readiness check (DB + Redis) |

---

## 4. Frontend Setup

All commands below run from the `frontend/` directory.

```powershell
cd frontend
```

### 4a. Install dependencies

```powershell
npm install
```

### 4b. Configure environment variables

Create a `.env.local` file in the `frontend/` directory:

```powershell
# Windows
copy .env.local.example .env.local

# Or create it manually
```

Contents of `.env.local`:

```env
# URL of the backend API — must match where uvicorn is running
NEXT_PUBLIC_API_URL=http://localhost:8000

# App display name
NEXT_PUBLIC_APP_NAME=Obelytics
```

> The frontend communicates with the backend through Next.js BFF route handlers (under `app/api/`). The `NEXT_PUBLIC_API_URL` must be reachable from both the browser and the Next.js server process.

### 4c. Start the development server

```powershell
npm run dev
```

The dashboard is now live at **[http://localhost:3000](http://localhost:3000)**

Log in with the credentials created in step 3e:

| Field | Value |
|---|---|
| Email | `admin@obelytics.local` |
| Password | `Admin@123` |

### 4d. Frontend npm scripts reference

| Command | What it does |
|---|---|
| `npm run dev` | Start dev server with hot reload |
| `npm run build` | Production build |
| `npm run start` | Serve the production build |
| `npm run lint` | Run ESLint |
| `npm run typecheck` | TypeScript type-check (no emit) |
| `npm run generate:types` | Re-generate API types from the live backend OpenAPI spec |

### Regenerating API types

When backend routes or schemas change, regenerate the frontend TypeScript types:

```powershell
# Backend must be running on port 8000
npm run generate:types
```

This hits `http://localhost:8000/api/openapi.json` and writes updated types to `types/api.d.ts`.

---

## 5. Full Stack — Day-to-Day Workflow

Once set up, a typical dev session:

**Terminal 1 — Infrastructure**
```powershell
cd backend
docker compose up -d
```

**Terminal 2 — Backend API**
```powershell
cd backend
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux
uvicorn app.main:app --reload --port 8000
```

**Terminal 3 — Frontend**
```powershell
cd frontend
npm run dev
```

Then open **[http://localhost:3000](http://localhost:3000)**.

---

## 6. Creating a New Database Migration

After changing a SQLAlchemy model in `backend/app/modules/`:

```powershell
cd backend
.venv\Scripts\activate

# Auto-generate a migration from model changes
alembic revision --autogenerate -m "describe what changed"

# Review the generated file in migrations/versions/ then apply it
alembic upgrade head
```

Migration files follow the naming convention `00XX_description.py` and are numbered sequentially.

---

## 7. Running Tests

Tests run against a real Postgres database (a separate `obelytics_test` DB is created automatically by the test fixtures). Docker must be running.

```powershell
cd backend
.venv\Scripts\activate
pytest
```

With coverage report:

```powershell
pytest --cov=app --cov-report=term-missing
```

Run a single file or test:

```powershell
pytest tests/integration/test_auth_flow.py -v
pytest tests/integration/test_auth_flow.py::test_login_success -v
```

---

## 8. MinIO File Storage (Optional)

MinIO runs locally and mimics AWS S3. To manage buckets:

1. Open the MinIO console at **[http://localhost:9001](http://localhost:9001)**
2. Log in: username `minioadmin` / password `minioadmin`
3. Create a bucket named `obelytics` (or whatever `MINIO_BUCKET` is set to in `.env`)

For production, replace MinIO with an actual S3 bucket and update `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, and set `MINIO_SECURE=true`.

---

## 9. Production Checklist

Before deploying to production:

- [ ] Set a strong random `SECRET_KEY` (`python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] Set `ENV=production` and `DEBUG=false`
- [ ] Use a managed Postgres instance (not the Docker container)
- [ ] Use a managed Redis instance (e.g., ElastiCache, Upstash)
- [ ] Replace MinIO with AWS S3 or compatible storage, set `MINIO_SECURE=true`
- [ ] Set `ALLOWED_ORIGINS` to your actual frontend domain(s)
- [ ] Configure `RESEND_API_KEY` and `EMAIL_FROM` for real email delivery
- [ ] Set `NEXT_PUBLIC_API_URL` in the frontend to the production API URL
- [ ] Run `alembic upgrade head` against the production database before deploying

---

## Troubleshooting

**`alembic: command not found`**
→ Virtual environment is not activated. Run `.venv\Scripts\activate` first.

**`connection refused` on port 5434 / 6381 / 9000`**
→ Docker containers are not running. Run `docker compose up -d` and wait for `(healthy)`.

**`address already in use` on port 5434 / 6381 / 8000 / 3000`**
→ Another process is using that port. Stop it or change the port in `.env` and `docker-compose.yml`.

**`ModuleNotFoundError` in backend**
→ Virtual environment is not activated or `pip install -r requirements-dev.txt` was not run.

**Migration fails with `relation already exists`**
→ Run `alembic downgrade base` then `alembic upgrade head`, or do a full reset with `docker compose down -v`.

**`NEXT_PUBLIC_API_URL` calls failing (CORS error in browser)**
→ Make sure `ALLOWED_ORIGINS` in `backend/.env` includes `http://localhost:3000`.

**`npm run generate:types` fails**
→ The backend API server must be running on port 8000 before running this command.

**Frontend shows blank page / auth loop**
→ Make sure the backend is running and `.env.local` has the correct `NEXT_PUBLIC_API_URL`. Check the browser console for failed API calls.
