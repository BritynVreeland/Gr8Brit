"""Load versioned config (config/*.yaml) into reference tables. Idempotent."""

from pathlib import Path

import psycopg
import yaml

from bbos.settings import get_settings

# Data sources we use, with the terms basis that permits each (docs/INTEGRATIONS.md).
SOURCES = [
    {
        "key": "ig_own",
        "name": "Our Instagram accounts (media, insights, comments)",
        "access_method": "official_api",
        "terms_basis": "Meta Platform Terms; own Professional accounts",
        "retention_days": None,
        "is_first_party": True,
    },
    {
        "key": "ig_market",
        "name": "Instagram category content (Hashtag Search, Business Discovery)",
        "access_method": "official_api",
        "terms_basis": "Meta Platform Terms; official public-content endpoints",
        "retention_days": 730,
        "is_first_party": False,
    },
    {
        "key": "youtube",
        "name": "YouTube videos and comments",
        "access_method": "official_api",
        "terms_basis": "YouTube API Services Terms",
        "retention_days": 730,
        "is_first_party": False,
    },
    {
        "key": "manual_inbox",
        "name": "Evidence Inbox (human-captured threads, forums, notes)",
        "access_method": "manual_capture",
        "terms_basis": "Human capture for internal research",
        "retention_days": 730,
        "is_first_party": False,
    },
    {
        "key": "customer_messages",
        "name": "Our DMs, emails, WhatsApp inquiries (anonymized)",
        "access_method": "manual_capture",
        "terms_basis": "Own customer communications; PII stripped",
        "retention_days": 730,
        "is_first_party": True,
    },
    {
        "key": "field_notes",
        "name": "Tour field notes from Brit, Berat and guides",
        "access_method": "manual_capture",
        "terms_basis": "Own observations",
        "retention_days": None,
        "is_first_party": True,
    },
    {
        "key": "swipe_file",
        "name": "Swipe file of standout category posts",
        "access_method": "manual_capture",
        "terms_basis": "Links curated by Brit; metadata via official APIs",
        "retention_days": 730,
        "is_first_party": False,
    },
]


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def seed(conn: psycopg.Connection, config_dir: Path | None = None) -> dict[str, int]:
    config_dir = config_dir or get_settings().config_dir
    counts: dict[str, int] = {}

    for s in SOURCES:
        conn.execute(
            """insert into sources (key, name, access_method, terms_basis, retention_days, is_first_party)
               values (%(key)s, %(name)s, %(access_method)s, %(terms_basis)s, %(retention_days)s, %(is_first_party)s)
               on conflict (key) do update set name=excluded.name, access_method=excluded.access_method,
                 terms_basis=excluded.terms_basis, retention_days=excluded.retention_days,
                 is_first_party=excluded.is_first_party""",
            s,
        )
    counts["sources"] = len(SOURCES)

    accounts = _load(config_dir / "accounts.yaml")["accounts"]
    for a in accounts:
        conn.execute(
            """insert into accounts (key, name, handle, role, primary_objectives, weekly_feed_target,
                 weekly_feed_min, stories_per_week)
               values (%(key)s, %(name)s, %(handle)s, %(role)s, %(primary_objectives)s, %(weekly_feed_target)s,
                 %(weekly_feed_min)s, %(stories_per_week)s)
               on conflict (key) do update set name=excluded.name,
                 handle=coalesce(excluded.handle, accounts.handle), role=excluded.role,
                 primary_objectives=excluded.primary_objectives, weekly_feed_target=excluded.weekly_feed_target,
                 weekly_feed_min=excluded.weekly_feed_min, stories_per_week=excluded.stories_per_week""",
            a,
        )
    counts["accounts"] = len(accounts)

    offers = _load(config_dir / "offers.yaml")["offers"]
    for o in offers:
        conn.execute(
            """insert into offers (key, name, description, price_range, url)
               values (%s, %s, %s, %s, %s)
               on conflict (key) do update set name=excluded.name, description=excluded.description,
                 price_range=excluded.price_range, url=excluded.url""",
            (o["key"], o["name"], o.get("description"), o.get("price_range"), o.get("url")),
        )
    counts["offers"] = len(offers)

    nodes = _load(config_dir / "taxonomy.yaml")["nodes"]
    for n in nodes:
        parent = None
        if n.get("parent"):
            parent = conn.execute("select id from taxonomy_nodes where key=%s", (n["parent"],)).fetchone()["id"]
        conn.execute(
            """insert into taxonomy_nodes (key, parent_id, label, description) values (%s, %s, %s, %s)
               on conflict (key) do update set parent_id=excluded.parent_id, label=excluded.label,
                 description=excluded.description""",
            (n["key"], parent, n["label"], n.get("description")),
        )
    counts["taxonomy_nodes"] = len(nodes)

    banned = _load(config_dir / "banned_phrases.yaml")["banned"]
    for phrase in banned:
        conn.execute(
            "insert into brand_rules (rule_type, value) values ('banned_phrase', %s) on conflict do nothing",
            (phrase,),
        )
    counts["banned_phrases"] = len(banned)
    return counts
