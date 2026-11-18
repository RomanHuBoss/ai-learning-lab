"""Restricted local code runner used by the demo API.

The production deployment should point the API at the rootless worker service
defined in ``workers/runner.py``. The local mode still isolates every run in a
temporary directory, clears the environment, rejects network/process escapes,
and enforces a hard timeout.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


MAX_CODE_LENGTH = 8_000
MAX_OUTPUT_LENGTH = 12_000
DEFAULT_TIMEOUT_SECONDS = 3

# This is intentionally conservative. It protects the local demo worker from
# the common escape paths. Container isolation remains the production boundary.
FORBIDDEN_PATTERNS = [
    r"\bimport\s+(socket|subprocess|multiprocessing|ctypes|os|pathlib|shutil)\b",
    r"\bfrom\s+(socket|subprocess|multiprocessing|ctypes|os|pathlib|shutil)\b",
    r"\b(open|eval|exec|compile|__import__)\s*\(",
    r"\b(input|help|breakpoint)\s*\(",
    r"__\w+__",
]


@dataclass(frozen=True)
class SandboxResult:
    status: str
    stdout: str
    stderr: str
    duration_ms: int
    blocked_reason: str | None = None


def validate_code(code: str) -> str | None:
    if not isinstance(code, str) or not code.strip():
        return "Код не должен быть пустым."
    if len(code) > MAX_CODE_LENGTH:
        return f"Код превышает лимит {MAX_CODE_LENGTH} символов."
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            return "Команда заблокирована политикой безопасного запуска."
    return None


def _preexec_limits() -> None:
    """Apply Unix resource limits when the worker runs on Unix."""
    if os.name == "nt":
        return
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024 * 1024, 2 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))


def run_sandboxed(code: str, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> SandboxResult:
    blocked_reason = validate_code(code)
    if blocked_reason:
        return SandboxResult("blocked", "", blocked_reason, 0, blocked_reason)

    timeout_seconds = max(1, min(int(timeout_seconds), 10))
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="ailab-run-") as temp_dir:
        script = Path(temp_dir) / "main.py"
        script.write_text(code, encoding="utf-8")
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONNOUSERSITE": "1",
        }
        command = [sys.executable, "-I", script.name]
        try:
            completed = subprocess.run(
                command,
                cwd=temp_dir,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
                preexec_fn=_preexec_limits if os.name != "nt" else None,
            )
        except subprocess.TimeoutExpired as exc:
            duration = int((time.perf_counter() - started) * 1000)
            stdout = (exc.stdout or "")[:MAX_OUTPUT_LENGTH]
            stderr = (exc.stderr or "")[:MAX_OUTPUT_LENGTH]
            return SandboxResult("timeout", stdout, stderr, duration, "Превышен лимит времени.")

    duration = int((time.perf_counter() - started) * 1000)
    stdout = completed.stdout[:MAX_OUTPUT_LENGTH]
    stderr = completed.stderr[:MAX_OUTPUT_LENGTH]
    status = "ok" if completed.returncode == 0 else "error"
    return SandboxResult(status, stdout, stderr, duration)
