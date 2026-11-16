"""Database connections and migrations."""

from __future__ import annotations

from pathlib import Path

import psycopg

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


def connect(url: str) -> psycopg.Connection[tuple[object, ...]]:
    return psycopg.connect(url, autocommit=False)


def migrate(conn: psycopg.Connection[tuple[object, ...]], directory: Path = MIGRATIONS) -> list[str]:
    """Apply each .sql file in name order once. Returns the names applied now."""
    with conn.transaction():
        conn.execute(
            "CREATE TABLE IF NOT EXISTS public.hishob_migrations "
            "(name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
    applied: list[str] = []
    for path in sorted(directory.glob("*.sql")):
        with conn.transaction():
            done = conn.execute("SELECT 1 FROM public.hishob_migrations WHERE name = %s", (path.name,)).fetchone()
            if done:
                continue
            conn.execute(path.read_text(encoding="utf-8").encode())
            conn.execute("INSERT INTO public.hishob_migrations (name) VALUES (%s)", (path.name,))
            applied.append(path.name)
    return applied
