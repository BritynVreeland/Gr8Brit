"""Writing to the immutable raw layer (sources, collection runs, raw documents)."""

import hashlib
import hmac
import uuid
from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from bbos.evidence.quotes import normalize_body
from bbos.settings import get_settings


def content_hash(body_text: str) -> str:
    return hashlib.sha256(body_text.encode("utf-8")).hexdigest()


def hash_author(username: str | None, salt: str | None = None) -> str | None:
    """Salted, keyed hash of a public username: lets us count independent authors without storing identities."""
    if not username:
        return None
    salt = salt or get_settings().author_hash_salt
    if not salt:
        raise RuntimeError("AUTHOR_HASH_SALT must be set before storing author hashes")
    return hmac.new(salt.encode(), username.strip().lower().encode(), hashlib.sha256).hexdigest()


def source_id(conn: psycopg.Connection, key: str) -> uuid.UUID:
    row = conn.execute("select id from sources where key = %s", (key,)).fetchone()
    if not row:
        raise KeyError(f"Unknown source {key!r}; run `bbos seed` first")
    return row["id"]


def start_collection_run(conn: psycopg.Connection, source_key: str, params: dict[str, Any]) -> uuid.UUID:
    row = conn.execute(
        "insert into collection_runs (source_id, params) values (%s, %s) returning id",
        (source_id(conn, source_key), Jsonb(params)),
    ).fetchone()
    return row["id"]


def finish_collection_run(
    conn: psycopg.Connection, run_id: uuid.UUID, items: int, status: str = "succeeded", error: str | None = None
) -> None:
    conn.execute(
        "update collection_runs set status=%s, items_fetched=%s, error=%s, finished_at=now() where id=%s",
        (status, items, error, run_id),
    )


def insert_raw_document(
    conn: psycopg.Connection,
    *,
    source_key: str,
    external_id: str,
    body_text: str,
    capture_method: str,
    collection_run_id: uuid.UUID | None = None,
    parent_external_id: str | None = None,
    url: str | None = None,
    author_hash: str | None = None,
    author_meta: dict | None = None,
    published_at: datetime | None = None,
    title: str | None = None,
    raw_payload: dict | None = None,
    engagement: dict | None = None,
    language: str | None = None,
    captured_by: str | None = None,
    capture_note: str | None = None,
) -> tuple[uuid.UUID, bool]:
    """Insert a raw document once. Returns (id, created). Re-collecting the same item is a no-op,
    except engagement which is refreshed (it's a fetch-time observation, not content)."""
    body = normalize_body(body_text)
    if not body:
        raise ValueError("raw document body is empty")
    row = conn.execute(
        """
        insert into raw_documents (source_id, collection_run_id, external_id, parent_external_id, url,
          author_hash, author_meta, published_at, title, body_text, raw_payload, content_hash,
          engagement, language, capture_method, captured_by, capture_note)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        on conflict (source_id, external_id) do update set engagement = excluded.engagement
        returning id, (xmax = 0) as created
        """,
        (
            source_id(conn, source_key),
            collection_run_id,
            external_id,
            parent_external_id,
            url,
            author_hash,
            Jsonb(author_meta or {}),
            published_at,
            title,
            body,
            Jsonb(raw_payload) if raw_payload is not None else None,
            content_hash(body),
            Jsonb(engagement or {}),
            language,
            capture_method,
            captured_by,
            capture_note,
        ),
    ).fetchone()
    return row["id"], row["created"]
