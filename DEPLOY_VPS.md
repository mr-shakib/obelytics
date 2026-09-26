# Obelytics — VPS Deployment Guide

Runs the whole stack on one Linux VPS with Docker Compose. Caddy terminates HTTPS
(automatic Let's Encrypt certificates) and serves frontend and backend on **one domain**:

```
                 ┌──────────────── VPS (docker compose) ────────────────┐
 Browser ─443──► │ caddy ─┬─ /api/v1/*, /health/* ──► backend (gunicorn) │
                 │        └─ everything else ───────► frontend (Next.js)│
                 │ backend, worker (arq) ──► postgres, redis (internal) │
                 │ migrate (one-shot: alembic upgrade head)             │
                 └──────────────────────────────────────────────────────┘
```

Files: `docker-compose.prod.yml`, `deploy/Caddyfile`, `.env.production.example`,
`frontend/Dockerfile`, `backend/Dockerfile`, `deploy/backup.sh`.

## 1. Requirements

- Ubuntu 22.04/24.04 (or any Linux with Docker), **2 vCPU / 4 GB RAM** recommended
  (the frontend build needs ~2 GB; add swap on smaller machines)
- A domain with an **A record** pointing at the VPS IP (e.g. `obelytics.example.com`)
- Ports **80** and **443** open

## 2. Prepare the server

```bash
# Docker Engine + compose plugin
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker

# Firewall
sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443/tcp && sudo ufw allow 443/udp
sudo ufw enable

# Optional: 2 GB swap for small VPSes
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile \
  && sudo swapon /swapfile && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 3. Get the code and configure

```bash
sudo mkdir -p /opt/obelytics && sudo chown $USER /opt/obelytics
git clone https://github.com/mr-shakib/obelytics.git /opt/obelytics
cd /opt/obelytics
cp .env.production.example .env.production
nano .env.production
```

Fill in at least `DOMAIN`, `SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`
(generate each with `openssl rand -hex 32`). `ALLOWED_ORIGINS`, DB/Redis hosts and the
frontend API URL are derived from `DOMAIN` automatically.

## 4. Launch

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Startup order: postgres/redis → `migrate` runs migrations and exits → backend + worker →
frontend → caddy. The first start takes a few minutes (image builds + certificate).

Check it:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
curl https://$DOMAIN/health/ready     # {"status":"ok","db":"ok","redis":"ok"}
```

> Tip: `alias dc='docker compose -f docker-compose.prod.yml --env-file .env.production'`
> — the rest of this guide uses `dc`.

## 5. Seed initial data (first deploy only)

```bash
dc exec backend python -m scripts.seed_superadmin \
  --email admin@yourdomain.com --password 'ChangeMe!123' \
  --org-name 'Daffodil International University' --org-short-name DIU
dc exec backend python -m scripts.seed_reference_data
```

Both are safe to re-run. Log in at `https://$DOMAIN/login` and change the password.

To keep the same organization ID as an existing deployment, add `--org-id <uuid>`.

## 6. Updating

```bash
cd /opt/obelytics
git pull
dc up -d --build        # rebuilds images, re-runs migrations, restarts changed services
docker image prune -f
```

`NEXT_PUBLIC_*` values are compiled into the frontend, so changing `DOMAIN` or
`NEXT_PUBLIC_APP_NAME` requires `--build`.

## 7. Backups

```bash
./deploy/backup.sh                      # writes backups/obelytics_<timestamp>.sql.gz
crontab -e                              # daily at 03:00:
# 0 3 * * * cd /opt/obelytics && ./deploy/backup.sh >> backups/backup.log 2>&1
```

Copy `backups/` off the server regularly. Restore:

```bash
gunzip -c backups/obelytics_XXXX.sql.gz | dc exec -T postgres psql -U obelytics -d obelytics
```

## 8. Operations

| Task | Command |
|---|---|
| Logs (all / one service) | `dc logs -f` / `dc logs -f backend` |
| Restart a service | `dc restart backend` |
| Run migrations manually | `dc run --rm migrate` |
| Postgres shell | `dc exec postgres psql -U obelytics -d obelytics` |
| Stop everything | `dc down` (data volumes are kept; `down -v` **deletes** them) |

## Troubleshooting

- **No HTTPS certificate** — DNS must resolve to the VPS and ports 80/443 must be open
  before Caddy starts. Check `dc logs caddy`.
- **Login loops / logged out immediately** — auth cookies are `Secure`; the site must be
  served over HTTPS (Caddy does this). Don't access the app by raw IP.
- **CORS errors** — `DOMAIN` in `.env.production` must match the URL in the browser exactly.
- **`migrate` failed** — `dc logs migrate`; backend and worker won't start until it succeeds.
- **Reports stuck in "pending"** — check `dc logs worker`.
- **Frontend build killed (exit 137)** — out of memory; add swap (step 2).
