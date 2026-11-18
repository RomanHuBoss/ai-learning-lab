"""Apply versioned SQL migrations with a durable migration ledger."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.database import engine, init_db  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"


def statements(sql: str) -> list[str]:
    clean = "\n".join(line for line in sql.splitlines() if not line.strip().startswith("--"))
    return [part.strip() for part in clean.split(";") if part.strip()]


def migrate_postgres() -> list[str]:
    applied: list[str] = []
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(120) PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
        existing = {row[0] for row in connection.execute(text("SELECT version FROM schema_migrations"))}
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name in existing:
                continue
            for statement in statements(path.read_text(encoding="utf-8")):
                connection.execute(text(statement))
            connection.execute(text("INSERT INTO schema_migrations(version) VALUES (:version)"), {"version": path.name})
            applied.append(path.name)
    return applied


def main() -> int:
    if engine.url.get_backend_name() == "postgresql":
        applied = migrate_postgres()
        print("Migrations applied:", ", ".join(applied) if applied else "none")
        return 0
    init_db()
    print("SQLite metadata schema ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
