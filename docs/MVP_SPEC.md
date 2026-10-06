# MVP Spec — "Evidence → Recommendations v0"

Status: **Proposed — awaiting approval** · Last updated: 2026-10-06

## 1. Goal

Prove the core loop's hardest and most valuable part: **turning real audience evidence into ~10
distinctive, evidence-backed content recommendations that Brit would actually make — and that are
fully traceable to source.** Small enough to build in ~2–3 weeks; real enough to use every week.

## 2. The user story

> Every Monday, Brit opens one report. It says what Americans planning Istanbul asked, feared, and
> wanted this week (with real quotes), what our own content history suggests (with honest confidence),
> and presents ~10 recommended pieces of content — each with *why it exists*, its objective, the Brit &
> Berat angle, suggested hooks drawn from audience language, the offer bridge (if natural), and
> clickable evidence. Brit approves/rejects each with a reason in under 15 minutes. The system
> remembers those decisions.

## 3. In scope

| Component | MVP version |
|---|---|
| **DB** | Supabase Postgres + pgvector; tables: sources, collection_runs, raw_documents, evidence_items, evidence_embeddings, audience_phrases, taxonomy_nodes, clusters, cluster_members, cluster_snapshots, offers, facts_registry, brand_rules, opportunities (+links), concepts, concept_scores, critiques, recommendations, decisions, assets, asset_metric_snapshots, asset_comments, pipeline_runs, llm_calls, reports |
| **Collector: Instagram own** | One-time backfill (last 12–24 months: media, captions, insights, comments) via Graph API; **CSV import fallback** if the API setup is delayed. Weekly refresh |
| **Collector: Evidence Inbox** | CLI + Claude Code skill to add pasted text / URL+text / files with `captured_by` and note. Seed corpus: ~150–300 items gathered in a "research sprint" (forum threads, YouTube comments, our IG comments, anonymized inquiries/DMs, Berat's tour questions) |
| **Instagram market intelligence** | Hashtag Search API (≤30 hashtags/week) + Business Discovery on a 30–60 creator watchlist (automated weekly) + Brit's swipe file (standout post links + why) resolved via official APIs + YouTube view counts → `market_content`. Feeds the Gap factor, the format/hook library, and the "content market observations / what competitors are missing" report sections. No browser automation |
| **Collector: YouTube** | Curated list of ~20–40 Istanbul travel videos/channels + ≤10 searches/week; comments → raw docs, videos → market_content |
| **Relevance + Extraction** | Batch API; structured outputs; **code-verified verbatim quotes**; US-likelihood with cues |
| **Understanding** | Voyage embeddings; HDBSCAN clustering; LLM cluster labels (canonical question, summary, misconceptions); simple weekly snapshots (no trend claims yet — "baseline building") |
| **Content memory v0** | Assets from IG backfill, LLM auto-labeled (topic, hook type, angle, objective, CTA) with confidence; Brit spot-checks ~20. Simple normalized performance table by topic/format/hook type with sample sizes and confidence labels |
| **Opportunities** | Strategist → 15–25 opportunities; Concept Generator → 30–50 concepts |
| **Scoring v1** | Gates (evidence, novelty, banned phrases, purpose) + Opportunity Strength (D, I, G-lite from YouTube market content, R rubric) + evidence confidence; per-objective value with historical prior (shrunk) |
| **Critic** | Independent LLM critic with any-creator test + one transform round; banned-phrase linter; 90-day similarity check |
| **Selection** | Portfolio of ~10 with objective mix + diversity constraints |
| **Resource flag** | Each recommendation states whether a resource is warranted (yes/no + format + evidence) — no resource production yet |
| **Report** | Weekly HTML report (+ Markdown) with sections below, every claim linked to evidence |
| **Decisions** | `bbos review` CLI / Claude Code skill to approve/reject/modify with reason codes |
| **Ops** | GitHub Actions weekly run; cost logged per stage; `bbos doctor` |

### MVP report sections
1. Research volume (documents, signals, sources, first-party share — exact counts)
2. What Americans are asking (top clusters, canonical questions, representative quotes)
3. What they're worried about / what they want / misconceptions
4. High-purchase-intent questions
5. What our content history suggests (with sample sizes and confidence labels; "insufficient data" where true)
6. Content market observations from Instagram + YouTube (what the Istanbul/Turkey category posts, winning formats/hooks, saturated vs. missing topics)
7. Top ~10 recommendations (full cards as in SCORING_MODEL §5)
8. Resource opportunities (flagged, not built)
9. Proposed hypotheses (≤3) to test
10. Appendix: rejected concepts and why (so you can overrule the critic)

## 4. Out of scope for MVP (explicitly)

ManyChat integration (incl. browser-built flows) · Gmail collector · GSC/GA4 · Trends/DataForSEO ·
rising/falling trend claims · designed creatives · video · campaign generation · scripts/captions
writing · Streamlit UI · auto-publishing (never).

## 5. Acceptance criteria

1. **Traceability**: 100% of recommendations link to ≥ gate-threshold evidence; 100% of quotes in the
   DB pass substring verification against stored raw documents.
2. **Usefulness**: across two consecutive cycles, Brit marks ≥6 of 10 recommendations "would make"
   (approve or approve-with-edits).
3. **Distinctiveness**: ≤1 recommendation per cycle judged by Brit as "any creator could post this".
4. **Honesty**: report never states a trend or performance conclusion below the confidence thresholds;
   spot-check of 10 random claims finds 0 unsupported.
5. **Repeatability**: the weekly cycle runs end-to-end from one command/scheduled job, idempotently.
6. **Cost**: measured cost per cycle reported; target < $75/cycle at MVP volume.
7. **Time**: Brit's review takes ≤15 minutes.

## 6. Build plan (sequence)

| Step | Deliverable |
|---|---|
| 1 | Scaffold, Supabase, migrations, LLM wrapper, configs (offers, taxonomy v1, brand voice, banned phrases) |
| 2 | Evidence Inbox + raw document model + quote verification utility (with tests) |
| 3 | IG backfill (API or CSV) → assets + metric snapshots + comments as raw docs |
| 4 | YouTube collector + IG Hashtag Search / Business Discovery collectors + swipe-file intake |
| 5 | Relevance + extraction (batch) + extraction eval on ~50 hand-labeled docs |
| 6 | Embeddings + clustering + cluster analyst |
| 7 | Legacy content auto-labeling + performance table |
| 8 | Strategist → concepts → scoring v1 → critic → selection |
| 9 | Report generator + review/decision capture |
| 10 | Weekly GitHub Actions job; first live cycle; tune; second cycle |

Parallel human task during steps 1–4: **research sprint** — you (and I, via Claude-assisted discovery
with your confirmation) capture the seed corpus into the Evidence Inbox.

## 7. Decisions (resolved 2026-10-06 unless noted)

Resolved: architecture + MVP approved; Instagram via API; two accounts (Brit in Istanbul 5–7/week, Brit & Berat 3 unique/week, daily stories on both); Stripe + ActiveCampaign. Open: watchlist and swipe file (system will propose candidates).

Original list:

1. Approve the architecture (pipeline + Supabase + Python + Claude API) — or flag concerns.
2. Approve the MVP scope above (especially: no ManyChat/video in MVP).
3. Choose the Instagram path for MVP: API setup now, or CSV export first.
4. Confirm you'll own the accounts (Supabase, Anthropic, Google Cloud, Meta app) and share credentials via secrets.
5. Weekly production capacity and desired objective mix (default: 3 reach · 2 trust · 2 lead · 1 conversion · 1 experiment · 1 story).
6. Creator/competitor watchlist (30–60 accounts) and a first batch of 20–30 swipe-file posts you think are great, each with one line on why.
