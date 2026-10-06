import httpx
import pytest
import respx

from bbos.collectors.instagram import (
    GraphClient,
    InsightsFetcher,
    discover_accounts,
    normalize_metrics,
    parse_insights,
    sync_account,
)

G = "https://graph.facebook.com/v24.0"


def client():
    return GraphClient(access_token="t", http=httpx.Client(), sleep=lambda s: None)


def test_parse_insights_handles_both_shapes():
    payload = {
        "data": [
            {"name": "reach", "values": [{"value": 1200}]},
            {"name": "views", "total_value": {"value": 5400}},
        ]
    }
    assert parse_insights(payload) == {"reach": 1200, "views": 5400}


def test_normalize_converts_watch_time_ms_to_seconds():
    cols = normalize_metrics({"ig_reels_avg_watch_time": 7300, "saved": 41, "unknown": 3})
    assert cols == {"avg_watch_time_s": 7.3, "saves": 41}


@respx.mock
def test_insights_fallback_skips_unsupported_metric_for_rest_of_run():
    def handler(request):
        metric = request.url.params["metric"]
        if "," in metric or metric == "reels_skip_rate":
            return httpx.Response(400, json={"error": {"message": "invalid metric", "code": 100}})
        return httpx.Response(200, json={"data": [{"name": metric, "values": [{"value": 1}]}]})

    respx.get(url__regex=rf"{G}/m\d/insights").mock(side_effect=handler)
    f = InsightsFetcher(client())
    first = f.fetch("m1", "REELS")
    assert "reels_skip_rate" not in first and first["reach"] == 1
    assert "reels_skip_rate" in f.unsupported["REELS"]
    f.fetch("m2", "REELS")
    assert not any(
        c.request.url.params.get("metric") == "reels_skip_rate" for c in respx.calls if "/m2/" in str(c.request.url)
    )


@respx.mock
def test_backs_off_when_usage_high():
    slept = []
    c = GraphClient(access_token="t", http=httpx.Client(), sleep=slept.append)
    respx.get(f"{G}/me").mock(
        return_value=httpx.Response(
            200, json={}, headers={"x-app-usage": '{"call_count": 92, "total_time": 10, "total_cputime": 5}'}
        )
    )
    c.get("me")
    assert slept == [60]


@respx.mock
def test_full_sync_writes_assets_snapshots_comments(conn):
    conn.execute("update accounts set handle='britinistanbul' where key='brit_in_istanbul'")
    conn.execute("update accounts set handle='britandberat' where key='brit_and_berat'")
    respx.get(f"{G}/me/accounts").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {
                        "name": "Brit in Istanbul",
                        "instagram_business_account": {"id": "111", "username": "britinistanbul"},
                    },
                    {"name": "Brit & Berat", "instagram_business_account": {"id": "222", "username": "britandberat"}},
                ]
            },
        )
    )
    respx.get(f"{G}/111").mock(return_value=httpx.Response(200, json={"followers_count": 5000}))
    respx.get(f"{G}/111/media").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "m1",
                        "caption": "Landing at IST at night? Here's what to do",
                        "media_type": "VIDEO",
                        "media_product_type": "REELS",
                        "permalink": "https://instagram.com/reel/abc",
                        "timestamp": "2026-09-30T18:00:00+0000",
                        "like_count": 300,
                        "comments_count": 2,
                    }
                ]
            },
        )
    )
    respx.get(f"{G}/111/stories").mock(return_value=httpx.Response(200, json={"data": []}))
    respx.get(f"{G}/m1/collaborators").mock(
        return_value=httpx.Response(200, json={"data": [{"username": "britandberat"}]})
    )
    respx.get(f"{G}/m1/insights").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"name": "reach", "values": [{"value": 9000}]},
                    {"name": "saved", "values": [{"value": 410}]},
                    {"name": "ig_reels_avg_watch_time", "values": [{"value": 6500}]},
                ]
            },
        )
    )
    respx.get(f"{G}/m1/comments").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "c1",
                        "text": "Is the Havaist bus OK with two big suitcases?",
                        "username": "traveler_jen",
                        "timestamp": "2026-10-01T10:00:00+0000",
                        "like_count": 4,
                        "replies": {
                            "data": [
                                {
                                    "id": "c2",
                                    "text": "Yes! Plenty of room.",
                                    "username": "britinistanbul",
                                    "timestamp": "2026-10-01T11:00:00+0000",
                                }
                            ]
                        },
                    }
                ]
            },
        )
    )

    c = client()
    found = discover_accounts(conn, c)
    assert {f["username"] for f in found} == {"britinistanbul", "britandberat"}
    stats = sync_account(conn, c, "brit_in_istanbul")
    assert (stats.media, stats.comments) == (1, 1)

    asset = conn.execute("select * from assets").fetchone()
    bb = conn.execute("select id from accounts where key='brit_and_berat'").fetchone()["id"]
    assert asset["format"] == "reel" and asset["collaborator_account_ids"] == [bb]
    snap = conn.execute("select * from asset_metric_snapshots").fetchone()
    assert (snap["reach"], snap["saves"], snap["avg_watch_time_s"], snap["likes"]) == (9000, 410, 6.5, 300)
    docs = conn.execute("select body_text, author_hash from raw_documents").fetchall()
    assert len(docs) == 1 and "Havaist" in docs[0]["body_text"]
    assert docs[0]["author_hash"] and "traveler_jen" not in docs[0]["author_hash"]
    own = conn.execute("select is_own_reply from asset_comments where external_id='c2'").fetchone()
    assert own["is_own_reply"] is True

    # Re-sync: no duplicate asset/comments, new snapshot appended.
    sync_account(conn, c, "brit_in_istanbul")
    assert conn.execute("select count(*) n from assets").fetchone()["n"] == 1
    assert conn.execute("select count(*) n from raw_documents").fetchone()["n"] == 1
    assert conn.execute("select count(*) n from asset_metric_snapshots").fetchone()["n"] == 2


def test_sync_requires_discovered_account(conn):
    with pytest.raises(RuntimeError, match="ig discover"):
        sync_account(conn, client(), "brit_and_berat")
