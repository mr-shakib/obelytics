# Obelytics — VPS Deployment

Production runs at **https://obelytics.bitstreamhq.com** on the shared VPS
(`shakib@187.53.136.115`, Ubuntu, Docker). The app lives in `~/obelytics` on the server.

```
Browser ─443─► host nginx (TLS, certbot) ─┬─ /api/v1/*, /health/* ─► 127.0.0.1:8320 backend
                                          └─ everything else ──────► 127.0.0.1:3320 frontend
docker compose (project "obelytics"):
  backend (gunicorn) · worker (arq) · frontend (Next.js standalone)
  postgres · redis (internal network only) · migrate (one-shot alembic upgrade head)
```

The host nginx also serves other sites, so the stack never binds 80/443 itself.
`/api/auth/*` is intentionally routed to Next.js — those are the BFF auth routes.

Files: `docker-compose.prod.yml`, `.env.production.example`, `deploy/nginx/obelytics.conf`,
`deploy/install-nginx.sh`, `deploy/backup.sh`, `frontend/Dockerfile`, `backend/Dockerfile`.

> Tip: on the server, `alias dc='docker compose -f docker-compose.prod.yml --env-file .env.production'`.
> The commands below use `dc` and run from `~/obelytics`.

## Updating (routine deploy)

```bash
ssh shakib@187.53.136.115
cd ~/obelytics && git pull
dc up -d --build          # rebuilds, runs migrations, restarts changed services
docker image prune -f
curl -s https://obelytics.bitstreamhq.com/health/ready
```

`NEXT_PUBLIC_*` values are compiled into the frontend, so changing `DOMAIN` or
`NEXT_PUBLIC_APP_NAME` needs `--build`.

## First-time setup (already done — for rebuilding the server)

1. DNS: `A obelytics.bitstreamhq.com → 187.53.136.115`.
2. Code and secrets:
   ```bash
   git clone https://github.com/mr-shakib/obelytics.git ~/obelytics && cd ~/obelytics
   cp .env.production.example .env.production
   # fill SECRET_KEY, POSTGRES_PASSWORD, REDIS_PASSWORD with `openssl rand -hex 32`
   chmod 600 .env.production
   ```
3. Start the stack: `dc up -d --build`.
4. TLS and nginx site (needs sudo, one time): `sudo ./deploy/install-nginx.sh`.
   Certbot's systemd timer renews the certificate automatically.
5. Seed:
   ```bash
   dc exec backend python -m scripts.seed_superadmin \
     --email admin@obelytics.com --password '<strong password>' \
     --org-name 'Daffodil International University' --org-short-name DIU
   dc exec backend python -m scripts.seed_reference_data
   ```
6. Backups: `crontab -e` →
   `0 3 * * * cd $HOME/obelytics && ./deploy/backup.sh >> $HOME/obelytics/backups/backup.log 2>&1`

## Backups and restore

`./deploy/backup.sh` writes `backups/obelytics_<timestamp>.sql.gz` and keeps the newest 14.
Copy them off the server regularly. Restore into the running database:

```bash
gunzip -c backups/obelytics_XXXX.sql.gz | dc exec -T postgres psql -U obelytics -d obelytics
```

## Operations

| Task | Command |
|---|---|
| Status | `dc ps` |
| Logs | `dc logs -f backend` (or `worker`, `frontend`, `migrate`) |
| Restart a service | `dc restart backend` |
| Re-run migrations | `dc run --rm migrate` |
| Postgres shell | `dc exec postgres psql -U obelytics -d obelytics` |
| Stop | `dc down` (keeps data; `down -v` **deletes** the database) |

## Troubleshooting

- **502 from nginx** — a container is down or starting: `dc ps`, `dc logs backend`.
- **backend/worker not starting** — `migrate` failed: `dc logs migrate`.
- **Logged out immediately / login loop** — auth cookies are `Secure`; use the https URL.
- **CORS errors** — `DOMAIN` in `.env.production` must match the browser URL exactly.
- **Reports stuck pending** — `dc logs worker`.
- **nginx changes** — edit `deploy/nginx/obelytics.conf`, then `sudo ./deploy/install-nginx.sh`.
