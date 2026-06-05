# Obelytics Backend — Setup Guide

Complete instructions for getting the backend running on a fresh machine.

---

## Prerequisites

Install these before anything else:

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12+ | [python.org](https://python.org) — check "Add to PATH" on Windows |
| Docker Desktop | Latest | Runs Postgres, Redis, MinIO |
| Git | Any | To clone the repo |

Verify:
```powershell
python --version   # Python 3.12.x
docker --version   # Docker version 27.x
```

---

## 1. Clone the Repository

```powershell
git clone <repo-url>
cd obelytics
```

---

## 2. Start Infrastructure (Docker)

From the `backend/` directory, spin up Postgres 16, Redis, and MinIO:

```powershell
cd backend
docker compose up -d
```

Wait for all three containers to be healthy (~15 seconds):

```powershell
docker compose ps
# All three services should show "(healthy)"
```

Ports used (intentionally non-standard to avoid conflicts):

| Service | Host port | Default password |
|---|---|---|
| PostgreSQL 16 | `5434` | `obelytics_dev` |
| Redis 7.2 | `6381` | `redis_dev` |
| MinIO | `9000` (API), `9001` (console) | `minioadmin` |

---

## 3. Create the Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
```

Install all dependencies (prod + dev + test):

```powershell
pip install -r requirements-dev.txt
```

---

## 4. Configure Environment Variables

Copy the example file and use it as-is for local development:

```powershell
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
```

The defaults in `.env.example` match the Docker Compose ports and passwords exactly — no edits needed for local dev.

If you need a fresh `SECRET_KEY` for any environment:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 5. Run Database Migrations

```powershell
alembic upgrade head
```

This creates all schemas and tables. Nine migration files are applied in order (`0001` → `0009`).

Verify the migration ran cleanly:

```powershell
alembic current
# Should print the latest revision hash with "(head)"
```

---

## 6. Seed Reference Data

Load the built-in reference data (assessment types, course types, permission manifest):

```powershell
python -m scripts.seed_reference_data
```

Create the first super-admin user (required to log in):

```powershell
python -m scripts.seed_superadmin
```

Default credentials created by the script:

| Field | Value |
|---|---|
| Email | `admin@obelytics.local` |
| Password | `Admin@123` |

**To create a second superadmin** (pass the same `--org-id` printed on first run):

```powershell
python -m scripts.seed_superadmin --email you@example.com --password "YourPassword123" --org-id <printed-org-id>
```

**To change the default password on first run:**

```powershell
python -m scripts.seed_superadmin --password "MyStrongPassword123"
```

Note: if the superadmin already exists the script skips creation — it will not update the password. To change an existing password use the API's change-password endpoint after logging in.

---

## 7. Start the API Server

```powershell
uvicorn app.main:app --reload --port 8000
```

The API is now live at:

| URL | Purpose |
|---|---|
| `http://localhost:8000` | API root |
| `http://localhost:8000/docs` | Swagger UI (interactive) |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/api/v1/health` | Health check |

---

## 8. Run Tests

Tests run against a real Postgres database (a separate `obelytics_test` schema is created automatically by the test fixtures).

Make sure Docker is running and `.env` is configured, then:

```powershell
pytest
```

Run with coverage:

```powershell
pytest --cov=app --cov-report=term-missing
```

Run a single test file:

```powershell
pytest tests/integration/test_auth_flow.py -v
```

Run a single test:

```powershell
pytest tests/integration/test_auth_flow.py::test_login_success -v
```

---

## Day-to-Day Commands

Once set up, a typical session is:

```powershell
cd backend
docker compose up -d          # start infra (if not already running)
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Stop everything when done:

```powershell
docker compose down           # stops containers, keeps data volumes
# docker compose down -v      # stops containers AND wipes all data
```

---

## Troubleshooting

**`alembic: command not found`**
→ The venv is not activated. Run `.venv\Scripts\activate` first.

**`connection refused` on Postgres**
→ Docker containers are not running. Run `docker compose up -d` and wait for `(healthy)`.

**`address already in use` on port 5434 / 6381 / 8000**
→ Another process is using that port. Either stop it or change the port in `.env` and `docker-compose.yml`.

**`ModuleNotFoundError`**
→ The venv is not activated or `pip install -r requirements-dev.txt` was not run.

**Migration fails with `relation already exists`**
→ Run `alembic downgrade base` then `alembic upgrade head` to reset, or wipe the DB volume with `docker compose down -v`.
