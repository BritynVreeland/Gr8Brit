"""`bbos` command line. Every pipeline stage is runnable by hand, by Claude Code, or by CI."""

import sys
from pathlib import Path

import typer

from bbos import db
from bbos.settings import get_settings

app = typer.Typer(help="Brit & Berat Content Intelligence OS", no_args_is_help=True)
db_app = typer.Typer(help="Database commands", no_args_is_help=True)
inbox_app = typer.Typer(help="Evidence Inbox", no_args_is_help=True)
ig_app = typer.Typer(help="Instagram (our accounts)", no_args_is_help=True)
app.add_typer(db_app, name="db")
app.add_typer(inbox_app, name="inbox")
app.add_typer(ig_app, name="ig")


@db_app.command("migrate")
def db_migrate() -> None:
    """Apply pending SQL migrations."""
    with db.connect() as conn:
        applied = db.migrate(conn)
    typer.echo(f"Applied: {', '.join(applied) or 'nothing (up to date)'}")


@app.command()
def seed() -> None:
    """Load config/*.yaml into reference tables (accounts, offers, taxonomy, banned phrases, sources)."""
    from bbos.seed import seed as run_seed

    with db.connect() as conn:
        counts = run_seed(conn)
    typer.echo(", ".join(f"{k}={v}" for k, v in counts.items()))


@app.command()
def doctor() -> None:
    """Check configuration, credentials, and connectivity."""
    s = get_settings()
    ok = True

    def check(label: str, passed: bool, hint: str = "") -> None:
        nonlocal ok
        ok &= passed
        typer.echo(f"[{'ok' if passed else '!!'}] {label}" + ("" if passed or not hint else f" — {hint}"))

    for var in (
        "database_url",
        "anthropic_api_key",
        "voyage_api_key",
        "meta_access_token",
        "youtube_api_key",
        "author_hash_salt",
    ):
        check(f"{var.upper()} set", bool(getattr(s, var)), "see docs/SETUP.md")
    if s.database_url:
        try:
            with db.connect() as conn:
                n = conn.execute("select count(*) as n from schema_migrations").fetchone()["n"]
                accts = conn.execute("select key, handle, ig_user_id from accounts order by key").fetchall()
            check(f"database reachable ({n} migrations applied)", True)
            for a in accts:
                check(
                    f"account {a['key']} handle={a['handle']} ig_user_id={a['ig_user_id']}",
                    bool(a["handle"] and a["ig_user_id"]),
                    "set handle in config/accounts.yaml, then `bbos ig discover`",
                )
        except Exception as e:  # noqa: BLE001 — doctor reports, never crashes
            check("database reachable", False, str(e).splitlines()[0])
    sys.exit(0 if ok else 1)


@inbox_app.command("add")
def inbox_add(
    captured_by: str = typer.Option(..., help="brit / berat / guide / claude-assisted"),
    text: str | None = typer.Option(None, help="Pasted text (or use --file)"),
    file: Path | None = typer.Option(None, exists=True, readable=True, help="Text file to store"),
    url: str | None = typer.Option(None, help="Where it came from"),
    title: str | None = typer.Option(None),
    source: str = typer.Option("manual_inbox", help="manual_inbox | customer_messages | field_notes | swipe_file"),
    note: str | None = typer.Option(None, help="Why this matters (one line)"),
) -> None:
    """Store a captured thread, message, field note, or swipe-file entry as evidence."""
    from bbos.evidence.inbox import add_to_inbox

    body = file.read_text() if file else text
    if not body:
        raise typer.BadParameter("Provide --text or --file")
    with db.connect() as conn:
        doc_id, created = add_to_inbox(
            conn, text=body, source_key=source, url=url, title=title, captured_by=captured_by, note=note
        )
    typer.echo(f"{'Stored' if created else 'Already stored'}: {doc_id}")


@ig_app.command("discover")
def ig_discover() -> None:
    """Find our Instagram accounts via the token and record their IG user IDs."""
    from bbos.collectors.instagram import client_from_settings, discover_accounts

    with db.connect() as conn:
        found = discover_accounts(conn, client_from_settings())
    for f in found:
        typer.echo(f"{f['username']} ({f['ig_user_id']}) via Page '{f['page']}'")


@ig_app.command("sync")
def ig_sync(
    account: str = typer.Option("all", help="Account key, or 'all'"),
    max_media: int | None = typer.Option(None, help="Limit media per account (backfills are rate-limited)"),
    no_comments: bool = typer.Option(False, help="Skip comment collection"),
) -> None:
    """Pull media, insights, stories, and comments for our accounts."""
    from bbos.collectors.instagram import client_from_settings, sync_account

    client = client_from_settings()
    with db.connect() as conn:
        keys = (
            [account]
            if account != "all"
            else [r["key"] for r in conn.execute("select key from accounts where active and ig_user_id is not null")]
        )
        for key in keys:
            stats = sync_account(conn, client, key, max_media=max_media, with_comments=not no_comments)
            typer.echo(f"{key}: {stats}")


if __name__ == "__main__":
    app()
