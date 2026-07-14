# Obelytics — Railway Deployment Guide

This guide deploys the **FastAPI backend** and **Next.js frontend** as two separate Railway services, backed by Railway-managed PostgreSQL and Redis.

---

## Architecture

```
                    ┌─────────────────┐
                    │   Railway Cloud  │
                    ├─────────────────┤
   Users ──────────►│   Frontend      │ (Next.js, port $PORT)
                    │   ─────────────►│
                    │   Backend       │ (FastAPI + Gunicorn, port $PORT)
                    │   ─────────────►│
                    │   PostgreSQL    │ (Railway-managed)
                    │   Redis         │ (Railway-managed)
                    │   Cloudinary    │ (external media storage)
                    └─────────────────┘
```

---

## Prerequisites

- A [Railway](https://railway.com) account (Hobby plan or above for production)
- The GitHub repo pushed to GitHub (Railway deploys from Git)
- A [Cloudinary](https://cloudinary.com) account (free tier is generous) for logo/report storage

---

## Step 1: Create the Railway Project

1. Go to [railway.com/new](https://railway.com/new)
2. Click **"Deploy from GitHub repo"**
3. Select your `obelytics` repository
4. Railway will create a project — **do not deploy yet**, we need to add services first

---

## Step 2: Add PostgreSQL

1. In your Railway project, click **"+ New"** → **"Database"** → **"PostgreSQL"**
2. Railway provisions a PostgreSQL instance automatically
3. Note: Railway exposes the connection string as `DATABASE_URL` — we use `DATABASE_URL_OVERRIDE` to read it

---

## Step 3: Add Redis

1. Click **"+ New"** → **"Database"** → **"Redis"**
2. Railway provisions a Redis instance automatically
3. The connection string is exposed as `REDIS_URL` — we use `REDIS_URL_OVERRIDE` to read it

---

## Step 4: Deploy the Backend

### 4a. Create the backend service

1. Click **"+ New"** → **"GitHub Repo"** → select the same repo
2. Go to **Settings** for this service:
   - **Root Directory**: `backend`
   - **Builder**: `Dockerfile` (auto-detected from `backend/Dockerfile`)
   - Railway will use the `railway.toml` in the backend directory

### 4b. Set environment variables

Go to the **Variables** tab and add:

| Variable | Value |
|---|---|
| `DATABASE_URL_OVERRIDE` | `${{Postgres.DATABASE_URL}}` (click "Add Reference" → select PostgreSQL) |
| `REDIS_URL_OVERRIDE` | `${{Redis.REDIS_URL}}` (click "Add Reference" → select Redis) |
| `ENV` | `production` |
| `DEBUG` | `false` |
| `SECRET_KEY` | Generate with: `openssl rand -hex 32` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` |
| `ALLOWED_ORIGINS` | `https://YOUR-FRONTEND-DOMAIN.vercel.app` |
| `CLOUDINARY_CLOUD_NAME` | Your Cloudinary cloud name |
| `CLOUDINARY_UPLOAD_PRESET` | Your Cloudinary unsigned upload preset |
| `CLOUDINARY_API_KEY` | Your Cloudinary API key (optional, only needed for delete support) |
| `CLOUDINARY_API_SECRET` | Your Cloudinary API secret (optional, only needed for delete support) |
| `RESEND_API_KEY` | Your Resend API key (optional, for emails) |
| `EMAIL_FROM` | `Obelytics <noreply@yourdomain.com>` |

> **Important**: `ALLOWED_ORIGINS` should be a comma-separated list with no trailing slash. JSON array strings are tolerated by the backend, but comma-separated values are the preferred format.

### 4c. Deploy

Click **Deploy**. The Dockerfile will:
1. Install Python dependencies + WeasyPrint system libraries (for PDF generation)
2. Run `alembic upgrade head` (database migrations)
3. Start Gunicorn with 2 Uvicorn workers

### 4d. Verify

Once deployed, visit:
- `https://YOUR-BACKEND.up.railway.app/health/live` → should return `{"status": "ok"}`
- `https://YOUR-BACKEND.up.railway.app/health/ready` → should return `{"status": "ok", "db": "ok", "redis": "ok"}`

---

## Step 5: Deploy the Frontend

### 5a. Create the frontend service

1. Click **"+ New"** → **"GitHub Repo"** → select the same repo again
2. Go to **Settings**:
   - **Root Directory**: `frontend`
   - **Builder**: Nixpacks (auto-detected for Next.js)

### 5b. Set environment variables

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://YOUR-BACKEND.up.railway.app` (the backend URL from Step 4) |
| `NEXT_PUBLIC_APP_NAME` | `Obelytics` |

### 5c. Deploy

Click **Deploy**. Nixpacks will auto-detect Next.js, run `npm install` and `npm run build`, then `npm start`.

### 5d. Update backend CORS

After the frontend is live, go back to the **backend** service variables and update:

```
ALLOWED_ORIGINS=https://YOUR-FRONTEND.vercel.app
```

If you have a custom domain, include both:

```
ALLOWED_ORIGINS=https://YOUR-FRONTEND.vercel.app,https://yourdomain.com
```

---

## Step 6: Custom Domains (Optional)

1. In each service's **Settings** → **Networking** → **Custom Domain**
2. Add your domain (e.g., `api.yourdomain.com` for backend, `app.yourdomain.com` for frontend)
3. Add the CNAME record Railway provides to your DNS
4. Update `ALLOWED_ORIGINS` and `NEXT_PUBLIC_API_URL` to use the custom domains

---

## Step 7: Seed Initial Data

After the first deployment, you need to create the initial admin user and seed reference data.

### Option A: Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and link
railway login
railway link

# Open a shell in the backend service
railway run --service backend -- python -c "
from app.core.seed import seed_all
import asyncio
asyncio.run(seed_all())
"
```

### Option B: Use the API directly

```bash
BACKEND=https://YOUR-BACKEND.up.railway.app

# The first POST to /auth/register creates the super admin
curl -X POST $BACKEND/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourdomain.com",
    "password": "YourSecurePassword123",
    "full_name": "Super Admin",
    "org_name": "Your University",
    "org_short_name": "YU"
  }'
```

Then log in at the frontend and configure the system through the UI.

---

## Cloudinary Storage Setup

The backend uses [Cloudinary](https://cloudinary.com) for logo and report storage, via an unsigned upload preset (no API key/secret required for uploads):

1. Create a Cloudinary account and note your **Cloud name**.
2. Create an **unsigned upload preset** (Settings → Upload → Upload presets → Add upload preset, set "Signing Mode" to "Unsigned").
3. Set the env vars:
```
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_UPLOAD_PRESET=your_upload_preset
```
4. Optionally set `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` if you need `delete_object` support (deletion requires a signed request).

---

## Environment Variable Reference

### Backend (all variables)

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL_OVERRIDE` | Yes | — | Railway PostgreSQL connection string |
| `REDIS_URL_OVERRIDE` | Yes | — | Railway Redis connection string |
| `SECRET_KEY` | Yes | — | JWT signing key (`openssl rand -hex 32`) |
| `ENV` | Yes | `development` | Set to `production` |
| `DEBUG` | Yes | `true` | Set to `false` in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token lifetime |
| `ALLOWED_ORIGINS` | Yes | — | Comma-separated allowed CORS origins |
| `CLOUDINARY_CLOUD_NAME` | Yes | — | Cloudinary cloud name |
| `CLOUDINARY_UPLOAD_PRESET` | Yes | — | Cloudinary unsigned upload preset |
| `CLOUDINARY_API_KEY` | No | — | Cloudinary API key (only needed for delete support) |
| `CLOUDINARY_API_SECRET` | No | — | Cloudinary API secret (only needed for delete support) |
| `CLOUDINARY_FOLDER_REPORTS` | No | `reports` | Folder for PDF reports |
| `CLOUDINARY_FOLDER_LOGOS` | No | `logos` | Folder for org logos |
| `CLOUDINARY_FOLDER_ACCREDITATION` | No | `accreditation` | Folder for accreditation docs |
| `RESEND_API_KEY` | No | — | Email provider API key |
| `EMAIL_FROM` | No | — | Email sender address |
| `DB_POOL_SIZE` | No | `20` | Database connection pool size |
| `DB_MAX_OVERFLOW` | No | `10` | Max overflow connections |

### Frontend

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | — | Backend URL (e.g., `https://api.yourdomain.com`) |
| `NEXT_PUBLIC_APP_NAME` | No | `Obelytics` | App name shown in UI |

---

## Troubleshooting

### Backend fails to start
- Check **Deploy Logs** in Railway for error details
- Common: missing env vars, database not ready yet
- The health check at `/health/ready` reports which services are down

### Database migrations fail
- Check if PostgreSQL is fully provisioned (can take 30s on first deploy)
- Railway CLI: `railway run --service backend -- python -m alembic upgrade head`

### PDF generation fails
- WeasyPrint needs system libraries (Cairo, Pango, GDK-Pixbuf) — these are installed in the Dockerfile
- If using Nixpacks instead of Dockerfile, add a `nixpacks.toml` with these packages

### CORS errors
- Verify `ALLOWED_ORIGINS` includes the exact frontend URL (with `https://`, no trailing slash)
- Redeploy backend after changing CORS origins

### Frontend can't reach backend
- Verify `NEXT_PUBLIC_API_URL` is the backend's public URL
- The frontend's BFF routes (`/api/auth/*`) proxy to the backend — both must be publicly accessible
