# Data Model — Brit & Berat Content Intelligence OS

Status: **Proposed** · Database: Postgres (Supabase) + pgvector · Last updated: 2026-10-06

## 1. Principles

1. **Immutable raw layer.** What we collected is stored exactly as received (payload + text + hash),
   never edited. Everything downstream is *derived* and can be regenerated.
2. **Atomic evidence.** One `evidence_item` = one signal (one question, one fear, one desire…) with a
   **verbatim quote** and character offsets into its raw document.
3. **Derived objects carry provenance**: `pipeline_run_id`, `model`, `prompt_version`, `created_at`.
4. **Lineage via link tables.** Evidence → clusters → opportunities → concepts → recommendations →
   assets → metrics → learnings are joined by explicit many-to-many tables, never by free text.
5. **Time series, not overwrites.** Metrics are snapshots (`asset_metric_snapshots`), so we can see
   performance at 24h / 7d / 30d and survive API metric renames.
6. **Controlled vocabularies** (taxonomy, offers, travel stages, emotions, objectives) live in tables
   seeded from `config/*.yaml`, so analysis is consistent across months.
7. **Confidence everywhere.** Any inferred field has a sibling confidence (0–1) or an ordinal level.

## 2. Entity overview

```
sources ─┬─ collection_runs ─── raw_documents ─── evidence_items ─┬─ evidence_annotations
         │                                                        ├─ evidence_embeddings
         │                                                        └─ cluster_members ── clusters ── cluster_snapshots
         │                                                                                  │
facts_registry   offers   taxonomy_nodes   brand_rules                              opportunity_clusters
                                                                                           │
                       hypotheses ── experiments ── experiment_arms             opportunities ── opportunity_evidence
                            │                             │                              │
                        learnings ◀───────────────────────┤                          concepts ── concept_scores
                                                          │                              │      └─ critiques
                                         assets (content memory) ◀── recommendations ◀──┘
                                           │        └─ campaigns ── campaign_assets
                                           ├─ asset_metric_snapshots
                                           ├─ asset_comments (→ also raw_documents)
                                           └─ attribution_events ── audience_profiles (ManyChat) ── bookings
                                                 resources ── resource_deliveries
             decisions (human approve/reject + reason on any object)     pipeline_runs  llm_calls
             broll_clips ── clip_segments ── clip_tags (Phase 6)          reports
```

## 3. Tables

Types abbreviated. All tables have `id uuid pk`, `created_at timestamptz` unless noted.

### 3.1 Collection & raw evidence

**sources** — a data source definition.
`key text unique` (e.g. `youtube`, `reddit`, `ig_own`, `manual_inbox`, `gmail_inquiries`, `field_notes`),
`name`, `access_method enum(official_api, mcp, authenticated_integration, third_party_api, manual_export, manual_capture, webhook)`,
`terms_basis text` (which ToS/permission allows this use), `retention_days int`, `is_first_party bool`, `active bool`.

**collection_runs** — one execution of a collector.
`source_id`, `started_at`, `finished_at`, `status`, `params jsonb` (queries, channel ids, date ranges),
`items_fetched int`, `error text`, `pipeline_run_id`.

**raw_documents** — immutable snapshot of one retrieved unit (a Reddit post, a comment, a YouTube
comment thread, an IG comment, an email question, a pasted forum thread, a tour field note).
| column | notes |
|---|---|
| `source_id`, `collection_run_id` | provenance |
| `external_id text` | platform id; unique with `source_id` |
| `parent_external_id text` | thread structure (comment → post) |
| `url text` | canonical reference |
| `author_hash text` | salted hash of username; never the raw handle |
| `author_meta jsonb` | non-identifying cues only (e.g. self-stated home country, flair) |
| `published_at timestamptz`, `fetched_at timestamptz` | |
| `title text`, `body_text text` | normalized plain text |
| `raw_payload jsonb` or `raw_object_path text` | full API response / HTML snapshot in storage |
| `content_hash text` | sha256 of body_text (dedupe + tamper evidence) |
| `engagement jsonb` | upvotes, likes, reply count, view count at fetch time |
| `language text` | |
| `capture_method enum` | api, manual_paste, manual_url, export_file, webhook |
| `captured_by text` | for manual items: brit / berat / guide / claude-assisted |
| `deleted_at_source bool`, `purge_after date` | compliance |
| `relevance jsonb` | output of the relevance filter: `{is_relevant, us_likelihood, us_cues[], confidence}` |

### 3.2 Evidence (atomic signals)

**evidence_items** — one signal extracted from a raw document.
| column | notes |
|---|---|
| `raw_document_id` | |
| `signal_type enum` | question, fear, objection, desire, excitement, misconception, planning_problem, recommendation_request, experience_report, complaint, purchase_intent, resource_request, cultural_curiosity |
| `verbatim_quote text` | **must be an exact substring** of `raw_documents.body_text` (validated in code) |
| `quote_start int`, `quote_end int` | char offsets |
| `normalized_statement text` | short neutral restatement (e.g. "How do I get from IST to Sultanahmet late at night?") |
| `topic_node_id`, `subtopic_node_ids uuid[]` | taxonomy |
| `travel_stage enum` | dreaming, considering, planning, booked, in_trip, post_trip, unknown |
| `emotion enum[]`, `emotion_intensity smallint (1–5)` | anxiety, confusion, excitement, frustration, curiosity, distrust, overwhelm, delight |
| `purchase_intent smallint (0–3)` | 0 none · 1 latent · 2 evaluating · 3 ready to book |
| `offer_fit jsonb` | `[{offer_key, fit: natural/plausible/forced, rationale}]` |
| `resource_signal bool` + `resource_hint text` | asks for/implies a checklist, map, guide… |
| `us_likelihood real` | inherited from document, may be refined |
| `trip_context jsonb` | party type, trip length, month, first-time vs repeat, budget cues (when stated) |
| `extraction_confidence real` | |
| `pipeline_run_id`, `model`, `prompt_version` | provenance |

**evidence_embeddings** — `evidence_item_id`, `model`, `embedding vector(1024)`.

**audience_phrases** (the "audience language bank") — `evidence_item_id`, `phrase text`
(verbatim), `phrase_type enum(hook_candidate, objection_wording, desire_wording, fear_wording)`.
Copywriting draws from here, not from imagination.

### 3.3 Understanding

**taxonomy_nodes** — hierarchical topic tree (`parent_id`, `key`, `label`, `description`, `active`).
Seed examples: arrival/IST airport · transport · neighborhoods & where to stay · safety & scams ·
money/lira/tipping · food · Old City sights · Asian Side · bazaars & shopping · culture & etiquette ·
mosques & dress code · religion & Ramadan · day trips · itinerary length · seasonality/weather ·
visa/entry · connectivity/SIM · family travel · solo female travel · accessibility · nightlife ·
hammam · Bosphorus · prices & budget · cruise port days · layovers.
New clusters can *propose* taxonomy nodes; a human approves additions.

**clusters** — `label`, `canonical_question`, `summary`, `status (active/merged/dormant)`,
`merged_into_id`, `centroid vector`, `first_seen_at`, `last_seen_at`, `taxonomy_node_id`, `pipeline_run_id`.

**cluster_members** — `cluster_id`, `evidence_item_id`, `membership_prob real`, `assigned_run_id`.

**cluster_snapshots** — weekly metrics for trend math:
`cluster_id`, `week_start date`, `signal_count`, `independent_author_count`, `source_count`,
`first_party_count`, `mean_emotion_intensity`, `purchase_intent_dist jsonb`, `travel_stage_dist jsonb`,
`engagement_sum`, `velocity_z real`, `baseline_weeks int` (how much history backs the velocity number).

### 3.4 Market / competitor content

**market_content** — public content by other creators/competitors (Business Discovery, YouTube):
`platform`, `account_handle`, `external_id`, `url`, `published_at`, `caption_or_title`, `format`,
`public_metrics jsonb` (likes, comments, views where public), `topic_node_ids`, `angle_summary`,
`embedding vector`.
**market_coverage** — per cluster per period: how many/how well competitors address it:
`cluster_id`, `period`, `matching_content_count`, `best_answer_quality smallint (1–5)`, `gap_notes`.

### 3.5 Business knowledge

**offers** — `key` (old_city_tour, asian_side_tour, airport_transfer, bazaar_experience,
private_experience, planning_service), `name`, `description`, `price_range`, `url`, `active`.
**facts_registry** — verifiable travel facts used in content: `claim`, `value`, `source_url`,
`last_verified_at`, `verified_by`, `volatility enum(stable/seasonal/volatile)`, `expires_at`.
Content containing a factual claim must link to a fact that hasn't expired.
**brand_rules** — voice rules, banned phrases, required disclosures, sensitive-topic guidance (seeded
from `config/brand_voice.md`, `config/banned_phrases.yaml`).

### 3.6 Opportunities → concepts → recommendations

**opportunities** — a strategic opening, not yet a post.
`title`, `opportunity_type enum(content, resource, offer_messaging, faq_page, experiment)`,
`audience_need text`, `why_now text`, `bb_advantage text`, `primary_offer_key`, `offer_fit enum`,
`measured_factors jsonb` (see SCORING_MODEL), `evidence_strength enum(anecdotal, emerging, established)`,
`status`, `pipeline_run_id`.
**opportunity_clusters**, **opportunity_evidence** — links (evidence links carry `role: primary/supporting/counter`).

**concepts** — candidate content ideas (30–50 per cycle).
`opportunity_id`, `format enum(reel, carousel, story_sequence, static, live, guide_page, pdf, email)`,
`objective enum(reach, trust, authority, education, engagement, lead, conversion, experiment, storytelling)`,
`angle text`, `hook_options jsonb` (with source phrases), `outline text`, `cta text`,
`perspective_used enum(american, local, both)`, `required_assets jsonb`, `similar_past_asset_ids uuid[]`,
`novelty_sim real` (max cosine to last-90-day assets), `status (candidate/rejected/transformed/selected)`.
**concept_scores** — one row per dimension per scoring run: `concept_id`, `dimension`, `value`,
`scale`, `rationale`, `evidence_ids uuid[]`, `scorer (code|llm)`, `scoring_version`.
**critiques** — `concept_id`, `verdict (accept/transform/reject)`, `failure_modes text[]`,
`any_creator_test (pass/fail)`, `notes`, `transformed_concept_id`, `critic_version`.
**recommendations** — the ~10 selected: `concept_id`, `cycle_id`, `rank`, `portfolio_slot`
(e.g. reach / trust / lead / experiment), `why_it_exists text`, `expected_outcome jsonb`, `status`.

### 3.7 Human decisions (taste memory)

**decisions** — `object_type`, `object_id`, `decided_by`, `decision (approve/reject/modify/defer)`,
`reason_codes text[]` (e.g. off_brand, already_done, not_true_to_us, boring, wrong_timing, love_it),
`comment`, `decided_at`. These are training signal for the critic and selector.

### 3.8 Content memory

**assets** — every piece we publish (and drafts).
| column | notes |
|---|---|
| `platform`, `external_id`, `permalink`, `published_at` | |
| `format`, `duration_s` | |
| `topic_node_id`, `subtopic_node_ids` | |
| `hook_text`, `hook_type enum` | e.g. american_pov, local_secret, mistake_warning, myth_bust, question, story, list |
| `angle`, `perspective_used` | |
| `script`, `caption`, `on_screen_text` | |
| `cta_type enum`, `cta_text`, `manychat_keyword` | |
| `offer_key`, `resource_id`, `objective` | |
| `recommendation_id`, `campaign_id`, `experiment_arm_id` | lineage (nullable for legacy content) |
| `production_meta jsonb` | who's on camera, location, music, template used |
| `labels_source enum(manual, llm_backfill, system)` + `label_confidence` | legacy content is auto-labeled then spot-checked |
| `embedding vector` | for novelty/similarity |

**asset_metric_snapshots** — `asset_id`, `captured_at`, `age_hours`, `metrics jsonb` (raw names as the
API returned them) plus normalized columns: `views`, `reach`, `likes`, `comments`, `saves`, `shares`,
`reposts`, `follows`, `profile_visits`, `avg_watch_time_s`, `total_watch_time_s`, `skip_rate`,
`follower_count_at_capture`. Normalized derived metrics computed in views (e.g. saves/reach,
shares/reach, follows per 1k reach, completion proxy = avg_watch_time / duration).

**asset_comments** — comments on our posts (also inserted as `raw_documents` so they become evidence).

### 3.9 Funnels, leads, revenue

**audience_profiles** — ManyChat subscriber reference: `manychat_subscriber_id`, `ig_user_hash`,
`first_seen_at`, `segments jsonb` (travel_month, party_type, trip_stage, interests), `email_ref`
(pointer/ID in email platform, not the address), `consent jsonb`.
**attribution_events** — `event_type (keyword_trigger, flow_step, resource_delivered, email_captured,
question_answered, link_click, inquiry, booking)`, `audience_profile_id`, `asset_id` (via keyword→asset map),
`manychat_keyword`, `payload jsonb`, `occurred_at`, `source (manychat_webhook, ga4, booking_system, manual)`.
**bookings** — `external_ref`, `offer_key`, `amount`, `currency`, `booked_at`, `audience_profile_id`
(nullable), `attribution_source text`, `attribution_confidence`.
**resources** — `title`, `format`, `delivery (manychat/email/web)`, `url`, `opportunity_id`, `version`, `status`.
**campaigns**, **campaign_assets** — campaign spine and each asset's `role` and `objective`.

### 3.10 Learning

**hypotheses** — `statement`, `rationale`, `origin (performance_analysis, research, brit, critic)`,
`status (proposed/testing/supported/refuted/inconclusive/retired)`, `confidence enum(anecdote, signal, pattern, validated)`,
`prior_belief real`, `posterior_belief real`, `review_by date`.
**experiments** — `hypothesis_id`, `design text`, `primary_metric`, `min_sample`, `start/end`, `status`, `result_summary`.
**experiment_arms** — `experiment_id`, `label`, `variant_description`; assets link here.
**learnings** — `statement`, `scope` (e.g. "Reels about airport"), `effect_size`, `interval jsonb`,
`n`, `confidence enum`, `evidence (asset ids, experiment ids)`, `valid_from`, `review_by`, `status (active/superseded)`.
Learnings are consumed by the scorer and strategist; they expire/require review so stale beliefs decay.

### 3.11 Operations

**pipeline_runs** — `cycle_id`, `stage`, `status`, `started/finished`, `config_hash`, `git_sha`.
**llm_calls** — `pipeline_run_id`, `stage`, `model`, `prompt_key`, `prompt_version`, `input_tokens`,
`output_tokens`, `cache_read_tokens`, `cost_usd`, `latency_ms`, `batch_id`, `status`.
**reports** — `cycle_id`, `type (weekly)`, `html_path`, `markdown`, `stats jsonb`.

### 3.12 Video (Phase 6)

**broll_clips** — `storage_uri` (Drive file ID), `filename`, `duration_s`, `resolution`, `orientation`,
`fps`, `shot_at`, `location_hint`, `quality_flags`, `rights (own/licensed)`.
**clip_segments** — per detected shot: `clip_id`, `start_s`, `end_s`, `keyframe_paths`, `transcript`,
`description`, `embedding vector`.
**clip_tags** — `segment_id`, `tag_type (person, location, activity, object, mood, shot_type, subject, use_case)`,
`value`, `confidence`, `source (vision_llm, manual)`.

## 4. Evidence preservation — how it works

1. **Capture**: collector writes `raw_documents` with full payload (or HTML/PDF snapshot in storage),
   `content_hash`, URL, timestamps, capture method, and the ToS basis recorded on `sources`.
2. **Verbatim guarantee**: extraction returns quote + offsets; code verifies
   `body_text[start:end] == verbatim_quote` (with whitespace normalization). Failures are rejected,
   not "fixed" by the model. **This makes fabricated quotes structurally impossible to store.**
3. **Lineage**: every report sentence that asserts something about the audience is generated from
   structured objects with evidence IDs, and the HTML report renders those as expandable citations
   (quote, source, date, link).
4. **Reproducibility**: derived rows store `pipeline_run_id`, `model`, `prompt_version`; prompts are
   versioned files; re-running a stage on the same raw layer is possible.
5. **Compliance lifecycle**: `purge_after` and `deleted_at_source` drive a scheduled purge job; derived
   evidence from purged documents is anonymized (quote removed, statistics retained) where required.
6. **Manual evidence is first-class**: the Evidence Inbox stores pasted text, URL, screenshot (optional),
   who captured it and why — the same verbatim rules apply.

## 5. Key indexes & views

- `raw_documents (source_id, external_id) unique`, `(published_at)`, GIN on `engagement`.
- HNSW indexes on all `embedding` columns.
- `evidence_items (topic_node_id, travel_stage, signal_type)`.
- Views: `v_cluster_weekly_trend`, `v_asset_performance_normalized` (metrics at fixed ages: 24h, 7d, 30d,
  normalized by follower count and rolling account median), `v_keyword_funnel` (keyword → triggers →
  emails → inquiries → bookings), `v_recommendation_outcomes` (score vs. realized performance — for calibration).

## 6. Migration approach

SQL migrations (`db/migrations/NNN_name.sql`), applied by a small runner or Supabase CLI. MVP creates
sections 3.1–3.8 + 3.11 only; later phases add 3.9, 3.10 fully, and 3.12.
