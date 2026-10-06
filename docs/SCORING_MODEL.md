# Scoring Model — Opportunities & Concepts

Status: **Proposed** · Weights live in `config/scoring.yaml` (versioned) · Last updated: 2026-10-06

## 1. Critique of the proposed 17-dimension model

The proposed dimensions (demand, conversation volume, velocity, recency, emotional intensity, search
intent, purchase intent, saveability, shareability, commentability, B&B authority, uniqueness, offer
proximity, resource potential, historical performance, competitive saturation, confidence) are the
right *ingredients* but the wrong *structure*:

1. **Redundant / collinear.** Demand, conversation volume, velocity, and recency all measure "how much
   and how recently people talk about it". Summing them quadruple-counts one thing.
2. **Mixes inputs with predicted outcomes.** Saveability, shareability, and commentability are not
   properties of an *opportunity*; they are predicted outcomes of a specific *execution* (format + hook).
   They belong to concepts, and should eventually be predicted from our own data, not guessed.
3. **False precision.** If an LLM assigns 17 numbers on a 1–10 scale, the total looks rigorous but is
   mostly noise; small prompt changes reshuffle rankings.
4. **One score conflates objectives.** A great reach play (safety myth-bust) and a great lead play
   (airport arrival checklist) shouldn't compete on one number. Strategy needs a *mix*.
5. **Confidence is not a dimension to add.** Weak evidence shouldn't be offset by a high "shareability"
   guess. Confidence should *gate* and *discount*, not be summed.
6. **Some things are rules, not scores.** "Not repetitive", "evidence exists", "not off-brand" are
   pass/fail gates. Averaging them lets bad ideas through on other merits.
7. **Historical performance is sparse early.** It must be shrunk toward a prior until there's data.
8. **Top-N by score ≠ best set.** Ten top-scored ideas may all be about the airport. Selection is a
   portfolio problem.

## 2. Proposed model: Gates → Opportunity Strength → Concept Value → Critique → Portfolio

```
            ┌──────────┐   ┌─────────────────────┐   ┌───────────────────────┐   ┌──────────┐   ┌────────────┐
 signals ──▶│ clusters │──▶│ OPPORTUNITY STRENGTH │──▶│ CONCEPT VALUE (per    │──▶│ GATES +  │──▶│ PORTFOLIO  │──▶ ~10 recs
            └──────────┘   │ (measured, cluster-  │   │ objective) + novelty  │   │ CRITIC + │   │ SELECTION  │
                           │ level, with CI)      │   │ + feasibility         │   │ PAIRWISE │   │ (mix,      │
                           └─────────────────────┘   └───────────────────────┘   └──────────┘   │ diversity) │
                                                                                                 └────────────┘
```

### 2.1 Gates (pass/fail — applied to every concept)

| Gate | Rule (initial; tune with data) |
|---|---|
| **G-Evidence** | ≥5 evidence items from ≥3 independent authors, **or** ≥2 first-party signals (DM, inquiry, tour question, comment on our post), **or** explicit `basis = experiment / business_priority` with written rationale |
| **G-Truth** | All factual claims map to non-expired `facts_registry` entries or are flagged for verification before production |
| **G-Novelty** | Cosine similarity to any asset in last 90 days < 0.85 (or explicitly framed as a sequel/update) |
| **G-Brand** | No banned phrases; passes sensitive-topic rules |
| **G-Purpose** | Declares one primary objective and a CTA consistent with it |
| **G-Distinctive** | Critic's any-creator test passes (after ≤1 transform round) |

### 2.2 Opportunity Strength (cluster/opportunity level — mostly *measured*, not guessed)

Five factors, each 0–1 as **percentiles within our own corpus** (so they're comparable over time):

| Factor | Computation | Replaces |
|---|---|---|
| **D — Demand** | independent authors (not raw mentions) across sources in trailing 12 weeks, source-weighted (first-party ×2), + keyword volume / GSC impressions when available | demand, volume, recency, search intent |
| **M — Momentum** | velocity z-score vs. trailing baseline, shrunk toward 0 when `baseline_weeks < 8`; seasonal comparison (same weeks last year) once a year of data exists | velocity, recency, seasonal |
| **I — Intent & Pain** | share of signals at planning/booked stages, mean purchase intent, mean emotion intensity (fear/confusion weigh more than curiosity for lead objectives) | purchase intent, emotional intensity |
| **G — Gap** | 1 − (competitor coverage × best-answer quality), from market_coverage | competitive saturation, underserved |
| **R — Right to win** | rubric (LLM, 1–5 anchored, evidence required): does the American+local dual perspective, Berat's local access, or our real guest experience make our answer meaningfully better? + offer proximity (natural / plausible / none) | B&B authority, uniqueness, offer proximity |

**Evidence confidence (C)** is computed separately from evidence count, source diversity, first-party
share, extraction confidence, and US-likelihood. It **discounts** and produces an uncertainty band:

```
OpportunityStrength = C_adj × (w_D·D + w_M·M + w_I·I + w_G·G + w_R·R)
C_adj = 0.5 + 0.5·C        # weak evidence halves the score; strong evidence leaves it intact
```
Initial weights (configurable): D 0.30, I 0.25, R 0.20, G 0.15, M 0.10. Momentum starts low because
early baselines are weak; it rises once we have ≥6 months of data.

### 2.3 Concept Value (per concept, **per objective**)

A concept is an execution of an opportunity (format + angle + hook + CTA). It receives an expected
value for **its declared objective only**:

| Objective | Predicted from |
|---|---|
| Reach | opportunity D & M, hook strength (rubric), format prior, historical reach rate of similar assets |
| Trust/Save | I (planning-stage share), practicality (rubric), historical saves/reach of similar assets |
| Engagement | emotion/curiosity, opinion-worthiness (rubric), historical comments/reach |
| Lead | I, resource fit, historical leads per 1k reach of similar keyword CTAs |
| Conversion | offer proximity (natural only), purchase-intent share, historical inquiry rate |
| Experiment | information value: does it test an open hypothesis cleanly? |

**Historical prior with shrinkage**: for "similar assets" (same topic cluster / hook type / format),
predicted rate = `(n·observed_mean + k·account_mean) / (n + k)` with `k ≈ 5`. With no history, the
prediction is the account mean → historical performance can't dominate until it's earned.

Also recorded (not summed): **Novelty** (distance to our past content), **Feasibility** (can we film
it this week? B-roll available? needs Berat on camera?), **Cost/effort** (S/M/L).

LLM rubric items use **1–5 anchored scales** with written anchors and must cite evidence IDs.
Where possible, numbers are computed, not judged.

### 2.4 Critique and pairwise ranking

After gates, the critic runs a **pairwise tournament within each objective slot** ("Which of these two
will better achieve <objective> for Americans planning Istanbul, given the evidence?"). LLMs are far
more consistent at comparisons than at absolute scores. Final within-slot order = blend of concept
value (60%) and pairwise win rate (40%) — tunable.

### 2.5 Portfolio selection (~10 recommendations)

Selection is a constrained optimization (greedy is fine at this size):
- **Objective mix** (default per week, configurable): 3 reach/education · 2 trust/save ·
  2 lead (resource/ManyChat) · 1 conversion/offer · 1 experiment · 1 storytelling/brand.
  Not every piece sells (principle from your brief).
- **Diversity**: ≤2 per cluster, ≤3 per taxonomy branch, ≥3 formats.
- **Capacity**: total effort ≤ weekly production capacity (set by you).
- **Explore/exploit**: ≥1 slot reserved for an experiment or under-tested topic, so we don't only
  repeat what worked.
- **Freshness**: rising (momentum) opportunities get a tie-break.

## 3. Resource opportunity scoring

A resource is recommended only when all hold:
1. **Need evidence**: ≥8 signals (or ≥3 first-party) asking for the same practical help, many phrased as
   "how do I / what should I / is there a list…".
2. **Too big for a caption**: answer requires steps, a checklist, a map, or reference use *during the trip*.
3. **Repeat use**: travelers would reopen it (saved, printed, used on arrival).
4. **Offer adjacency**: natural bridge to an offer (e.g. arrival checklist → airport transfer), or none
   (pure trust builder is acceptable — it's flagged as such).
5. **Format decision tree**:
   - one-time answer → content only / carousel
   - sequence of actions in the moment → checklist (ManyChat-delivered image/PDF)
   - spatial → map (Google My Maps link or designed map)
   - reference with depth, SEO value → webpage
   - high value, high effort, high specificity → paid resource (validate with a free version first)
   - ongoing need → email series
   - capture value → lead magnet only if the evidence shows people *want* it, not because we want emails.

## 4. Calibration (how the model gets smarter)

- Every recommendation stores its sub-scores; every published asset links back.
  `v_recommendation_outcomes` compares predicted vs. realized (at 7d/30d, normalized).
- **Monthly**: report rank correlation between predicted value and outcome per objective.
- **Quarterly (from ~12 weeks of data)**: refit factor weights with a simple regularized regression per
  objective (or Bayesian updating), bounded so no weight moves >±0.1 per quarter. Changes are proposed,
  reviewed by a human, and versioned in `config/scoring.yaml`.
- Human decisions also calibrate: if Brit consistently rejects high-scoring concepts for the same
  reason code, that reason becomes a gate or a rubric item.

## 5. What a recommendation shows

```
#3 · LEAD · "What Americans get wrong at IST arrival (and the 6-step fix)"
Opportunity strength 0.78 (CI 0.66–0.86) · Evidence: 41 signals / 29 authors / 4 sources / 7 first-party
  D 0.84  M 0.40 (baseline 5 wks — low confidence)  I 0.91  G 0.62  R 0.88
Why it exists: …   B&B angle: Brit's first-arrival mistakes + Berat on what locals actually do
Gates: ✔ evidence ✔ truth (3 facts verified 2026-09) ✔ novelty (nearest: 2026-05 reel, sim 0.61) ✔ brand ✔ distinctive
Critic: accepted after transform (removed "ultimate"; hook rebuilt from audience phrase "I landed and had no idea…")
Resource: Checklist PDF via ManyChat keyword ARRIVE → offer bridge: airport transfer (natural)
Evidence: [12 quotes, expandable, linked to source]
```
