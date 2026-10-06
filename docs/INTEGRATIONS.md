# Integrations — Brit & Berat Content Intelligence OS

Status: **Proposed** · Research current as of 2026-10-06 (platform rules change — re-verify before building each collector)

Preference order for every source: **official API → authenticated integration/MCP → reputable
licensed third-party API → manual export → manual capture → (only with explicit approval and ToS
permission) browser automation.** We do not scrape against terms of service.

**Browser-assisted tier (added 2026-10-06):** Claude in Chrome / Claude Code's Chrome integration can
operate *your own logged-in browser* in **supervised, low-volume, human-started sessions** that save
what they find to the Evidence Inbox. This is a research assistant, not a scraper: no headless bots,
no bulk crawling, no unattended schedules on third-party platforms. See §2.10–2.11.

## 1. Source matrix

| # | Source | Value | Method | Compliance | Reliability | Phase |
|---|---|---|---|---|---|---|
| 1 | **Our Instagram** (media, insights, comments, stories) | ★★★★★ content memory + audience questions | Instagram Graph API (official) via a Meta app linked to our Business/Creator account | ✅ Own data | High (watch token expiry, metric renames) | MVP (CSV export fallback) |
| 2 | **Evidence Inbox** (manual capture: Reddit threads, Tripadvisor/Rick Steves forums, FB groups, DMs, WhatsApp inquiries, tour field notes) | ★★★★★ broad + first-party | CLI/Claude Code skill, later a browser bookmarklet & simple form; paste text/URL/file | ✅ Human captures for internal research; no automated scraping | High | MVP |
| 3 | **YouTube** (Istanbul travel videos + comments) | ★★★★ large volume of American traveler questions in comments | YouTube Data API v3 (official; 10k units/day free) | ✅ YouTube API Services Terms | High | MVP |
| 4 | **ManyChat** (keyword triggers, segmentation answers, email captures, resource deliveries) | ★★★★★ leads attribution | External Request actions in flows → our webhook; ManyChat API (Pro) for subscriber fields/tags | ✅ Own data | Medium-High | Phase 2 |
| 5 | **Customer inquiry emails** (Gmail) | ★★★★★ highest purchase intent | Gmail API (OAuth, read-only scope, label-filtered) | ✅ Own data; PII minimization | High | Phase 2 (MVP: paste examples into Inbox) |
| 6 | **Google Search Console** | ★★★★ what people search to find us | GSC API (official) | ✅ | High | Phase 3 |
| 7 | **GA4** | ★★★ traffic & conversions | GA4 Data API (official) | ✅ | High | Phase 3 |
| 8 | **Reddit** (r/istanbul, r/travel, r/Turkey, r/solotravel, r/TravelNoPics, r/onebag…) | ★★★★★ candid American planning talk | Reddit Data API **after approval**; commercial use → agreement. Until then: supervised Claude-in-Chrome research sessions (reads threads you'd read, saves quotes to the Inbox) | ⚠️ Apply now; no bulk scraping; honor deletions | High once approved | Browser sessions MVP; API Phase 3 |
| 9 | **Keyword demand** | ★★★ absolute search volume & seasonality | DataForSEO (Google Ads keyword data; pay-as-you-go) or Google Ads Keyword Planner | ✅ licensed data | High | Phase 3 |
| 10 | **Google Trends** | ★★ relative interest, seasonality | Apply for official Trends API alpha; meanwhile monthly CSV export — done by Claude in Chrome in a supervised session | ✅ / ⚠️ low-volume | Medium (sparse for niche terms) | Phase 3 |
| 11 | **Instagram market intelligence** (what *everyone* posts about Istanbul / Turkey travel: top Reels, formats, hooks, creators, saturation) | ★★★★★ market saturation, winning formats, gaps | Three layers: (a) official Hashtag Search API (top/recent media for ≤30 hashtags/week), (b) Business Discovery API on a creator watchlist, (c) supervised Claude-in-Chrome "market scan" sessions for keyword search & visible view counts | ✅ (a)(b) official · ⚠️ (c) low-volume supervised browsing, see §2.10 | Medium | **MVP** (pulled forward) |
| 12 | **Competitor YouTube** | ★★★ | YouTube Data API | ✅ | High | Phase 3 |
| 13 | **Reviews** (our Google reviews, Tripadvisor reviews) | ★★★★ what delighted/annoyed buyers | Google Business Profile API (own); Tripadvisor manual export/capture | ✅ | Medium | Phase 3 |
| 14 | **Context feeds** (US State Dept Türkiye advisory, IST airport news, lira exchange rate, Turkish holidays/Ramadan dates, major events) | ★★★ explains spikes in fear/interest | Public pages/RSS, free FX API, static calendars | ✅ | High | Phase 3 |
| 15 | **Booking system / payments** | ★★★★★ revenue attribution | Depends on your tool (FareHarbor/Bókun/Stripe/WooCommerce/manual?) — API or export | ✅ Own data | TBD | Phase 2–3 |
| 16 | **TikTok** | ★★ | Research API is academic-only → manual capture only | ⚠️ | — | Manual only |
| 17 | **Facebook groups** | ★★★ | No API for group content → manual capture, anonymized | ⚠️ Respect group rules/privacy | — | Manual only |

## 2. Details per integration

### 2.1 Instagram Graph API (own account)
- **Setup**: Instagram Business or Creator account; Meta developer app; use "Instagram API with
  Instagram Login" (or Facebook Login if the account is linked to a Facebook Page). For our own
  account, the app can stay in development mode with us as app roles — no public app review needed
  for our own data (verify at setup; Meta changes this periodically).
- **Data**: media list (caption, type, timestamp, permalink, product type REELS/FEED/STORY), media
  insights (views, reach, likes, comments, saved, shares, total_interactions, reposts,
  ig_reels_avg_watch_time, ig_reels_video_view_total_time, reels_skip_rate, profile_visits, follows
  where available), comments + replies, account insights (followers, demographics — aggregate only).
- **Gotchas**: Story insights only while the story is live → **daily** (better: 2×/day) story sync.
  2025 deprecations (plays/impressions → views; video_views removed) → store raw payloads, map names in
  one adapter. Rate limit ~200 calls/hour/user token. Long-lived tokens expire after 60 days → refresh job.
- **Backfill**: API returns historical media; insights for older posts are generally available but
  some metrics did not exist historically. Supplement with a Meta Business Suite CSV export if gaps appear.

### 2.2 Evidence Inbox (manual & assisted capture)
The single most important "integration" for compliant breadth.
- **MVP**: `bbos inbox add --url ... --text-file ... --note ... --captured-by brit` and a Claude Code
  skill `/capture-evidence` where you paste a thread, DM, or email; the system stores it as a raw document.
- **Phase 2**: a browser bookmarklet / tiny form that posts selected page text + URL to a Supabase function.
- **Field Intelligence**: Berat/guides send voice memos ("today three guests asked whether the Blue
  Mosque is open on Fridays") → transcription → raw documents with `source=field_notes`. This is
  proprietary signal no competitor has.
- **Claude-assisted discovery**: in a Claude Code session, Claude can use web search to *find*
  relevant public threads and propose a capture list; a human confirms what gets captured.

### 2.3 YouTube Data API v3
- Curate: ~20–50 channels/videos about Istanbul travel with American audiences (e.g., first-time
  visitor guides, "mistakes to avoid", food tours) + a handful of weekly searches.
- Budget: search.list = 100 units (≤20 searches/day budget), commentThreads.list = 1 unit/page (cheap).
- Store video metadata as `market_content`; comments as `raw_documents`.

### 2.4 ManyChat
**Researched capabilities (Pro plan required for API):**
- API (Bearer token): page info, tags, custom fields, bot fields, subscriber info / find by name or
  custom field, add/remove tags, set custom fields, `sendContent` (dynamic blocks) and `sendFlow`
  (≈100 calls/subscriber/hour), across Messenger/Instagram/WhatsApp.
- **Cannot**: create/edit flows or keyword triggers via API; export conversation transcripts; no
  idempotency key on sends (retries can duplicate messages).
- **Messaging policy**: Instagram's 24-hour messaging window applies; outside it, sends need specific
  tags/opt-ins. Comment-to-DM automation is supported natively in ManyChat.
- No official ManyChat MCP server (third-party wrappers exist; we don't need them).

**Our design:**
1. Claude generates **flow specs** (Markdown + a structured JSON spec: trigger keyword, messages,
   buttons, questions, field writes, tags, External Request events, consent copy).
2. Brit builds the flow in ManyChat's UI from the spec (human gate G4).
3. Every meaningful step includes an **External Request** action POSTing
   `{event, keyword, subscriber_id, field values, timestamp}` to our Supabase webhook → `attribution_events`.
4. Segmentation answers are stored as ManyChat **custom fields** (travel_month, party_type,
   trip_stage, interests, first_time_istanbul) and mirrored to `audience_profiles` via the API.
5. Each Reel/post CTA keyword maps to an asset in `assets.manychat_keyword` → per-post lead attribution.
6. Emails captured flow to your email platform (ManyChat native integration or webhook); our DB stores a reference.

### 2.5 Gmail inquiries
- Read-only OAuth scope, restricted to a label (e.g. `Inquiries`) to avoid touching personal mail.
- Pre-processing strips names/emails/phones; extraction captures questions, trip context, objections.
- Phase 2. For MVP, paste 20–50 representative (anonymized) inquiries into the Inbox.

### 2.6 Reddit
- **Action now**: register a Reddit app and submit a Data API access request describing low-volume,
  read-only research of public travel subreddits for audience understanding (no AI training, no
  redistribution). Expect 2–4 weeks; commercial terms may apply.
- If approved: OAuth client, pull recent posts/comments from target subreddits + keyword searches;
  honor deletions (purge job); respect rate limits.
- If denied/too costly: continue with Evidence Inbox for Reddit, and consider a reputable licensed data
  provider only after reviewing its legal basis (Reddit is litigating against scraping intermediaries).

### 2.7 Search demand: GSC, DataForSEO, Trends
- GSC API: queries, pages, impressions, clicks, CTR, position (16 months) — what Americans type when
  they find us. Strongly recommended if you have a website with content.
- DataForSEO: monthly volumes for a curated keyword universe (~300–1,000 Istanbul travel terms, US
  location) refreshed monthly. Cheap at our scale.
- Trends: apply for alpha; meanwhile monthly CSV export for ~20 head terms (US geo). Treated as weak
  seasonality signal only.

### 2.8 Competitor Instagram (Business Discovery)
- Query public business/creator accounts by username: recent media captions, like_count, comments_count,
  timestamps, permalinks. No views/saves. Good enough for "what formats/topics are saturated".
- Hashtag search: ≤30 unique hashtags/7 days; useful for a few category tags only.
- No third-party IG scrapers.

### 2.9 Video & creative tooling (Phase 5–7)
- Rendering: Playwright (Chromium is available in our environment) + HTML/CSS templates.
- Video analysis: ffmpeg/PySceneDetect, transcription service or local Whisper-class model, Claude vision
  on keyframes; optional Twelve Labs for video-native semantic search.
- Rough cuts: Remotion (React-based, self-hosted render) or Shotstack (JSON timeline API, hosted);
  timeline export via OpenTimelineIO → CapCut/DaVinci/Premiere for finishing.
- Raw video stays in Google Drive (connected); we index by Drive file ID.

### 2.10 Instagram market intelligence (Istanbul / Turkey travel category)

Goal: know what the whole category is posting — which topics, hooks, formats and creators win, what
is saturated, and what is missing — so our recommendations avoid crowded angles and borrow proven formats.

**Layer A — Hashtag Search API (official, automated, weekly).** Requires the Instagram API *with
Facebook Login* (our IG account linked to a Facebook Page) and the hashtag-search permission (verify
whether app review is needed for our own-account use at setup). Budget: 30 unique hashtags per rolling
7 days, e.g. #istanbul #istanbultravel #istanbulguide #visitistanbul #turkeytravel #traveltürkiye
#istanbultips #istanbulfood #grandbazaar #cappadocia (adjacent) … Returns top & recent media with
caption, media type, like count, comment count, permalink, timestamp. **Does not return views, saves,
shares, or (reliably) the author.** Captions → hook/topic/angle extraction; permalinks feed Layer C.

**Layer B — Business Discovery API (official, automated, weekly).** A watchlist of ~30–60 Istanbul /
Turkey travel creators and competitors (seeded by you + discovered via Layers A/C). Per account:
followers, media count, recent posts with captions, like/comment counts. Lets us compute each
creator's *relative* winners (post vs. their own median) — the best proxy for "what's working".

**Layer C — Claude in Chrome market scan (supervised, ~30–45 min/week).** What the APIs can't give:
Instagram *keyword* search results ("Istanbul travel", "Istanbul tips", "Turkey travel", "Istanbul
airport"…), Reels tab ordering, **visible view counts on Reels grids**, audio used, on-screen hook
text, cover style. You start the session from a saved shortcut; Claude browses like a researcher
would, records structured observations (permalink, creator, format, hook, visible views/likes, topic,
angle, what's distinctive) and saves them to the Inbox as `market_content` with
`capture_method = browser_assisted`. You watch or spot-check.

*Risk, stated plainly:* Meta's terms prohibit collecting data by automated means without permission.
A slow, supervised session viewing a few dozen posts looks like normal browsing and is low risk, but
it is not zero, and the account at risk is **your main acquisition channel**. Rules: low volume,
human-started, no bulk scrolling/downloading, no running unattended on a schedule, stop at any
warning/CAPTCHA. The alternative is a paid social-listening tool with licensed Instagram data — worth
pricing if this becomes core.

**Outputs:** `market_content` rows (with embeddings) → market coverage per cluster, "saturated vs.
underserved" in scoring factor **G**, a format/hook library ("myth-bust POV reels on mosques: 9 of the
top 30; nobody covers the IST arrival flow from an American POV"), and the report section
"Content market observations / What competitors are missing".

### 2.11 Browser-assisted workflows (Claude in Chrome) — where they fit

**How it works:** Claude in Chrome (Pro/Max/Team/Enterprise) drives *your* Chrome with your logins;
it has per-site permissions, pauses at logins/CAPTCHAs, and supports saved shortcuts and scheduled
tasks. Claude Code can also drive Chrome, but **only from a local session on your computer**
(`claude --chrome`, or `@browser` in VS Code) — not from cloud sessions like this one. The Claude
desktop app (Cowork) hosts it too.

**The integration pattern:** a browser session finds and reads; it saves structured results through
our **Inbox endpoint** (a small authenticated web form / Supabase function), or a local Claude Code
session calls `bbos inbox add`. Then the normal pipeline takes over (extraction, verified quotes, clustering).

| Workflow | Browser role | Verdict | Guardrails |
|---|---|---|---|
| **ManyChat flow building** | Claude builds the flow in ManyChat's editor from our approved flow spec: keyword trigger, messages, buttons, questions, custom-field writes, tags, External Request events | ✅ **Recommended** (Phase 4). Your own account; fills the gap that ManyChat's API cannot create flows | Built as **unpublished/draft** (or with a test keyword); you test on a test IG account; **you** publish (gate G4). Screenshot of the final flow saved with the spec |
| **ManyChat data pull** | Export subscriber/flow stats from the dashboard when the API lacks them | ✅ OK | Read-only; PII rules apply |
| **Instagram market scan** | §2.10 Layer C | ⚠️ Low-volume, supervised only | As above |
| **Reddit research sessions** | Search target subreddits, open relevant threads, save verbatim quotes + URLs to the Inbox | ⚠️ Interim until API approval. Reddit's terms restrict automated collection; a supervised session reading ~20–40 threads is research-scale, not scraping | Human-started, ≤1 session/week, no bulk crawling, no scheduling; switch to the API when approved |
| **Google Trends** | Enter ~20 terms (US geo), download CSVs, save to Inbox | ✅ Low risk (replaces the manual export) | Monthly, supervised |
| **Tripadvisor / Rick Steves / FB groups** | Read threads you point it to; save quotes | ⚠️ Same as Reddit | Manual-scale only; anonymize FB group content |
| **Meta Business Suite exports** | Download CSV exports when the API is unavailable | ✅ | — |

**What browser automation is *not* for:** anything unattended and recurring on Instagram, Reddit, or
Tripadvisor; publishing posts; sending DMs; anything a reliable API already does. Browser UIs change, so
these workflows are allowed to break without breaking the pipeline: the pipeline only reads what reached the Inbox.

## 3. Build order (first integrations)

1. **Instagram own account** (API, with CSV backfill fallback) — the foundation of content memory.
2. **Evidence Inbox + Inbox endpoint** — unlocks Reddit/forums/DMs/emails/field notes and browser-assisted sessions.
3. **Instagram market intelligence** — Hashtag Search + Business Discovery (automated) + weekly supervised Claude-in-Chrome market scan.
4. **YouTube Data API** — automated external listener.
5. **ManyChat webhook events + subscriber fields** — per-post lead attribution (Phase 2); Claude-in-Chrome flow building (Phase 4).
6. **Gmail inquiries + booking system source capture** — purchase intent and revenue (Phase 2).
7. **GSC + GA4** (Phase 3). 8. **Reddit API** (when approved; browser research sessions until then). 9. **DataForSEO/Trends**.

## 4. Credentials & accounts needed (eventually)

| Item | For | When |
|---|---|---|
| Anthropic API key (org account with billing) | all LLM stages | MVP |
| Supabase project (you own it; invite me via service key in secrets) | DB, storage, webhooks | MVP |
| Voyage AI API key (or approve local embeddings) | embeddings | MVP |
| Meta developer app + Instagram Business/Creator account access (or a Meta Business Suite CSV export of last 12–24 months); IG account linked to a Facebook Page (needed for Hashtag Search / Business Discovery) | IG sync + market intel | MVP |
| Claude Pro/Max/Team plan with Claude in Chrome installed on your computer | browser-assisted sessions | MVP |
| Watchlist of Istanbul/Turkey travel creators & competitors you follow | IG market intel | MVP |
| Google Cloud project + YouTube Data API key | YouTube | MVP |
| GitHub Actions secrets access (repo admin) | scheduler | MVP |
| ManyChat Pro API key + list of current flows/keywords | funnels | Phase 2 |
| Gmail OAuth (read-only, label-scoped) or exported inquiries | inquiries | Phase 2 |
| Booking system name + API/export access | revenue | Phase 2 |
| Email platform (Klaviyo/Mailchimp/ConvertKit/…?) API key | email captures | Phase 2–4 |
| Google Search Console + GA4 access (service account) | search/web | Phase 3 |
| Reddit app credentials (after approval) | Reddit | Phase 3 |
| DataForSEO account ($50 deposit) | keyword volume | Phase 3 |
| Google Drive folder of B-roll (shared to service account) | video | Phase 6 |
