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
                    │   S3/MinIO      │ (external or Railway volume)
                    └─────────────────┘
```

---

## Prerequisites

- A [Railway](https://railway.com) account (Hobby plan or above for production)
- The GitHub repo pushed to GitHub (Railway deploys from Git)
- An S3-compatible storage provider (AWS S3, Cloudflare R2, or self-hosted MinIO). Railway does not provide managed object storage

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
| `ALLOWED_ORIGINS` | `["https://YOUR-FRONTEND-DOMAIN.up.railway.app"]` |
| `MINIO_ENDPOINT` | Your S3-compatible endpoint (e.g., `s3.amazonaws.com` or R2 endpoint) |
| `MINIO_ACCESS_KEY` | Your S3 access key |
| `MINIO_SECRET_KEY` | Your S3 secret key |
| `MINIO_SECURE` | `true` |
| `RESEND_API_KEY` | Your Resend API key (optional, for emails) |
| `EMAIL_FROM` | `Obelytics <noreply@yourdomain.com>` |

> **Important**: The `ALLOWED_ORIGINS` must be a JSON array string. Update it with the actual frontend URL after deploying the frontend.

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
ALLOWED_ORIGINS=["https://YOUR-FRONTEND.up.railway.app"]
```

If you have a custom domain, include both:

```
ALLOWED_ORIGINS=["https://YOUR-FRONTEND.up.railway.app","https://yourdomain.com"]
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

## S3-Compatible Storage Options

The backend uses S3-compatible storage for logos and reports. Options:

### Cloudflare R2 (recommended — free tier generous)
```
MINIO_ENDPOINT=YOUR_ACCOUNT_ID.r2.cloudflarestorage.com
MINIO_ACCESS_KEY=your_r2_access_key
MINIO_SECRET_KEY=your_r2_secret_key
MINIO_SECURE=true
```

### AWS S3
```
MINIO_ENDPOINT=s3.amazonaws.com
MINIO_ACCESS_KEY=your_aws_access_key
MINIO_SECRET_KEY=your_aws_secret_key
MINIO_SECURE=true
```

### Self-hosted MinIO on Railway
1. Add a new service from Docker image: `minio/minio`
2. Set command: `server /data --console-address :9001`
3. Add a volume mounted at `/data`
4. Set `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` env vars
5. Use the internal Railway URL as `MINIO_ENDPOINT`

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
| `ALLOWED_ORIGINS` | Yes | — | JSON array of allowed CORS origins |
| `MINIO_ENDPOINT` | Yes | — | S3-compatible endpoint |
| `MINIO_ACCESS_KEY` | Yes | — | S3 access key |
| `MINIO_SECRET_KEY` | Yes | — | S3 secret key |
| `MINIO_SECURE` | No | `false` | Use HTTPS for S3 |
| `MINIO_BUCKET_REPORTS` | No | `reports` | Bucket for PDF reports |
| `MINIO_BUCKET_LOGOS` | No | `logos` | Bucket for org logos |
| `MINIO_BUCKET_ACCREDITATION` | No | `accreditation` | Bucket for accreditation docs |
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
