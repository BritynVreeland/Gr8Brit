"""Evidence Inbox: human-captured evidence (threads, forum posts, DMs, inquiries, field notes, swipe file)."""

import hashlib
import uuid
from datetime import datetime

import psycopg

from bbos.evidence.store import insert_raw_document

INBOX_SOURCES = {"manual_inbox", "customer_messages", "field_notes", "swipe_file"}


def add_to_inbox(
    conn: psycopg.Connection,
    *,
    text: str,
    source_key: str = "manual_inbox",
    url: str | None = None,
    title: str | None = None,
    published_at: datetime | None = None,
    captured_by: str,
    note: str | None = None,
) -> tuple[uuid.UUID, bool]:
    """Store one captured item. Identity is the URL when given, otherwise the text itself,
    so pasting the same thing twice doesn't create duplicates."""
    if source_key not in INBOX_SOURCES:
        raise ValueError(f"source_key must be one of {sorted(INBOX_SOURCES)}")
    identity = url or text.strip()
    external_id = "inbox:" + hashlib.sha256(identity.encode()).hexdigest()[:32]
    return insert_raw_document(
        conn,
        source_key=source_key,
        external_id=external_id,
        body_text=text,
        capture_method="manual_url" if url else "manual_paste",
        url=url,
        title=title,
        published_at=published_at,
        captured_by=captured_by,
        capture_note=note,
    )
