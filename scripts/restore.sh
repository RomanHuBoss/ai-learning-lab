#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! -f "$1" ]]; then
  echo "Usage: $0 backups/ailab-YYYYMMDDTHHMMSSZ.sql.gz" >&2
  exit 2
fi

echo "Restoring $1 into ${POSTGRES_DB:-ailab}"
gzip -dc "$1" | docker compose exec -T db psql \
  --username "${POSTGRES_USER:-ailab}" \
  --dbname "${POSTGRES_DB:-ailab}"
echo "Restore completed"
