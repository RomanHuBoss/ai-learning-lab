#!/usr/bin/env bash
set -euo pipefail

curl --fail --silent --show-error http://127.0.0.1:8000/health/live >/dev/null
curl --fail --silent --show-error http://127.0.0.1:8000/health/ready >/dev/null
echo "AI Learning Lab is ready"
