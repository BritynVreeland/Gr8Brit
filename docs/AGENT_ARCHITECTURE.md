# Agent Architecture — Brit & Berat Content Intelligence OS

Status: **Proposed** · Last updated: 2026-10-06

## 1. Philosophy: a pipeline of narrow roles, not a swarm

"Agents" here means **narrowly-scoped LLM roles** with fixed inputs, a structured output schema,
a versioned prompt, and an eval set. **Python code orchestrates** them in a fixed order. Roles do not
chat with each other or decide what runs next. This gives us:

- **Reliability**: each step's output is schema-validated and stored before the next step runs.
- **Debuggability**: when a recommendation is bad, we can see exactly which step went wrong.
- **Independent improvement**: swap the prompt, the model, or the algorithm of one role without
  touching others (principle #15).
- **Cost control**: bulk steps use the Batch API; judgment-heavy steps use more effort.

Tool-using agent loops are reserved for **interactive work in Claude Code** (exploring data,
answering "why?" questions, drafting a ManyChat spec) — where a human is present.

## 2. Roles

| # | Role | Type | Input | Output | Notes |
|---|---|---|---|---|---|
| 1 | **Collectors** | Code | APIs, Evidence Inbox, webhooks | `raw_documents` | No LLM. One module per source |
| 2 | **Relevance Filter** | LLM (bulk, batch) | raw doc | `{is_relevant, us_likelihood, us_cues, confidence}` | Cheap, high-recall; drops noise early |
| 3 | **Signal Extractor** | LLM (bulk, batch) | relevant raw doc + taxonomy + offers | `evidence_items[]` with verbatim quotes & offsets | Quote verification in code; no tools; UGC wrapped as data |
| 4 | **Embedder + Clusterer** | Code | evidence items | clusters, memberships, snapshots | UMAP+HDBSCAN full re-cluster monthly; nearest-centroid assignment weekly |
| 5 | **Cluster Analyst** | LLM | cluster sample (diverse, up to ~40 quotes) + stats | label, canonical question, summary, sub-themes, misconceptions, taxonomy mapping, merge/split suggestions | Must cite evidence IDs for every claim |
| 6 | **Trend Analyst** | Code (+ LLM narrative) | cluster_snapshots | velocity z-scores, rising/falling flags with `baseline_weeks` | Refuses "rising" claims without ≥8 weeks baseline |
| 7 | **Market Analyst** | LLM + code | market_content matched to clusters | coverage counts, best-answer quality, gaps, oversaturation | "What competitors are missing" |
| 8 | **Performance Analyst** | Code (stats) + LLM narrative | assets + metric snapshots + attribution | per-segment effect sizes with intervals; candidate hypotheses | LLM writes narrative **only from computed numbers**; can't invent stats |
| 9 | **Opportunity Strategist** | LLM (high effort) | top clusters, gaps, learnings, offers, recent content, business priorities | `opportunities[]` incl. resource & offer-messaging opportunities | Must state audience need, why now, B&B advantage, evidence IDs |
| 10 | **Concept Generator** | LLM | opportunities + audience phrase bank + learnings + recent assets | 30–50 `concepts` spanning formats/objectives/angles | Diversity constraints enforced in prompt + code (no >N per cluster) |
| 11 | **Scorer** | Code + LLM rubric | concepts + measured factors | `concept_scores` per dimension with rationale | See SCORING_MODEL.md |
| 12 | **Critic / Creative Director** | LLM (independent, high effort) | each concept + its evidence + last-90-day content + banned patterns + Brit's past rejection reasons | accept / transform / reject + failure modes | Separate prompt and context; never sees the generator's self-assessment |
| 13 | **Fact Checker** | LLM + facts registry | concept/draft claims | claims list → verified / needs-verification / contradicted | Flags anything not in `facts_registry` or expired |
| 14 | **Portfolio Selector** | Code (+ LLM pairwise tie-break) | surviving concepts + scores | ~10 recommendations filling portfolio slots | Diversity + objective mix + capacity |
| 15 | **Resource Evaluator** | LLM | resource opportunities + evidence | format decision (carousel/checklist/PDF/page/map/lead magnet/paid/ManyChat/email) with justification or "not warranted" | Default answer is "content only" unless evidence clears the bar |
| 16 | **Campaign Architect** | LLM | approved opportunity | campaign spine: asset roles, objectives, sequence, ManyChat flow spec, email, offer bridge | Phase 4 |
| 17 | **Writer** (scripts, captions, carousel copy) | LLM | approved concept + phrase bank + brand voice + facts | drafts | Phase 4–5; always reviewed by Critic then human |
| 18 | **Reporter** | LLM + templates | structured results of the cycle | weekly report (HTML/MD) with citations | Writes only from stored objects |
| 19 | **Hypothesis Manager** | Code + LLM | performance analysis, experiments, decisions | hypothesis updates, experiment proposals, learnings with confidence | Monthly |
| 20 | **Video Librarian** | Code + LLM vision | clips → keyframes, transcripts | tags, descriptions, embeddings; shot lists, gap lists | Phase 6 |

## 3. Weekly cycle orchestration

```
bbos cycle weekly
  ├─ collect (per source, idempotent)
  ├─ relevance  ──(Batch API)──▶ filter
  ├─ extract    ──(Batch API)──▶ evidence_items  ──▶ quote verification (code)
  ├─ embed → assign/cluster → snapshots → trends (code)
  ├─ cluster-analyst (new/changed clusters only)
  ├─ market-analyst (clusters with new market content)
  ├─ performance-analyst (assets with new snapshots)
  ├─ strategist → opportunities (≈15–25)
  ├─ concept-generator → 30–50 concepts
  ├─ dedupe vs. history (code: embedding similarity to last 90 days of assets & last 8 weeks of recs)
  ├─ score (code + rubric)
  ├─ critic (+ one transform round max) + fact-checker
  ├─ select portfolio (~10) + resource evaluator
  └─ report → HUMAN REVIEW (decisions captured)
```

Each arrow is a persisted boundary; any stage can be re-run with `--from <stage>`.

## 4. Quality control (the Critic system)

QC is **layered**, cheapest first:

1. **Deterministic checks (code)**
   - Evidence check: concept links to ≥ the gate threshold of evidence (see SCORING_MODEL §2).
   - Banned-phrase linter (`config/banned_phrases.yaml`): "hidden gem(s)", "where East meets West",
     "bucket list", "you won't believe", "ultimate guide", "must-see", "vibrant", "tapestry", "nestled",
     "a feast for the senses", "off the beaten path" (unless evidenced as literal audience wording), etc.
   - Repetition: cosine similarity to the last 90 days of assets and last 8 weeks of recommendations
     above threshold → flagged with the nearest neighbors shown.
   - Objective present; CTA consistent with objective (a reach Reel shouldn't carry a hard sell).
   - Topic saturation: ≤2 recommendations per cluster per cycle.
2. **LLM Critic (independent)** — rubric, each item answered with evidence:
   - *Any-creator test*: "Could virtually any Istanbul creator post this?" If yes → name what would make
     it Brit & Berat-specific (American expectation vs. local reality, Berat's insider access, a real
     guest story) or reject.
   - Is the hook generic/cliché? Rewrite using audience phrase bank wording or reject.
   - Is every claim supported by evidence or a verified fact?
   - Is the strategic purpose clear, and is the format right for it?
   - Is the offer connection natural, plausible, or forced? Forced → remove the offer, keep the content.
   - Is a proposed resource genuinely needed (evidence of the need, answer too big for a caption)?
   - Have we overused this angle/topic recently? Does it contradict an active learning?
   - Sensitive topic handling (safety, politics, earthquakes, scams): factual, non-sensational, useful.
   Output: `accept | transform | reject` + failure modes + specific transformation. One transform
   round max; transformed concepts are re-critiqued, not auto-accepted.
3. **Human review** — Brit/Berat decide with reason codes. Critic prompts include a rolling set of
   recent human rejections and approvals (few-shot), so the critic learns house taste.

**Critic health metric**: agreement rate between critic verdicts and human decisions, tracked per
cycle. If the critic approves things Brit rejects (or vice versa), we tune the rubric — with the
disagreements as the eval set.

## 5. Memory & historical learning

"Memory" is **structured data in Postgres**, not chat history. Six memory types:

| Memory | Contents | Written by | Read by |
|---|---|---|---|
| Evidence memory | raw documents, signals, quotes | collectors, extractor | everything downstream |
| Semantic memory | clusters, taxonomy, audience phrase bank, market coverage | understand/market stages | strategist, generator, reporter |
| Content memory | every asset + metrics time series + attribution | IG sync, manual entry, webhooks | performance analyst, dedupe, critic |
| Decision memory | human approvals/rejections with reasons | review UI/CLI | critic, selector |
| Learning memory | hypotheses, experiments, learnings with confidence & review dates | hypothesis manager | strategist, scorer, generator |
| Brand & business memory | offers, brand voice, banned phrases, facts registry, priorities | humans (versioned config) | all generative roles |

**Context assembly**: each LLM call receives a *curated slice*, assembled by code:
SQL filters (topic, date, objective) + vector retrieval (pgvector) + hard caps. Stable context
(brand voice, taxonomy, offers, rubric) goes first in the prompt and is **prompt-cached**; volatile
data goes last.

**How learning works (and stays honest)**:
1. Performance is normalized: metrics compared at fixed ages (24h/7d/30d), as rates (saves/reach,
   shares/reach, follows per 1k reach, leads per 1k reach), relative to a rolling account baseline,
   within format (Reels vs Reels).
2. Effects are estimated with shrinkage (small groups are pulled toward the overall mean) and reported
   with intervals. Thresholds:
   - **anecdote**: n < 3 per group → never used for decisions, may seed a hypothesis
   - **signal**: 3–9 per group, consistent direction → used as a weak prior
   - **pattern**: ≥10 per group, interval excludes zero → used in scoring
   - **validated**: confirmed by a designed experiment → used with full weight
3. Correlation vs. causation is explicit: observational patterns are "patterns"; only experiments
   produce "validated" learnings.
4. Learnings have `review_by` dates and decay (seasonality, algorithm changes, audience growth).
5. Experiments are **few and deliberate** (1–2 active at a time), matched on format, slot, and length,
   with a primary metric chosen *before* posting.

## 6. Human-in-the-loop gates

| Gate | What's approved | Where |
|---|---|---|
| G1 | Weekly recommendations (approve/reject/modify + reason) | Report + review CLI (MVP) → Streamlit (Phase 2) |
| G2 | Taxonomy additions, new learnings promoted to "pattern"/"validated" | Monthly review |
| G3 | Every public asset (script, caption, creative) | Before posting |
| G4 | Every ManyChat flow and resource | Before deployment in ManyChat |
| G5 | New data sources / scraping methods | Before any collector is built |

## 7. Model usage

- Default model: `claude-opus-5-5` for all roles (per project default), configured per role in
  `config/models.yaml` with effort levels (e.g. `low` for relevance filtering, `high` for strategist and critic).
- Bulk roles (2, 3) run through the **Message Batches API** (50% cost, async — fine for weekly cycles).
- All roles use **structured outputs** validated by Pydantic. Quote verification and evidence-ID
  existence checks run in code after every call.
- Moving bulk roles to cheaper models is a later, measured decision: only after an eval set shows
  equal extraction quality.
- Every call is logged in `llm_calls` (tokens, cost, prompt version) for cost tracking and audits.

## 8. Evals (how we keep LLM roles honest)

- `evals/extraction/`: ~100 hand-labeled raw docs → precision/recall of signal types, quote validity
  (must be 100%), US-likelihood calibration.
- `evals/clustering/`: labeled pairs (same/different need) → cluster purity.
- `evals/critic/`: concepts with Brit's verdicts → agreement rate.
- `evals/opportunities/`: past cycles' top recommendations vs. Brit's approvals and realized results.
Prompt changes must not regress their eval.
