# Integrations — Brit & Berat Content Intelligence OS

Status: **Proposed** · Research current as of 2026-10-06 (platform rules change — re-verify before building each collector)

Preference order for every source: **official API → authenticated integration/MCP → reputable
licensed third-party API → manual export → manual capture → (only with explicit approval and ToS
permission) browser automation.** We do not scrape against terms of service.

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
| 8 | **Reddit** (r/istanbul, r/travel, r/Turkey, r/solotravel, r/TravelNoPics, r/onebag…) | ★★★★★ candid American planning talk | Reddit Data API **after approval**; commercial use → agreement | ⚠️ Apply now; no scraping; honor deletions | High once approved | Apply now; build Phase 3 |
| 9 | **Keyword demand** | ★★★ absolute search volume & seasonality | DataForSEO (Google Ads keyword data; pay-as-you-go) or Google Ads Keyword Planner | ✅ licensed data | High | Phase 3 |
| 10 | **Google Trends** | ★★ relative interest, seasonality | Apply for official Trends API alpha; meanwhile monthly manual CSV export | ✅ | Medium (sparse for niche terms) | Phase 3 |
| 11 | **Competitor/creator Instagram** | ★★★ market saturation & formats | Business Discovery API (public business/creator accounts: captions, like/comment counts) + limited hashtag search (30/7 days) | ✅ official | Medium | Phase 3 |
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

## 3. Build order (first integrations)

1. **Instagram own account** (API, with CSV backfill fallback) — the foundation of content memory.
2. **Evidence Inbox** — unlocks Reddit/forums/DMs/emails/field notes compliantly on day one.
3. **YouTube Data API** — the one automated external listener for MVP.
4. **ManyChat webhook events + subscriber fields** — per-post lead attribution (Phase 2).
5. **Gmail inquiries + booking system source capture** — purchase intent and revenue (Phase 2).
6. **GSC + GA4** (Phase 3). 7. **Reddit API** (when approved). 8. **DataForSEO/Trends**. 9. **Competitor IG**.

## 4. Credentials & accounts needed (eventually)

| Item | For | When |
|---|---|---|
| Anthropic API key (org account with billing) | all LLM stages | MVP |
| Supabase project (you own it; invite me via service key in secrets) | DB, storage, webhooks | MVP |
| Voyage AI API key (or approve local embeddings) | embeddings | MVP |
| Meta developer app + Instagram Business/Creator account access (or a Meta Business Suite CSV export of last 12–24 months) | IG sync | MVP |
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
