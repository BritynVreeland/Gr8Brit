"""Instagram collector for OUR accounts (Graph API, Facebook Login flavor).

Pulls media, per-media insights, comments, and live stories for each account in `accounts`, and writes:
- `assets` (one row per media; Collab posts stored once under the owning account)
- `asset_metric_snapshots` (time series; raw API payload kept in `metrics` so renames don't lose history)
- `raw_documents` + `asset_comments` (audience comments become evidence; our own replies don't)

Meta changes metric availability per media type and over time, so insights are requested as a set and,
if the set is rejected, metric-by-metric; unsupported metrics are remembered for the rest of the run.
"""

import json
import logging
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
import psycopg
from psycopg.types.json import Jsonb

from bbos.evidence.store import (
    finish_collection_run,
    hash_author,
    insert_raw_document,
    start_collection_run,
)
from bbos.settings import get_settings

log = logging.getLogger(__name__)

MEDIA_FIELDS = (
    "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count,thumbnail_url,media_url"
)
COMMENT_FIELDS = "id,text,timestamp,username,like_count,replies{id,text,timestamp,username,like_count}"

# Requested insight metrics per media product type (Meta drops unsupported ones over time; see fallback).
INSIGHT_METRICS = {
    "REELS": [
        "views",
        "reach",
        "likes",
        "comments",
        "saved",
        "shares",
        "total_interactions",
        "reposts",
        "ig_reels_avg_watch_time",
        "ig_reels_video_view_total_time",
        "reels_skip_rate",
        "follows",
        "profile_visits",
    ],
    "FEED": [
        "views",
        "reach",
        "likes",
        "comments",
        "saved",
        "shares",
        "total_interactions",
        "reposts",
        "follows",
        "profile_visits",
    ],
    "STORY": ["views", "reach", "replies", "shares", "total_interactions", "follows", "profile_visits", "navigation"],
}

# API metric name -> (normalized column, multiplier)
NORMALIZED = {
    "views": ("views", 1),
    "reach": ("reach", 1),
    "likes": ("likes", 1),
    "comments": ("comments", 1),
    "saved": ("saves", 1),
    "shares": ("shares", 1),
    "reposts": ("reposts", 1),
    "follows": ("follows", 1),
    "profile_visits": ("profile_visits", 1),
    "total_interactions": ("total_interactions", 1),
    "ig_reels_avg_watch_time": ("avg_watch_time_s", 0.001),  # API returns milliseconds
    "ig_reels_video_view_total_time": ("total_watch_time_s", 0.001),
    "reels_skip_rate": ("skip_rate", 1),
}

FORMAT_BY_TYPE = {"REELS": "reel", "STORY": "story", "CAROUSEL_ALBUM": "carousel", "IMAGE": "static", "VIDEO": "video"}


class GraphError(RuntimeError):
    def __init__(self, status: int, payload: dict):
        self.status = status
        self.payload = payload
        err = payload.get("error", {}) if isinstance(payload, dict) else {}
        self.code = err.get("code")
        super().__init__(f"Graph API {status}: {err.get('message', payload)}")


@dataclass
class GraphClient:
    """Thin Graph API client with rate-limit awareness (≈200 calls/hour/user token)."""

    access_token: str
    version: str = "v24.0"
    http: httpx.Client = field(default_factory=lambda: httpx.Client(timeout=30))
    usage_ceiling_pct: int = 85
    sleep: Any = time.sleep
    calls: int = 0

    @property
    def base(self) -> str:
        return f"https://graph.facebook.com/{self.version}"

    def get(self, path_or_url: str, params: dict | None = None) -> dict:
        url = path_or_url if path_or_url.startswith("http") else f"{self.base}/{path_or_url.lstrip('/')}"
        params = dict(params or {})
        if "access_token=" not in url:
            params["access_token"] = self.access_token
        resp = self.http.get(url, params=params)
        self.calls += 1
        self._respect_usage(resp.headers)
        payload = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            raise GraphError(resp.status_code, payload)
        return payload

    def paginate(self, path: str, params: dict | None = None, max_items: int | None = None) -> Iterator[dict]:
        page = self.get(path, params)
        n = 0
        while True:
            for item in page.get("data", []):
                yield item
                n += 1
                if max_items and n >= max_items:
                    return
            nxt = page.get("paging", {}).get("next")
            if not nxt:
                return
            page = self.get(nxt)

    def _respect_usage(self, headers: httpx.Headers) -> None:
        """Back off when Meta reports usage near its limit (X-App-Usage / X-Business-Use-Case-Usage)."""
        worst, regain_min = 0, 0
        for name in ("x-app-usage", "x-business-use-case-usage"):
            raw = headers.get(name)
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except ValueError:
                continue
            entries = [data] if name == "x-app-usage" else [e for v in data.values() for e in v]
            for e in entries:
                worst = max(worst, e.get("call_count", 0), e.get("total_time", 0), e.get("total_cputime", 0))
                regain_min = max(regain_min, e.get("estimated_time_to_regain_access", 0) or 0)
        if worst >= self.usage_ceiling_pct:
            wait_s = max(60, regain_min * 60)
            log.warning("Graph API usage at %s%%; sleeping %ss", worst, wait_s)
            self.sleep(wait_s)


def parse_insights(payload: dict) -> dict[str, Any]:
    """Graph insights -> {metric_name: value}. Handles `values[0].value` and `total_value.value` shapes."""
    out: dict[str, Any] = {}
    for item in payload.get("data", []):
        name = item.get("name")
        if "total_value" in item:
            out[name] = item["total_value"].get("value")
        elif item.get("values"):
            out[name] = item["values"][-1].get("value")
    return out


def normalize_metrics(raw: dict[str, Any]) -> dict[str, float | int | None]:
    cols: dict[str, float | int | None] = {}
    for api_name, value in raw.items():
        if api_name in NORMALIZED and isinstance(value, int | float):
            col, mult = NORMALIZED[api_name]
            cols[col] = value * mult if mult != 1 else value
    return cols


class InsightsFetcher:
    """Fetch insights, degrading gracefully when Meta rejects a metric for a media type."""

    def __init__(self, client: GraphClient):
        self.client = client
        self.unsupported: dict[str, set[str]] = {}

    def fetch(self, media_id: str, product_type: str) -> dict[str, Any]:
        kind = "REELS" if product_type == "REELS" else "STORY" if product_type == "STORY" else "FEED"
        wanted = [m for m in INSIGHT_METRICS[kind] if m not in self.unsupported.setdefault(kind, set())]
        if not wanted:
            return {}
        try:
            return parse_insights(self.client.get(f"{media_id}/insights", {"metric": ",".join(wanted)}))
        except GraphError as e:
            if e.status != 400:
                raise
        # The set was rejected: find which metrics this media type supports.
        result: dict[str, Any] = {}
        for metric in wanted:
            try:
                result.update(parse_insights(self.client.get(f"{media_id}/insights", {"metric": metric})))
            except GraphError as e:
                if e.status != 400:
                    raise
                self.unsupported[kind].add(metric)
                log.info("Metric %s unsupported for %s; skipping for this run", metric, kind)
        return result


def discover_accounts(conn: psycopg.Connection, client: GraphClient) -> list[dict]:
    """Match Instagram accounts reachable by the token to our `accounts` rows (by handle) and store IG ids."""
    pages = client.paginate("me/accounts", {"fields": "name,instagram_business_account{id,username}"})
    found = []
    for page in pages:
        ig = page.get("instagram_business_account")
        if not ig:
            continue
        found.append({"ig_user_id": ig["id"], "username": ig.get("username"), "page": page.get("name")})
        conn.execute(
            "update accounts set ig_user_id=%s where lower(handle)=lower(%s)",
            (ig["id"], ig.get("username")),
        )
    return found


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")


def _upsert_asset(
    conn: psycopg.Connection, media: dict, owner_account_id: uuid.UUID, collaborator_ids: list[uuid.UUID]
) -> uuid.UUID:
    product = media.get("media_product_type") or ("STORY" if media.get("_story") else None)
    fmt = FORMAT_BY_TYPE.get(product) if product in ("REELS", "STORY") else FORMAT_BY_TYPE.get(media.get("media_type"))
    row = conn.execute(
        """
        insert into assets (platform, external_id, permalink, published_at, owner_account_id,
          collaborator_account_ids, media_type, media_product_type, format, caption, raw_payload)
        values ('instagram', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (platform, external_id) do update set
          permalink=excluded.permalink, caption=excluded.caption, raw_payload=excluded.raw_payload,
          collaborator_account_ids=(select array(select distinct unnest(
              assets.collaborator_account_ids || excluded.collaborator_account_ids))),
          updated_at=now()
        returning id
        """,
        (
            media["id"],
            media.get("permalink"),
            _parse_ts(media.get("timestamp")),
            owner_account_id,
            collaborator_ids,
            media.get("media_type"),
            product,
            fmt,
            media.get("caption"),
            Jsonb(media),
        ),
    ).fetchone()
    return row["id"]


def _snapshot(
    conn: psycopg.Connection, asset_id: uuid.UUID, media: dict, raw_metrics: dict, followers: int | None
) -> None:
    published = _parse_ts(media.get("timestamp"))
    age_h = (datetime.now(UTC) - published).total_seconds() / 3600 if published else None
    merged = {"like_count": media.get("like_count"), "comments_count": media.get("comments_count"), **raw_metrics}
    cols = normalize_metrics(raw_metrics)
    cols.setdefault("likes", media.get("like_count"))
    cols.setdefault("comments", media.get("comments_count"))
    names = ["asset_id", "age_hours", "metrics", "follower_count_at_capture", *cols.keys()]
    values = [asset_id, age_h, Jsonb(merged), followers, *cols.values()]
    conn.execute(
        f"insert into asset_metric_snapshots ({', '.join(names)}) values ({', '.join(['%s'] * len(values))})",
        values,
    )


def _store_comments(
    conn: psycopg.Connection,
    client: GraphClient,
    asset_id: uuid.UUID,
    media: dict,
    own_handles: set[str],
    run_id: uuid.UUID,
) -> int:
    stored = 0
    for c in client.paginate(f"{media['id']}/comments", {"fields": COMMENT_FIELDS}):
        thread = [(c, None)] + [(r, c["id"]) for r in c.get("replies", {}).get("data", [])]
        for comment, parent in thread:
            own = (comment.get("username") or "").lower() in own_handles
            raw_id = None
            if not own and (comment.get("text") or "").strip():
                raw_id, _ = insert_raw_document(
                    conn,
                    source_key="ig_own",
                    external_id=f"ig_comment:{comment['id']}",
                    parent_external_id=f"ig_media:{media['id']}" if parent is None else f"ig_comment:{parent}",
                    url=media.get("permalink"),
                    author_hash=hash_author(comment.get("username")),
                    published_at=_parse_ts(comment.get("timestamp")),
                    body_text=comment["text"],
                    engagement={"like_count": comment.get("like_count")},
                    capture_method="api",
                    collection_run_id=run_id,
                    raw_payload={k: v for k, v in comment.items() if k not in ("username", "replies")},
                )
                stored += 1
            conn.execute(
                """insert into asset_comments (asset_id, raw_document_id, external_id, parent_external_id,
                     is_own_reply, published_at, like_count)
                   values (%s,%s,%s,%s,%s,%s,%s)
                   on conflict (external_id) do update set like_count=excluded.like_count""",
                (
                    asset_id,
                    raw_id,
                    comment["id"],
                    parent,
                    own,
                    _parse_ts(comment.get("timestamp")),
                    comment.get("like_count"),
                ),
            )
    return stored


@dataclass
class SyncStats:
    media: int = 0
    stories: int = 0
    snapshots: int = 0
    comments: int = 0
    api_calls: int = 0


def sync_account(
    conn: psycopg.Connection,
    client: GraphClient,
    account_key: str,
    max_media: int | None = None,
    with_comments: bool = True,
) -> SyncStats:
    acct = conn.execute("select id, ig_user_id, handle from accounts where key=%s", (account_key,)).fetchone()
    if not acct or not acct["ig_user_id"]:
        raise RuntimeError(f"Account {account_key} has no ig_user_id; run `bbos ig discover` first")
    own = conn.execute("select id, lower(handle) as handle from accounts where handle is not null").fetchall()
    own_handles = {r["handle"] for r in own}
    id_by_handle = {r["handle"]: r["id"] for r in own}

    stats = SyncStats()
    run_id = start_collection_run(conn, "ig_own", {"account": account_key, "max_media": max_media})
    conn.commit()
    insights = InsightsFetcher(client)
    try:
        profile = client.get(acct["ig_user_id"], {"fields": "followers_count,username"})
        followers = profile.get("followers_count")

        media_iter = client.paginate(
            f"{acct['ig_user_id']}/media", {"fields": MEDIA_FIELDS, "limit": 50}, max_items=max_media
        )
        for media in [*media_iter, *_live_stories(client, acct["ig_user_id"])]:
            collaborators = _collaborator_ids(client, media, id_by_handle, acct["id"])
            asset_id = _upsert_asset(conn, media, acct["id"], collaborators)
            product = media.get("media_product_type") or "FEED"
            raw = insights.fetch(media["id"], product)
            _snapshot(conn, asset_id, media, raw, followers)
            stats.snapshots += 1
            if product == "STORY":
                stats.stories += 1
            else:
                stats.media += 1
                if with_comments and (media.get("comments_count") or 0) > 0:
                    stats.comments += _store_comments(conn, client, asset_id, media, own_handles, run_id)
            conn.commit()  # persist per media so a rate-limit stop keeps progress
        finish_collection_run(conn, run_id, stats.media + stats.stories)
    except Exception as e:
        conn.rollback()
        finish_collection_run(conn, run_id, stats.media + stats.stories, status="partial", error=str(e)[:2000])
        conn.commit()
        raise
    stats.api_calls = client.calls
    conn.commit()
    return stats


def _live_stories(client: GraphClient, ig_user_id: str) -> list[dict]:
    """Stories currently live (Meta only exposes them for 24h). A permission gap shouldn't stop the feed sync."""
    try:
        stories = list(client.paginate(f"{ig_user_id}/stories", {"fields": MEDIA_FIELDS}))
    except GraphError as e:
        if e.status != 400:
            raise
        log.warning("Could not list stories for %s: %s", ig_user_id, e)
        return []
    return [{**s, "_story": True, "media_product_type": "STORY"} for s in stories]


def _collaborator_ids(client: GraphClient, media: dict, id_by_handle: dict, owner_id: uuid.UUID) -> list:
    """Our other accounts that co-authored this media (Instagram Collab)."""
    if media.get("_story"):
        return []
    try:
        data = client.get(f"{media['id']}/collaborators", {"fields": "username"}).get("data", [])
    except GraphError as e:
        if e.status == 400:  # endpoint not available for this media/token; Collab info unknown
            return []
        raise
    ids = [id_by_handle.get((c.get("username") or "").lower()) for c in data]
    return [i for i in ids if i and i != owner_id]


def client_from_settings() -> GraphClient:
    s = get_settings()
    if not s.meta_access_token:
        raise RuntimeError("META_ACCESS_TOKEN is not set (see docs/SETUP.md §4)")
    return GraphClient(access_token=s.meta_access_token, version=s.meta_graph_version)
