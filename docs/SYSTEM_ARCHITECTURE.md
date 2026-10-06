# System Architecture — Brit & Berat Content Intelligence OS

Status: **Proposed** (awaiting approval) · Last updated: 2026-10-06

## 1. Executive summary

The system is a **data pipeline with narrowly-scoped LLM judgment steps**, built on one hosted
Postgres database. It is not an autonomous agent swarm and not a prompt that "gives 10 ideas".

```
 ┌─────────────┐   ┌──────────────┐   ┌───────────────┐   ┌──────────────┐   ┌────────────┐
 │  COLLECT    │──▶│  EXTRACT     │──▶│  UNDERSTAND   │──▶│  OPPORTUNITY │──▶│  DECIDE    │
 │ (code,APIs, │   │ (LLM: atomic │   │ (embeddings + │   │ (LLM: opps → │   │ (human:    │
 │  manual     │   │  signals w/  │   │  clustering + │   │  30–50 concepts│ │  approve / │
 │  inbox)     │   │  verbatim    │   │  LLM labeling,│   │  → score →   │   │  reject +  │
 │             │   │  quotes)     │   │  trends)      │   │  critic → ~10)│  │  reason)   │
 └─────────────┘   └──────────────┘   └───────────────┘   └──────────────┘   └─────┬──────┘
        ▲                                                                          │
        │          ┌──────────────┐   ┌───────────────┐   ┌──────────────┐         ▼
        └──────────│  LEARN       │◀──│  MEASURE      │◀──│  CREATE &    │◀── approved
                   │ (hypotheses, │   │ (IG insights, │   │  DISTRIBUTE  │
                   │  learnings,  │   │  ManyChat     │   │ (templates,  │
                   │  calibration)│   │  events, GA4) │   │  human posts)│
                   └──────────────┘   └───────────────┘   └──────────────┘
                     All stages read/write ONE Postgres DB (evidence → … → outcome lineage)
```

Design commitments:
- **One source of truth**: Postgres (Supabase) with pgvector. Every object has provenance.
- **Deterministic orchestration**: Python code decides *what runs when*; LLMs only perform defined
  judgment tasks with structured (schema-validated) outputs.
- **Evidence lineage end-to-end**: raw document → signal → cluster → opportunity → concept →
  recommendation → asset → metrics → learning. Any claim in a report is clickable back to source text.
- **Humans approve** recommendations, public content, resources, and funnels.

## 2. Feasibility assessment (researched October 2026)

| Capability | Feasible? | How | Main limitation |
|---|---|---|---|
| Own Instagram performance (reach, views, saves, shares, comments, watch time, skip rate, profile visits, follows) | ✅ High | Instagram Graph API (official), own Business/Creator account | Story insights only while story is live (24h) → daily job required; 200 calls/hr/user; some metrics renamed/deprecated in 2025 (plays/impressions → views) |
| Own Instagram comments | ✅ High | Graph API comments edge | Only own media |
| Instagram category intelligence (what everyone posts about Istanbul/Turkey travel) | ⚠️ Partial → good with layering | Hashtag Search API + Business Discovery API (official, automated) + weekly supervised Claude-in-Chrome market scan | APIs give captions + like/comment counts only (no views/saves; 30 hashtags/7 days); keyword search & visible view counts only via browser, low volume, small account-risk |
| Browser-assisted research (Reddit interim, Trends CSVs, IG keyword search) | ✅ supervised | Claude in Chrome on your computer, or local Claude Code with `--chrome`; results saved to Inbox endpoint | Not available from cloud sessions; human-started, low volume, not unattended on third-party platforms |
| ManyChat flow building | ✅ via browser | Claude in Chrome builds flows in ManyChat's editor from approved specs, left unpublished for your test + publish | UI changes can break the workflow; never auto-publish |
| Reddit posts/comments | ⚠️ Gated | Reddit Data API **after approval**; commercial use needs an agreement | Self-serve keys closed; approval 2–4 weeks; Reddit actively litigating scrapers → **no scraping** |
| YouTube videos + comments | ✅ High | YouTube Data API v3 (free, 10,000 units/day) | `search.list` = 100 units; `commentThreads.list` = 1 unit → curate channels/videos, search sparingly |
| Tripadvisor / Rick Steves / Facebook groups | ⚠️ Manual only | Evidence Inbox (human capture) | No APIs; ToS prohibit scraping |
| Google Trends | ⚠️ Gated | Official Trends API is application-only alpha; meanwhile manual CSV export | Niche queries are sparse/noisy; relative not absolute |
| Search demand (keyword volume) | ✅ | DataForSEO (Google Ads keyword data, pay-per-use) or Google Ads Keyword Planner | Monthly granularity; costs small |
| Our website search queries | ✅ High | Google Search Console API (16 months) | Needs site verified in GSC |
| Website traffic/conversions | ✅ High | GA4 Data API | Needs GA4 + conversion events configured |
| ManyChat data | ⚠️ Partial | ManyChat API (Pro plan) + "External Request" actions that POST events to our webhook | **No transcript export; cannot create/edit flows via API**; no idempotency on sends |
| Customer inquiry emails | ✅ | Gmail API (OAuth) | PII-heavy → extract questions, strip identities |
| Revenue attribution | ❌ Not yet | Depends on booking system (unknown) + source capture | Biggest gap; requires a business-process change (see §8) |
| LLM extraction / clustering labels / strategy / critique | ✅ High | Claude API (structured outputs, Batch API at 50% cost, prompt caching) | Cost scales with volume; manageable (see §7) |
| On-brand static creatives (carousels, stories, PDFs, covers) | ✅ High | HTML/CSS templates + Playwright (headless Chromium) → PNG/PDF | Requires an upfront design system build |
| B-roll tagging & search | ✅ Medium-High | ffmpeg scene detection → keyframes → Claude vision tags + speech transcription; pgvector search | Claude does not ingest video directly; keyframe sampling is the bridge. Twelve Labs is the upgrade path for video-native search |
| Rough-cut Reels | ⚠️ Medium | Shot list + timeline generated by system → Remotion/Shotstack render, or OpenTimelineIO/FCPXML export to CapCut/DaVinci for human finishing | Fully automatic "finished" Reels are low-ROI; human finishing recommended |
| Auto-publishing | 🚫 By design | — | Principle #11: humans publish |

## 3. What Claude Code does vs. what needs other components

| Work | Who/what does it |
|---|---|
| Write, test, and maintain the codebase; run migrations; debug | **Claude Code** (this tool) |
| Interactive analysis ("why did airport content spike?", "draft the ManyChat spec for BAZAAR") | **Claude Code**, querying the DB via CLI/skills |
| Scheduled data collection (daily IG sync, weekly YouTube pull) | **Python jobs** on a scheduler (GitHub Actions cron) — not Claude Code. Cloud sessions are ephemeral and not a scheduler |
| LLM steps inside the pipeline (extraction, clustering labels, opportunities, critique) | **Claude API** called from Python (Anthropic SDK), with versioned prompts and logged runs |
| Receiving ManyChat events in real time | **Webhook endpoint** (Supabase Edge Function) writing to Postgres |
| Storing evidence, content memory, metrics, learnings | **Postgres + pgvector** (Supabase) + **object storage** (raw snapshots, media) |
| Rendering carousels/PDFs | **Playwright + HTML templates** (Python job) |
| Video processing | **ffmpeg** + transcription (Whisper-class model) + Claude vision on keyframes; render via Remotion or export timeline |
| Building ManyChat flows | **Claude in Chrome** in ManyChat's editor from approved specs (draft/unpublished); **you test and publish** |
| Browser research sessions (IG keyword search, Reddit interim, Trends CSVs) | **Claude in Chrome** / local Claude Code `--chrome`, started by you; output to the Inbox endpoint |
| Publishing to Instagram | **Human** |
| Approving recommendations/content/funnels | **Brit / Berat** |

Claude Code also gets project **skills** (in `.claude/skills/`) that wrap the CLI, e.g.
`/weekly-cycle`, `/capture-evidence`, `/review-recommendations`, `/explain-recommendation <id>`.
These are conveniences on top of the same deterministic pipeline, not a separate system.

## 4. Recommended technology stack

| Layer | Choice | Why | Alternatives considered |
|---|---|---|---|
| Language | **Python 3.12** + `uv` | Best ecosystem for data/ML/media; Anthropic SDK first-class | TypeScript (better for UI; worse for data/ML) |
| Data models | **Pydantic v2** | Same schemas validate LLM structured outputs and DB rows | — |
| CLI | **Typer** (`bbos`) | Every stage runnable/re-runnable by hand or by Claude Code | — |
| Database | **Supabase Postgres + pgvector** | Hosted (survives ephemeral sessions), SQL, JSONB, vector search, row-level security, storage, edge functions in one; free→$25/mo | Neon + S3 (fine, more pieces); SQLite (not shared/hosted); dedicated vector DB (unnecessary) |
| Object storage | **Supabase Storage** for raw snapshots & generated assets; **Google Drive** stays the home of raw video originals (index, don't copy) | Simple; video is large | Cloudflare R2 when media volume grows |
| LLM | **Claude API** — default `claude-opus-5-5`, per-stage override in `config/models.yaml` | Structured outputs, Batch API (−50%) for bulk extraction, prompt caching for stable context (brand guide, taxonomy) | Cheaper models for bulk stages once an eval proves quality holds — a cost decision we make with data |
| Embeddings | **Voyage AI** (`voyage-3.5` class) via API, stored in pgvector | Strong retrieval quality, cheap | Local open-source embedding model (no API cost; slightly more ops) |
| Clustering | **UMAP + HDBSCAN** (scikit-learn ecosystem) + LLM cluster labeling; incremental assignment between full re-clusters | Handles unknown cluster counts and noise; cheap | k-means (needs k); pure-LLM clustering (expensive, unstable) |
| Stats | pandas + statsmodels / simple Bayesian (beta-binomial, log-normal shrinkage) | Honest uncertainty with small n | — |
| Scheduling | **GitHub Actions cron** | Free, in-repo, secrets management, logs | Supabase cron (pg_cron) for DB-only jobs; Managed Agents scheduled deployments later if useful |
| Webhooks | **Supabase Edge Function** (ManyChat → `/events/manychat`) | Always-on, tiny | Cloudflare Worker |
| Reports | Generated **HTML** (Jinja) published as a private page + Markdown copy in DB | Readable, linkable evidence drill-down | Notion/Google Docs export later |
| Review UI (Phase 2) | Minimal **Streamlit** app (approve/reject + reason, evidence explorer) | Fast to build, Python-native | Next.js (nicer, slower to build); Supabase table editor (MVP fallback) |
| Creative rendering | **Jinja HTML/CSS templates + Playwright** → PNG (1080×1350, 1080×1920) and PDF | Pixel-controlled brand system; Chromium already available | Canva Connect autofill (enterprise-gated); Figma (no render-from-data API); AI image gen (brand drift — rejected per your preference) |
| Video | **ffmpeg + PySceneDetect** (shots), transcription (Whisper-class via API or local), Claude vision on keyframes; **Remotion** or **Shotstack** for rough cuts; **OpenTimelineIO** export for CapCut/DaVinci/Premiere finishing | Controlled, inspectable, human-finishable | Twelve Labs (video-native search, add if keyframe tagging is insufficient); Creatomate (template video) |

## 5. Component architecture

```
bbos/
  collectors/        # one module per source; pure I/O, no LLM. Write raw_documents.
    instagram.py  youtube.py  manual_inbox.py  manychat_webhook (edge fn)  gsc.py  ga4.py
    reddit.py (after approval)  dataforseo.py  trends_csv.py  gmail_inquiries.py  competitors_ig.py
  extract/           # LLM: raw_document → evidence_items (signals) with verbatim quotes + annotations
  understand/        # embeddings, clustering, cluster labeling, trend/velocity math, taxonomy mapping
  market/            # competitor/market content index, coverage & gap analysis
  memory/            # content memory: assets, metric snapshots, attribution, performance analysis
  opportunities/     # opportunity synthesis, concept generation, scoring, critic, portfolio selection
  resources/         # resource-opportunity evaluation (format choice)
  campaigns/         # campaign architecture, ManyChat flow specs
  learning/          # hypotheses, experiments, learnings, score calibration
  creative/          # design system, templates, renderers (Phase 5)
  video/             # B-roll ingest, tagging, search, shot lists, timelines (Phase 6–7)
  reports/           # weekly intelligence report
  llm/               # Claude client wrapper: models, prompt registry, structured output, batch, cost logging
  db/                # SQLAlchemy/psycopg access layer, repositories
config/              # offers.yaml, taxonomy.yaml, models.yaml, scoring.yaml, brand_voice.md, banned_phrases.yaml
prompts/             # versioned prompt files
db/migrations/       # SQL migrations
evals/               # golden sets + eval scripts for each LLM stage
.claude/skills/      # Claude Code skills wrapping the CLI
```

Each stage: `bbos <stage> run --run-id <id>` reads its inputs from the DB, writes outputs with the
same `pipeline_run_id`, and can be re-run idempotently. A `bbos cycle weekly` command chains them.

## 6. Weekly cycle (target state)

| When | Job |
|---|---|
| Daily 06:00 TRT | IG sync (media, insights, stories before expiry, comments); ManyChat subscriber field sync |
| Continuous | ManyChat External Request events → webhook → `attribution_events` |
| Weekly (Sun) | YouTube pull, GSC/GA4 pull, competitor IG pull, keyword volumes (monthly), Reddit (once approved) |
| Weekly (Mon) | Extract → embed → cluster/assign → trend math → opportunities → concepts → score → critique → select → report |
| Weekly (Mon) | Brit reviews ~10 recommendations: approve / reject / modify + reason (captured) |
| Continuous | Evidence Inbox: Brit/Berat/guides capture threads, DMs, tour questions anytime |
| Monthly | Performance analysis deep-dive, hypothesis review, learning confidence updates |
| Quarterly | Scoring calibration against outcomes; taxonomy review; facts registry re-verification |

## 7. Cost envelope (rough, to be measured in MVP)

- Supabase: $0–25/mo. GitHub Actions: free tier likely sufficient. YouTube API: free.
- Claude API: a weekly cycle processing ~1,000 raw documents (~1.5M input / ~0.5M output tokens for
  extraction via Batch API on Opus 5.5) is on the order of **$10 for extraction**, plus synthesis,
  critique, and report steps, likely **$20–60/week** total. We measure actual cost per stage in the
  MVP and only then consider cheaper models for bulk stages (with an eval to prove quality holds).
- Embeddings: cents per week. DataForSEO: $50 minimum deposit lasts a long time at our volume.
- ManyChat Pro (API access) — you may already have it.

## 8. Major technical & strategic limitations (honest list)

1. **Signal volume is smaller than "thousands per week".** Truly relevant, American-authored Istanbul
   travel conversations across accessible sources are likely in the low hundreds per week. The
   system's power comes from **accumulation over months** and from **first-party data**, not weekly volume.
2. **Trend detection needs baselines.** "Rising" claims require ≥8 weeks of consistent collection per
   source. Until then, reports say "baseline building" rather than inventing trends.
3. **Identifying "Americans" in public data is probabilistic.** We infer from cues (USD, US cities,
   TSA/Global Entry, "flying from JFK") and store `us_likelihood` with confidence. We never assert it.
4. **Learning from our own performance is slow.** At ~4–7 posts/week, topic- and hook-level effects
   need months and/or deliberate experiments to separate from noise (one viral Reel can dominate).
   The system reports effect sizes with uncertainty and refuses conclusions below sample thresholds.
5. **Revenue attribution is the weakest link — and the most valuable.** Without capturing source at
   booking (ManyChat subscriber ID, UTM'd links, "how did you hear about us"), we can measure reach →
   engagement → leads but not → revenue. This needs a process change, not just code.
6. **ManyChat is a closed box for flow authoring** and has no transcript export. We instrument flows
   with External Request events and custom fields from the start.
7. **Reddit and Google Trends are gated.** We apply immediately but do not depend on them for MVP.
8. **Platform APIs change.** Meta deprecated and renamed key metrics in 2025. Collectors isolate
   metric mapping in one place and store raw API payloads so history survives renames.
9. **Travel facts go stale** (entry fees, e-visa rules, opening days, airport procedures). A
   **facts registry** with `last_verified_at` gates factual claims in content.

## 9. Security, privacy & compliance

- **Secrets**: GitHub Actions secrets + Supabase Vault; `.env` locally (gitignored); `.env.example` documents
  names only. Least-privilege scopes (read-only where possible). Meta long-lived tokens expire after 60
  days → automated refresh job + alert.
- **Repository**: keep private (contains strategy and business data references). Never commit data exports.
- **PII minimization**: public-source usernames are hashed (salted) — we need patterns, not identities.
  ManyChat: store subscriber ID + segmentation fields, not full transcripts. Emails remain in the email
  platform; our DB keeps a reference and consent flag. Gmail inquiries: extract the question text and
  trip context; drop names/emails/phones before LLM processing where feasible.
- **Laws**: Turkey's KVKK (business is Turkish), GDPR for EU leads, US state privacy laws (e.g. CCPA).
  Email capture in ManyChat must include clear consent language. Data retention policy: raw public
  documents 24 months; deleted-at-source content purged where the source's terms require (Reddit API terms do).
- **Platform terms**: use each platform's data only as its terms allow (Meta Platform Terms, YouTube API
  Services Terms, Reddit Data API Terms). No scraping against ToS. No buying scraped data.
- **Public use of audience words**: internal analysis may quote verbatim; public content paraphrases
  unless permission is obtained.
- **Prompt injection**: user-generated text is wrapped as data; extraction calls have no tools and use
  structured outputs; outputs are validated (e.g. quotes must be substrings of the source).
- **Approval gates**: nothing public-facing (posts, DMs, flows, resources) is deployed by the system.
- **Auditability**: every LLM call logged with model, prompt version, input hashes, cost, run ID.

## 10. Assumptions I'm challenging

| Your assumption | My recommendation |
|---|---|
| Research should extract "hundreds/thousands of signals" per cycle | Volume isn't the goal; **coverage and evidence quality** are. Accumulate a durable corpus; prioritize first-party signals (inquiry emails, DMs, tour questions) which carry real purchase intent |
| A 17-dimension opportunity score | Too many overlapping, LLM-guessed dimensions produce false precision. Use **gates + a few measured factors + objective-specific value + pairwise critique + portfolio selection** (see SCORING_MODEL.md) |
| External listening is the core intelligence source | It tells you what the *market* asks. **Your inquiries, DMs, and the questions guests ask on tours** tell you what *buyers* ask. Add a "Field Intelligence" capture channel for Brit, Berat, and guides |
| Weekly "what is rising/falling" | Valid only after baselines exist; early reports must say so |
| System should produce near-finished Reels | Highest ROI is **shot lists + B-roll retrieval + script/timing + timeline export**; humans finish in CapCut. Revisit auto-rendering after Phase 6 |
| Claude can build ManyChat funnels | Yes, through **Claude in Chrome** in ManyChat's editor (the API cannot create flows). Claude designs the spec, builds it as a draft; you test and publish |
| Revenue learning will emerge from content data | Only if bookings capture source. Decide the booking attribution process now |
| Many agents collaborating | One orchestrated pipeline with ~12 narrow LLM roles and one independent critic is more reliable, cheaper, and debuggable |
