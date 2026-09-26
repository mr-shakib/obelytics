#!/usr/bin/env sh
# Dump the production database to ./backups (keeps the 14 most recent).
# Cron example (daily 03:00):  0 3 * * * cd $HOME/obelytics && ./deploy/backup.sh
set -eu
cd "$(dirname "$0")/.."
# Not sourced: some values (e.g. EMAIL_FROM) aren't valid shell
env_get() { grep -E "^$1=" .env.production | tail -1 | cut -d= -f2-; }
POSTGRES_USER=$(env_get POSTGRES_USER)
POSTGRES_DB=$(env_get POSTGRES_DB)
mkdir -p backups
file="backups/obelytics_$(date +%Y%m%d_%H%M%S).sql.gz"
docker compose -f docker-compose.prod.yml --env-file .env.production exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$file"
ls -1t backups/*.sql.gz | tail -n +15 | xargs -r rm --
echo "Backup written to $file"
