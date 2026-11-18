"""Rootless worker entry point for production container execution.

The API may invoke this module in a separate service. The worker reads one
JSON request from stdin and writes one JSON response to stdout. The container
definition disables networking and runs as a non-root user.
"""

from __future__ import annotations

import json
import os
import sys

from fastapi import FastAPI
from pydantic import BaseModel, Field

from api.services.sandbox import run_sandboxed


worker_app = FastAPI(title="AI Learning Lab sandbox worker", version="0.1.0")


class RunRequest(BaseModel):
    code: str = Field(min_length=1, max_length=8_000)
    timeout_seconds: int = Field(default=3, ge=1, le=10)


@worker_app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sandbox-worker"}


@worker_app.post("/run")
def run(request: RunRequest) -> dict[str, object]:
    return run_sandboxed(request.code, request.timeout_seconds).__dict__


def main() -> int:
    request = json.loads(sys.stdin.readline() or "{}")
    result = run_sandboxed(request.get("code", ""), request.get("timeout_seconds", 3))
    print(json.dumps(result.__dict__, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if os.getenv("WORKER_HTTP", "0") == "1":
        import uvicorn

        uvicorn.run(worker_app, host="0.0.0.0", port=int(os.getenv("WORKER_PORT", "8010")))
    else:
        raise SystemExit(main())
