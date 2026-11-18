#!/usr/bin/env bash
set -euo pipefail

docker compose run --rm api python scripts/migrate.py
