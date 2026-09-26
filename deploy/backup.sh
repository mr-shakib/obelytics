#!/usr/bin/env sh
# Dump the production database to ./backups (keeps the 14 most recent).
# Cron example (daily 03:00):  0 3 * * * cd ~/obelytics && ./deploy/backup.sh
set -eu
cd "$(dirname "$0")/.."
set -a; . ./.env.production; set +a
mkdir -p backups
file="backups/obelytics_$(date +%Y%m%d_%H%M%S).sql.gz"
docker compose -f docker-compose.prod.yml --env-file .env.production exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$file"
ls -1t backups/*.sql.gz | tail -n +15 | xargs -r rm --
echo "Backup written to $file"
