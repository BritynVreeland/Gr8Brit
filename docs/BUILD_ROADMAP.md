# Build Roadmap — Brit & Berat Content Intelligence OS

Status: **Proposed** · Last updated: 2026-10-06

Each phase ends with a usable capability and explicit exit criteria. We don't start a phase until the
previous one's exit criteria are met and you've approved moving on. Durations assume part-time
collaboration with fast feedback from you; they are estimates, not promises.

## Phase 0 — Foundations (≈1 week)
- Repo scaffold (Python/uv, Typer CLI, config, prompts, evals dirs), Supabase project, migrations for
  core tables, LLM wrapper with cost logging, secrets setup, CI (lint + tests).
- Seed configs: `offers.yaml`, `taxonomy.yaml`, `brand_voice.md`, `banned_phrases.yaml`, initial
  `facts_registry` (top ~30 facts used in your content).
- File the **Google Trends API alpha** application (long lead time).
- **Exit**: `bbos doctor` passes (DB, API keys, storage); a raw document can be inserted and read back.

## Phase 1 — MVP: Evidence → Intelligence → Recommendations (≈2–3 weeks)
See `MVP_SPEC.md`. Instagram history backfill, Evidence Inbox (+ endpoint for browser sessions), Instagram market intelligence (Hashtag Search, Business Discovery, weekly Claude-in-Chrome scan), YouTube collector, extraction with
verified quotes, clustering, opportunities, concepts, scoring v1, critic, ~10 recommendations, weekly
report with evidence drill-down, decision capture.
- **Exit**: two consecutive weekly cycles where you rate ≥6/10 recommendations "would make", 100% quote
  verification, cost per cycle measured.

## Phase 2 — Measurement loop & Content Memory (≈2–3 weeks)
- Automated daily IG sync (incl. stories), legacy content auto-labeling (topic, hook type, angle,
  objective) with your spot-check.
- ManyChat: webhook endpoint + External Request event standard + custom-field mirror; keyword→asset map.
- Booking attribution process (source field / ManyChat ID / UTM links) agreed and implemented with your
  booking tool; Gmail inquiries collector (label-scoped, PII-stripped).
- Performance Analyst v1 (normalized metrics, shrinkage, confidence levels); hypotheses registry;
  first designed experiment.
- Streamlit review app (approve/reject + reasons, evidence explorer, asset performance).
- **Exit**: every new post has metrics at 24h/7d/30d automatically; per-keyword lead counts visible; first
  "what we learned" section with honest confidence labels.

## Phase 3 — Wider listening & market intelligence (≈2–3 weeks)
- GSC + GA4, DataForSEO keyword universe, Trends (browser-downloaded CSVs or alpha API), YouTube market index, review sources, context feeds (advisories, FX, holidays).
- Trend analyst with baselines; market coverage & gap analysis ("what competitors are missing").
- Weekly report reaches full target structure.
- **Exit**: report includes rising/falling with stated baseline length; competitor gap section backed by indexed content.

## Phase 4 — Resources, campaigns & ManyChat design (≈2–3 weeks)
- Resource Evaluator live; resource library table; first 1–2 evidence-backed resources produced.
- Campaign Architect: insight → angle → Reel → carousel → stories → resource → ManyChat → email → offer, with
  each asset's role/objective.
- ManyChat flow spec generator (Markdown + JSON) incl. segmentation questions, consent copy, event hooks;
  Claude in Chrome builds the flow as a draft in ManyChat; you test and publish. Writer role for scripts/captions/carousel copy, always critic-reviewed.
- **Exit**: one full campaign shipped end-to-end with attribution from keyword to email capture (and booking if any).

## Phase 5 — Design system & templated creative (≈2–4 weeks)
- Brand tokens (colors, type, spacing, logo usage), component library, 8–12 HTML templates: carousel
  (cover, list, myth/fact, step, comparison, quote, CTA), story frames, Reel cover, checklist PDF,
  one-page guide PDF, simple infographic.
- Template selector (content structure → template) + renderer (Playwright → PNG/PDF) + visual QA
  (overflow detection, contrast checks).
- **Exit**: you post a system-rendered carousel and PDF with only copy edits, no design fixes.

## Phase 6 — Video intelligence: B-roll library (≈2–3 weeks)
- Drive ingest, shot detection, keyframes, transcription, vision tagging (person, location, activity,
  object, mood, shot type, orientation, quality, subject, use case), semantic search.
- Shot-list generator for approved Reels: required shots, matches from library, **missing shots list**
  (your filming checklist), voiceover script, on-screen text, timing, music brief, cover.
- **Exit**: for an approved Reel, ≥70% of required shots are found in the library with usable matches.

## Phase 7 — Rough-cut pipeline (≈2–4 weeks, optional by ROI)
- Timeline assembly from shot list → OpenTimelineIO export (CapCut/DaVinci/Premiere) and/or Remotion/
  Shotstack render with captions, text overlays, VO track, cover frame.
- **Exit**: editing time per Reel reduced by ≥50% versus today (you measure).

## Phase 8 — Calibration & maturity (ongoing, from ~month 3)
- Quarterly scoring recalibration; critic-vs-human agreement tracking; prompt evals in CI; cost tuning
  (cheaper models for bulk stages only if evals hold); learning decay reviews; taxonomy evolution.

## Dependencies & lead times to start now
| Item | Lead time | Needed by |
|---|---|---|
| Google Trends API alpha | unknown / may not be granted | Phase 3 (CSV fallback) |
| Meta developer app + IG token | 1–3 days | MVP |
| Booking-source capture process decision | your call | Phase 2 |
| ManyChat Pro (API) | immediate if already subscribed | Phase 2 |
| Brand assets (fonts, colors, logos, sample posts you love) | your time | Phase 5 |
| B-roll organized in a Drive folder | your time | Phase 6 |

## What I need from you (consolidated checklist)

**Accounts & credentials**
- [ ] Anthropic API account with billing (or approval to use one you have)
- [ ] Supabase project (or approve me to set one up under your account)
- [ ] Meta developer app access / Instagram Business or Creator account admin — or a Meta Business Suite export of the last 12–24 months
- [ ] Google Cloud project for YouTube Data API key (later: GSC, GA4 service account)
- [ ] ManyChat plan level + API key (Phase 2); list of current keywords/flows
- [ ] Booking system name + export/API access; email platform name + API key
- [ ] Gmail label strategy for inquiries (Phase 2)
- [ ] A separate personal Instagram account for browser market scans

**Data & exports**
- [ ] Instagram content history (if API not ready): captions, dates, metrics
- [ ] Any spreadsheet you keep of posts, keywords, leads, bookings
- [ ] 20–50 anonymized customer inquiries / DMs (MVP Evidence Inbox seed)
- [ ] Your top 10 and bottom 10 posts with your explanation of why
- [ ] List of competitors/creators you watch (IG, YouTube)
- [ ] Forum/YouTube threads you already know are gold (URLs)

**Business knowledge**
- [ ] Offer details: descriptions, prices, margins, capacity, seasonality, which you most want to grow
- [ ] Brand voice notes: words you use/never use, examples of "very us" vs "not us" content
- [ ] Brit's story and Berat's story (perspective, credentials, signature opinions)
- [ ] Weekly production capacity (Reels, carousels, stories you can realistically make)
- [ ] Sensitive-topic stance (safety, politics, religion, scams)

**Creative (Phase 5–6)**
- [ ] Logo files, fonts (with licenses), color palette, any Canva/Figma templates
- [ ] B-roll in a structured Drive folder; music licensing approach
