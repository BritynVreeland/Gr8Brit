import psycopg
import pytest

from bbos import db
from bbos.evidence.inbox import add_to_inbox


def test_migrations_are_idempotent(conn):
    assert db.migrate(conn) == []


def test_seed_loads_accounts_offers_taxonomy(conn):
    keys = {r["key"] for r in conn.execute("select key from accounts")}
    assert keys == {"brit_in_istanbul", "brit_and_berat"}
    assert conn.execute("select count(*) n from offers").fetchone()["n"] == 6
    assert conn.execute("select count(*) n from taxonomy_nodes").fetchone()["n"] > 20


def test_inbox_dedupes_and_records_capture(conn):
    a, created_a = add_to_inbox(
        conn,
        text="Is Uber legal in Istanbul?",
        captured_by="brit",
        url="https://example.com/t/1",
        note="taxi confusion",
    )
    b, created_b = add_to_inbox(
        conn, text="Is Uber legal in Istanbul?", captured_by="brit", url="https://example.com/t/1"
    )
    assert a == b and created_a and not created_b
    row = conn.execute("select capture_method, captured_by, content_hash from raw_documents").fetchone()
    assert row["capture_method"] == "manual_url" and row["captured_by"] == "brit" and len(row["content_hash"]) == 64


def test_raw_documents_are_immutable(conn):
    doc_id, _ = add_to_inbox(conn, text="original words", captured_by="berat", source_key="field_notes")
    conn.commit()
    with pytest.raises(psycopg.errors.RaiseException):
        conn.execute("update raw_documents set body_text='edited' where id=%s", (doc_id,))
    conn.rollback()
    conn.execute("update raw_documents set deleted_at_source=true where id=%s", (doc_id,))  # bookkeeping is allowed


def test_inbox_rejects_unknown_source(conn):
    with pytest.raises(ValueError):
        add_to_inbox(conn, text="x", captured_by="brit", source_key="reddit")
