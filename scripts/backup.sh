#!/usr/bin/env bash
set -euo pipefail

mkdir -p backups
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
file="backups/ailab-${stamp}.sql.gz"

docker compose exec -T db pg_dump \
  --username "${POSTGRES_USER:-ailab}" \
  --dbname "${POSTGRES_DB:-ailab}" \
  --no-owner --no-privileges | gzip > "${file}"

echo "Backup written to ${file}"
