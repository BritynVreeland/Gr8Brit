"""Database access: connections and the SQL migration runner."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from bbos.settings import get_settings


def _require_url(url: str | None) -> str:
    url = url or get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not set (see docs/SETUP.md)")
    return url


@contextmanager
def connect(url: str | None = None) -> Iterator[psycopg.Connection]:
    """Yield a connection that commits on success and rolls back on error."""
    with psycopg.connect(_require_url(url), row_factory=dict_row) as conn:
        yield conn


def migrate(conn: psycopg.Connection, migrations_dir: Path | None = None) -> list[str]:
    """Apply any not-yet-applied `NNN_name.sql` files in order. Returns names applied."""
    migrations_dir = migrations_dir or get_settings().migrations_dir
    conn.execute(
        "create table if not exists schema_migrations ("
        " name text primary key, applied_at timestamptz not null default now())"
    )
    applied = {r["name"] for r in conn.execute("select name from schema_migrations")}
    newly_applied = []
    for path in sorted(migrations_dir.glob("*.sql")):
        if path.name in applied:
            continue
        with conn.transaction():
            conn.execute(path.read_text())
            conn.execute("insert into schema_migrations (name) values (%s)", (path.name,))
        newly_applied.append(path.name)
    return newly_applied
