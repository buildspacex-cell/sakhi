# Cross-Topic Continuity Reflection — Implementation Plan

> **Status**: Shipped (2026-03-15)
> **Last Updated**: 2026-03-18
> **Scope**: Upgrade deep reflect from single-thread synthesis to cross-thread pattern intelligence

---

## What We're Building

The current deep reflect system is single-threaded. It synthesizes one topic at a time — basketball, work stress, family tension — and produces a longitudinal arc for that thread. What it cannot do is see the person *across* threads.

The upgrade: when multiple threads are active and temporally correlated, Sakhi synthesizes the *interplay* between them. Not "here is your basketball arc" but "your basketball focus peaks in the 2-3 weeks after your work load drops — you've been using the court as a pressure release valve since March."

That second insight is impossible from a single-thread view. It requires seeing two threads running in parallel and detecting what they do to each other.

There is a second, orthogonal layer: **cross-cutting life dimensions**. Time, money, and emotional bandwidth are not pairwise between two threads — they are environmental pressures that color every thread simultaneously. When work is demanding, the time constraint doesn't just affect work; it affects basketball, family, and every other active thread at once. Sakhi surfaces this: "Across your work, basketball, and family threads — time pressure is showing up in all of them right now." It doesn't decide. It shows.

---

## Why This Builds on Existing Infrastructure

Almost everything needed already exists. This is mostly a new service layer and new prompts — not a new infrastructure stack.

| What's needed | What exists | Where |
|---------------|-------------|-------|
| Per-topic moment data with timestamps | `journal_entries.ts` + `continuity_labels.anchor` | DB |
| Topic arcs with phases | Compiled in-memory by `compiler.py` | `services/continuity/compiler.py` |
| Semantic overlap detection | `journal_embeddings.embedding_vec` / `embedding` (1536-dim), lexical fallback | DB |
| Shared facet tracking | `continuity_labels.facets[]` per anchor | DB |
| Stance / direction per moment | `entry_tags.stance`, `decision_state` (compiled output) | `compiler.py` output |
| Previous reflections for delta | `deep_reflections.result_json` | DB |
| Per-turn continuity signal | `build_continuity_pack()` | `turn_v2.py` |
| Reflection job infrastructure | `deep_reflections` table + async job | `reflection.py` |
| Surface policy exclusions | `continuity_surface_policy.exclusions[]` | DB |
| LLM routing layer | `router.chat()` | `reflection.py` |

**Pending items (non-blocking):**
- [ ] Dedicated refresh worker for proactive correlation/life-dimension recompute (current path is lazy read-through cache)
- [ ] Simulation page for inspecting cross-topic packet internals

**Implemented in current pass:**
- Reflection run contract now supports `mode=whole_story|cross_context` plus `topic_keys[]` for linked threads
- `/v2/turn` non-debug continuity signal now passes optional `candidate_topics`, `cross_context`, `whole_story`, `life_dimensions`
- Added cache tables: `continuity_topic_correlations` and `continuity_life_dimensions` (`sakhi/infra/scripts/migrations/0015_continuity_cross_topic.sql`)
- Added `services/continuity/cross_topic.py` as the source-of-truth service for correlation scoring + life-dimension cache reads/writes
- Correlation scoring now uses a 4-signal composite (temporal + semantic + facet + directional) and persists indexed per-pair scores
- Correlation cache hardening now does bounded all-pairs warm compute per request (up to profile cap), profile-driven cache TTL checks, resilient `entry_tags` lookups across key-format drift, and a sorted-window temporal overlap scan
- Semantic overlap now prefers journal embedding cosine centroids (`journal_embeddings`) and automatically falls back to lexical overlap when vectors are unavailable
- Cross-topic thresholds and topic cap are centralized in `thresholds.py` (`CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE`) and consumed by chat/reflection
- Deep reflection now reuses the same cross-topic life-dimensions cache service path used by turn-time continuity signals (single source for surfaced dimensions)
- Related-arc moments are deduplicated before deep packet composition to avoid repeated evidence across linked topics
- Deep reflection prompt composer now supports mode-specific contracts for `topic_reflection`, `deep_answer`, `whole_story`, and `cross_context`
- Continuity compilation now preserves bounded `related_anchors` per moment so one journal entry can be represented in both its primary thread and one linked thread without flattening the overlap away
- Whole-story gating now allows dominant mirror-safe primary threads to unlock linked synthesis, and supporting threads can qualify at 5+ moments when they are meaningfully active
- Chat Deep Reflect (mobile + web converse) now runs `mode=whole_story` only, gated dynamically by `continuity.whole_story` readiness with linked topic keys
- Profile Reflection now includes a separate `Me Story` action that runs `mode=cross_context`, while `<topic> Story` stays `mode=topic_reflection`
- Simulation Ask-Sakhi debug now includes a cross-topic gate panel that shows live go/no-go readiness from `continuity_pack` signals and can run all deep modes for validation
- Emotion mention guardrail is enforced across deep modes: only when explicit priority-conflict evidence is present
- Journal-delete flows now invalidate cross-topic caches immediately (`/memory/dev/reset`, `/lab/cleanup`) so deleted evidence cannot survive until TTL expiry

---

## Core Mental Model

```
Single-topic (current):
  topic_key → compile arc → build packet → LLM prompt (single thread)
            → "Here is your basketball arc"

Cross-context (new — longitudinal, no query, from topic-reflection screen):
  all topics → detect correlations → select top pair → build cross packet
             → LLM prompt (find the relationship) → "Here is how basketball and work interact"

Whole story (new — query-grounded, from chat deep reflect):
  query + correlated topics → compile multi-topic grounding pack
                            → LLM prompt (answer query, use both threads)
                            → "Here's how to set boundaries — your career and family threads both say..."
```

The two new modes are distinct. `cross_context` has no current query — it's purely longitudinal pattern detection. `whole_story` is query-first and uses multiple threads as supporting context.

---

## What Defines a Cross-Topic Relationship

Four correlation types, each grounded in specific existing data:

### 1. Temporal Co-occurrence
**Source:** `journal_entries.ts` JOIN `continuity_labels.anchor`
**Definition:** Moments from topic A and topic B that fall within 7 days of each other
**Score:** `(co-occurring moment pairs) / (min(count_A, count_B))` — normalized 0–1

### 2. Semantic Overlap
**Source:** `journal_embeddings.embedding_vec` / `journal_embeddings.embedding` (existing 1536-dim embeddings)
**Definition:** Cosine similarity between topic centroids built from per-moment journal embeddings for each topic pair
**Score:** normalized cosine `(cos + 1) / 2` when embeddings exist; lexical Jaccard fallback when vectors are unavailable

### 3. Shared Facets
**Source:** `continuity_labels.facets[]` — array of facet labels per journal entry per anchor
**Definition:** Jaccard similarity between facet sets of topic A and topic B across all their moments
**Score:** `|facets_A ∩ facets_B| / |facets_A ∪ facets_B|`

### 4. Directional Correlation
**Source:** `entry_tags.stance` (compiled per moment — values: `toward`, `away`, `neutral`)
**Definition:** Pearson correlation of weekly stance vectors between topic A and topic B over their shared active window
**Score:** `(correlation + 1) / 2` normalized to 0–1; negative correlation (antagonist relationship) is also surfaced

### Combined Score

```python
combined_score = (
    0.45 * temporal_score +
    0.25 * semantic_score +
    0.20 * facet_score +
    0.10 * directional_score
)
```

Temporal co-occurrence remains the strongest signal, but the current implementation uses all four signals in the persisted composite score.

---

## Cross-Cutting Life Dimensions

Pairwise correlations tell you how two threads relate to each other. Life dimensions tell you what *environmental pressure* is bearing down on all threads at once. They are orthogonal: you can have a strong basketball ↔ work correlation AND a high time-pressure dimension that is also squeezing the family and Sakhi-building threads.

The three dimensions:

| Dimension | What it captures | When it surfaces |
|-----------|-----------------|-----------------|
| **Time availability** | Whether the person is stretched too thin across domains simultaneously | Multiple topics with dense recent moments + urgency/deadline signals in `entry_tags` |
| **Financial pressure** | Whether money is a constraint surfacing across decisions in multiple threads | `continuity_labels` financial anchors + `entry_tags` cost/trade-off facets across ≥ 2 topics |
| **Emotional bandwidth** | Whether the person is emotionally depleted or resourced across all threads | `entry_tags.stance` aggregate (skewing `away` = compressed; `toward` = resourced) + `personal_model` energy state |

**The key UX principle:** Sakhi does not decide. It reflects. The output is: *"Across your work, basketball, and family threads — there's a time constraint running through all of them right now."* Then it stops. The user sees the pattern. What to do with it is theirs.

A dimension is surfaced **only when** all three gates pass:
1. Signal level ≥ 0.5 (or ≤ 0.3 for a positive "resourced" signal worth naming)
2. Visible in ≥ 2 distinct topics (it must be cross-cutting, not single-topic)
3. ≥ 4 journal entries carrying the relevant signals in the last 60 days

Financial pressure is held to a higher threshold (level ≥ 0.65) given sensitivity. It is also omitted from `cross_context` synthesis by default unless explicitly included.
Emotional bandwidth is treated as a secondary signal: it is mentioned only when there is explicit priority-conflict evidence (time/money/commitment tradeoff), and even then is capped to one brief sentence.

### New Table

```sql
-- One row per (person, dimension). Recomputed lazily alongside correlation cache.
-- signal_level: 0-1 (0=fully available/resourced, 1=maximally pressured/depleted)
-- signal_direction: 'pressured' | 'neutral' | 'resourced'
-- affected_topics: topic_keys where this dimension is most visible (≥ 2 required to surface)
CREATE TABLE IF NOT EXISTS continuity_life_dimensions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id        UUID NOT NULL,
    dimension        TEXT NOT NULL,         -- 'time_availability' | 'financial_pressure' | 'emotional_bandwidth'
    signal_level     FLOAT NOT NULL,        -- 0-1
    signal_direction TEXT NOT NULL,         -- 'pressured' | 'neutral' | 'resourced'
    affected_topics  TEXT[] DEFAULT '{}',   -- topic_keys where signal is visible
    evidence_summary TEXT,                  -- brief (1 sentence) narrative: what drove the signal
    signal_markers   JSONB DEFAULT '{}',    -- { entry_count, stance_distribution, recency_days, density_score }
    computed_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(person_id, dimension)
);

CREATE INDEX IF NOT EXISTS life_dimensions_person_idx
    ON continuity_life_dimensions(person_id);
```

### Service Contract: `compute_cross_topic_signals()`

Implemented in `services/continuity/cross_topic.py`:

```python
async def compute_cross_topic_signals(
    *,
    person_id: str,
    selected_anchor: str,
    selected_topic: dict[str, Any],
    topics: list[dict[str, Any]],
    window_start: str,
    window_end: str,
    now: datetime,
) -> tuple[cross_context | None, whole_story | None, life_dimensions | None]:
    """
    Read-through cache contract:
      1) Try indexed read from continuity_topic_correlations for all eligible
         topic pairs (bounded by profile sweep cap)
      2) Recompute missing/stale pairs using 4-signal composite score:
         temporal + semantic + facet + directional
      3) Upsert pair cache rows, then project selected-anchor rows for turn payload
      4) Build cross_context + whole_story readiness payloads from selected rows
      5) Read-through life dimensions from continuity_life_dimensions;
         recompute + upsert when stale/missing
    """
```

### Dimension Surfacing in Synthesis

Life dimensions are added as a **context block** at the end of both LLM prompts — after the topic evidence, before the response contract. The model uses them only when directly relevant to the relationship being described.

**For `cross_context` mode:** Append this block after the co-occurring moments:

```
Life dimensions (cross-cutting context — reference only if directly relevant):
  Time availability: {time_direction} ({time_level:.0%}) — showing in: {time_affected_topics}
  Emotional bandwidth: {emotional_direction} ({emotional_level:.0%}) — showing in: {emotional_affected_topics}
  [Financial pressure: only include this line if financial_pressure.surface=True]

If either of these environmental pressures is visible in the relationship you're describing,
name it once — briefly and specifically. Do not advise on it. Do not over-weight it.
Example: "And across both threads, time is running thin — that's the water both threads are swimming in."
If these dimensions are not directly relevant to the thread relationship, omit them entirely.
Never lead with emotion. Mention emotional bandwidth only when priority conflict is explicitly evidenced by the packet.
```

**For `whole_story` mode:** Append the same block after the "How these threads connect" section, with identical instructions.

**Dimension omit rule:** If a dimension is not `surface=True` in the computed output, it is never included in the prompt. The prompt never asks the model to infer a dimension the data doesn't support.

---

## Implementation Phases

| Phase | What | Goal |
|-------|------|------|
| **0** | Schema + correlation service | Core detection logic, grounded in real tables |
| **1** | Simulation page | Harden API and prompts before mobile touches them |
| **2** | New synthesis modes in reflection API | `cross_context` and `whole_story` |
| **3** | Per-turn signal extension | Surface readiness signals alongside topic signal |
| **4** | Mobile UX | "Full Picture" in chat + topic-reflection |

---

## Phase 0: Schema + Correlation Service

### New Table

```sql
-- Cache cross-topic correlation data per person.
-- Recomputed lazily when new moments arrive for either topic in a pair.
-- topic_key_a < topic_key_b (alphabetical) to avoid duplicate pairs.
-- combined_score is the weighted composite of all correlation types.
CREATE TABLE IF NOT EXISTS continuity_topic_correlations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id           TEXT NOT NULL,
    topic_key_a         TEXT NOT NULL,   -- alphabetically first
    topic_key_b         TEXT NOT NULL,   -- alphabetically second
    combined_score      FLOAT NOT NULL,  -- 0-1 weighted composite
    temporal_score      FLOAT DEFAULT 0, -- co-occurrence within 7 days (journal_entries.ts)
    semantic_score      FLOAT DEFAULT 0, -- memory_episodic.vector_vec overlap
    facet_score         FLOAT DEFAULT 0, -- continuity_labels.facets[] Jaccard
    directional_score   FLOAT DEFAULT 0, -- entry_tags.stance Pearson correlation
    correlation_types   TEXT[] NOT NULL, -- dominant types above 0.3 threshold
    shared_facets       TEXT[] DEFAULT '{}',
    overlap_windows     JSONB DEFAULT '[]', -- [{ start, end, moment_count_a, moment_count_b }]
    peak_overlap_period JSONB,              -- { start, end } — densest window
    moment_count_a      INTEGER DEFAULT 0,
    moment_count_b      INTEGER DEFAULT 0,
    computed_at         TIMESTAMPTZ DEFAULT now(),
    UNIQUE(person_id, topic_key_a, topic_key_b)
);

CREATE INDEX IF NOT EXISTS topic_correlations_person_score_idx
    ON continuity_topic_correlations(person_id, combined_score DESC);
```

**No new topic table.** Topics do not get a persistent table — they are compiled in-memory by `compiler.py` from `journal_entries` + `continuity_labels`. The correlation table caches pairwise scores only. Topic data for synthesis is always fetched fresh from the compiler.

### New Service: `services/continuity/cross_topic.py`

```python
async def compute_all_cross_topic_data(
    person_id: str,
    compiled_topics: list[dict],  # output of compiler.py — all person's topics
    force_recompute: bool = False,
) -> dict:
    """
    Convenience wrapper: runs compute_topic_correlations and compute_life_dimensions
    in parallel and returns { correlations: [...], life_dimensions: {...} }.
    Called once per turn when cross-topic data needs refresh.
    """

async def compute_topic_correlations(
    person_id: str,
    compiled_topics: list[dict],  # output of compiler.py — all person's topics
    force_recompute: bool = False,
) -> list[dict]:
    """
    For each pair of topics where the primary thread is either detail-safe or
    dominant+mirror-safe, and the supporting thread has >= 5 meaningful moments:
      1. temporal_score: count co-occurring moment pairs (journal_entries.ts within 7 days)
         Source: journal_entries JOIN continuity_labels WHERE anchor IN (key_a, key_b)
      2. semantic_score: memory_episodic records matching both topic keyword sets
         Source: memory_episodic.vector_vec cosine sim to each topic's taxonomy keywords
      3. facet_score: Jaccard(continuity_labels.facets[] for key_a, facets[] for key_b)
         Source: continuity_labels WHERE anchor IN (key_a, key_b)
      4. directional_score: Pearson(weekly stance vectors for key_a, key_b)
         Source: entry_tags.stance from compiled output
      5. combined_score weighted sum
      6. Upsert into continuity_topic_correlations
    Returns pairs sorted by combined_score DESC.
    """

async def get_top_correlations(
    person_id: str,
    min_score: float = 0.35,
    limit: int = 3,
) -> list[dict]:
    """Single indexed read from continuity_topic_correlations cache."""

async def build_cross_context_packet(
    person_id: str,
    topic_key_a: str,
    topic_key_b: str,
    compiled_topics: list[dict],
    correlation: dict,
) -> dict:
    """
    Builds the LLM input packet for cross_context mode (no current query).
    Returns:
    {
      synthesis_mode: "cross_context",
      topic_a: { key, label, arc_compact, evidence_anchors, phase_count, direction },
      topic_b: { key, label, arc_compact, evidence_anchors, phase_count, direction },
      correlation: {
        combined_score,
        correlation_types,
        shared_facets,
        overlap_windows,
        peak_overlap_period,
        co_occurring_moments: [
          { ts_a, excerpt_a, facet_a, stance_a, ts_b, excerpt_b, facet_b, stance_b, days_apart }
        ]
      },
      state_hints: { emotion_hint, load_hint, energy_hint, identity_phase },
      response_contract: { ... }
    }
    """

async def build_whole_story_packet(
    person_id: str,
    primary_topic_key: str,
    related_topic_keys: list[str],
    compiled_topics: list[dict],
    correlations: list[dict],
    user_query: str,
) -> dict:
    """
    Builds the LLM input packet for whole_story mode (query-grounded).
    Primary topic is the query-matched topic. Related topics provide grounding.
    Returns packet with:
      current_query, primary_topic arc, related_topic arcs, bridge_insights,
      co_occurring_moments, response_contract (current_query_first)
    """

def is_cross_context_ready(
    topic_a: dict,
    topic_b: dict,
    correlation: dict,
) -> tuple[bool, str]:
    """
    Gates — aligned with thresholds.py conventions:
    - Primary topic: detail_allowed=True with >= 6 moments, OR mirror_allowed=True with >= 8 moments and dominant depth vs the next thread
    - Supporting topic: >= 5 moments and at least mirror_allowed=True
    - combined_score >= 0.35
    - At least one topic has a moment in the last 90 days
    Returns (ready, reason):
      reason: "ready" | "insufficient_overlap" | "insufficient_depth" | "threads_inactive"
    """

def is_whole_story_ready(
    primary_topic: dict,
    related_topics: list[dict],
    correlations: list[dict],
) -> tuple[bool, str]:
    """
    Gates for query-grounded whole story:
    - primary_topic: selected_count >= 8 AND either detail_allowed=True OR dominant+mirror_allowed=True
    - At least 1 related topic: selected_count >= 5 and meaningfully active (detail-safe or mirror-safe support thread)
    - At least 1 correlation with combined_score >= 0.35
    - combined topic count <= 3 (token budget)
    Returns (ready, reason)
    """
```

### Threshold Alignment

New thresholds belong in `thresholds.py` alongside existing ones:

```python
# thresholds.py additions
cross_context_min_moments_per_topic: int = 6     # vs 8 for single-topic
cross_context_min_combined_score: float = 0.35
cross_context_recent_activity_days: int = 90
whole_story_min_related_moments: int = 5
whole_story_primary_dominance_ratio: float = 1.5
whole_story_max_topics: int = 3
whole_story_min_link_score: float = 0.35
```

### Surface Policy Exclusions Apply

Before computing correlations and before building any cross-topic packet, check `continuity_surface_policy.exclusions[]` for the person. Any topic in the exclusions list is ineligible as either member of a pair. This applies identically to both `cross_context` and `whole_story` modes.

```python
# In compute_topic_correlations():
excluded = await get_excluded_topics(person_id)  # from continuity_surface_policy
eligible_topics = [t for t in compiled_topics if t["anchor"] not in excluded]
# Only pair from eligible_topics
```

---

## Phase 1: Simulation Page

### Goal

Harden the correlation detection and both LLM prompts before mobile touches them. The LLM prompt quality is the highest-risk part — the model wants to summarize two threads side-by-side rather than find the relationship. This needs to be caught and iterated in simulation, not in production.

### What the Simulation Demonstrates

Four panels:

**Panel 0 — Life Dimensions:** The three cross-cutting signals computed globally across all threads. Each dimension shown as a labeled bar (level 0–1), direction badge, and list of affected topic_keys. Makes the orthogonal layer visible before looking at any pairwise correlation.

**Panel 1 — Thread Map:** Vidhya's threads as nodes, correlation pairs as weighted edges. Shows correlation type breakdown per pair.

**Panel 2 — Temporal Alignment:** Timeline view of two selected threads showing moment density per week, with overlap windows highlighted.

**Panel 3 — Synthesis Comparison:** Single-topic output vs. cross-context output for the same threads side-by-side. Makes the gap visible. Dimension context shown as a callout when relevant.

```
┌────────────────────────────────────────────────────────────────────────────┐
│  CROSS-TOPIC REFLECTION — SIMULATION                                        │
│  "What one thread can't see, two threads together can."                    │
├────────────────────────────────────────────────────────────────────────────┤
│  LIFE DIMENSIONS (cross-cutting — not pairwise)                             │
│  ─────────────────────────────────────────────                              │
│  Time availability    PRESSURED  0.72  ████████░░   work, basketball, family│
│  Emotional bandwidth  PRESSURED  0.58  ██████░░░░   work, family            │
│  Financial pressure   NEUTRAL    0.31  ███░░░░░░░   (below threshold)       │
│                                                                              │
│  "Time is the water all three threads are swimming in right now."           │
│  [▶ Recompute Dimensions]                                                   │
├──────────────────────────────────┬─────────────────────────────────────────┤
│  THREAD MAP                      │  SELECTED PAIR: Basketball ←→ Work      │
│  ─────────────────────────────   │  ──────────────────────────────────     │
│                                  │                                          │
│  ● Basketball    12m             │  CORRELATION BREAKDOWN                   │
│    ──── Work     0.74 temporal   │  Temporal:    0.81  ████████░░           │
│    ──── Sleep    0.41 direction  │  Semantic:    0.52  █████░░░░░           │
│                                  │  Facets:      0.38  ████░░░░░░           │
│  ● Work          9m              │  Direction:   0.29  ███░░░░░░░           │
│    ──── Family   0.51 semantic   │  Combined:    0.74  ███████░░░           │
│                                  │                                          │
│  ● Family        7m              │  TEMPORAL ALIGNMENT (weekly moments)     │
│  ● Sleep         6m              │  ┌────────────────────────────────────┐  │
│                                  │  │ Jun ████░░░ Basketball             │  │
│  [▶ Run Correlations]            │  │     ░░░████ Work                   │  │
│                                  │  │ Jul ████░░░ Basketball             │  │
│  Shared facets: stress, decision │  │     ░░░░███ Work                   │  │
│  Peak overlap: Jun–Aug 2025      │  │ ← inverse pattern: 0.74 corr.     │  │
│  Co-occurring moments: 8         │  └────────────────────────────────────┘  │
│                                  │                                          │
│                                  │  [▶ Run Cross-Context Synthesis]         │
├──────────────────────────────────┴─────────────────────────────────────────┤
│  SYNTHESIS COMPARISON (appears after synthesis runs)                        │
│  ─────────────────────────────────────────────────────────────────────────  │
│  SINGLE-TOPIC (Basketball)          CROSS-CONTEXT (Basketball + Work)       │
│  ─────────────────────────────      ───────────────────────────────────     │
│  "Basketball has been a steady       "Your court time and your work         │
│   thread since March. You moved      deadlines have been running in          │
│   from learning phase into           opposite cycles since March. The        │
│   performance. There's a pattern     weeks you ship something big are        │
│   of intense practice followed       the weeks practice drops. And the       │
│   by stepping back..."               weeks work goes quiet, you're back      │
│                                      hard on the court. You've been          │
│  [Grounded in 1 thread]              using basketball as a reset valve       │
│                                      without naming it that way..."           │
│                                                                               │
│                                      [Grounded in 2 threads + 8 overlaps]   │
└───────────────────────────────────────────────────────────────────────────────┘
```

### New Web Proxy Routes

```
apps/web/app/api/continuity-cross-topic/
├── correlations/route.ts    GET  → /v1/continuity/cross-topic/correlations
├── dimensions/route.ts      GET  → /v1/continuity/cross-topic/dimensions
├── packet/route.ts          POST → /v1/continuity/cross-topic/packet
└── synthesize/route.ts      POST → /continuity/reflection/run (mode=cross_context)
```

---

## Phase 2: New Synthesis Modes in Reflection API

### API Extension

```python
POST /continuity/reflection/run
# Extended request — new fields shown with comments:
{
  "person_id": str,           # dev/sim use — prod binds to auth principal
  "topic_key": str,           # primary topic (required for all modes)
  "topic_keys": list[str],    # NEW — additional topics for whole_story mode
                              # MUST be from server-validated candidate_topics only
                              # server re-validates each key is in compiled topics
                              # with detail_allowed=True; rejects unknown keys
  "window": str,              # default "3650d"
  "mode": str,                # "topic_reflection" | "deep_answer" | "cross_context" | "whole_story"
  "scope": str,               # DEPRECATED — use mode directly; kept for backward compat
  "user_query": str,          # required for deep_answer and whole_story, null otherwise
}
```

**`topic_keys` validation:** The server re-validates every key in `topic_keys` against the current compiled topics for that person. Any key that is not in the compiled topic set, is excluded by surface policy, or has `detail_allowed=False` is rejected with 400. Client may only request keys from `candidate_topics` returned in the turn signal.

### New Mode: `cross_context`

Longitudinal, no current query. Triggered from the topic-reflection screen ("Full Picture" button). Finds what two threads reveal together over time.

**Result JSON shape:**
```python
{
  "reflection_mode": "cross_context",
  "topic_key_a": str,
  "topic_key_b": str,
  "topic_label_a": str,
  "topic_label_b": str,
  "relationship_summary": str,     # deterministic: e.g. "temporal inverse correlation since Jun 2025"
  "relationship_type": str,        # dominant correlation type
  "correlation_score": float,
  "bridge_insights": [             # deterministic structured output
    {
      "type": "spillover" | "reinforces" | "conflict" | "shared_goal",
      "summary": str,
      "confidence": float,
      "evidence_refs": list[str],  # "journal:{uuid}" strings from co-occurring moments
    }
  ],
  "chat_response": str,            # LLM output
  "deterministic_chat_response": str,  # fallback if LLM fails
  "chat_response_source": "llm" | "deterministic",
  "llm_reflection": { ... },       # same metadata shape as existing
}
```

**LLM Prompt — `cross_context`:**

```
System:
  You are Sakhi — a friend who sees the whole person, not just one part of their life.
  You are given two threads from this person's life and the moments where they overlap.
  Your job is to name the RELATIONSHIP between these threads — what one does to the other,
  or what they reveal together that neither reveals alone.

  Critical rules:
  - Do NOT summarize each thread separately. Find the relationship, not the summaries.
  - Every specific claim must map to a co-occurring moment in the evidence provided.
  - Do not introduce themes, causes, or patterns not explicitly in the evidence.
  - Speak like a perceptive friend, not a therapist. Be direct and specific.

User:
  Thread 1 — {topic_label_a}:
  - Where it began: {origin_story_a}
  - Where it is now: {current_stage_a}
  - Direction: {direction_a}
  - Recurring pattern: {recurring_tension_a}

  Thread 2 — {topic_label_b}:
  - Where it began: {origin_story_b}
  - Where it is now: {current_stage_b}
  - Direction: {direction_b}
  - Recurring pattern: {recurring_tension_b}

  How these threads overlap:
  - Co-occurred {N} times within 7 days of each other
  - Peak overlap period: {peak_overlap_period}
  - Shared facets: {shared_facets}
  - Correlation type: {correlation_types}

  Closest co-occurring moments (most temporally proximate pairs):
  {for each of top 5 co-occurring moment pairs:}
  - {ts_a}: "{excerpt_a}" ({facet_a}, {stance_a})
    {days_apart}d later: "{excerpt_b}" ({facet_b}, {stance_b})

  What is the relationship between these two threads?
  How does one affect the other? What do they reveal together?

  Response contract:
  - Voice: friend, warm, direct — not a therapist, not a coach
  - Length: 200-300 words
  - Format: natural prose — name the relationship in the FIRST sentence,
            then trace it through the evidence, end with ONE honest question
  - The first sentence must name the relationship explicitly
    (e.g. "Your basketball practice and your work deadlines have been running
    in opposite cycles since March.")
  - Do NOT start by summarizing Thread 1, then Thread 2 separately
  - Avoid: therapy-speak, generic motivation, unsupported causal claims
  - Max questions: 1

  Return plain text only.
```

**Deterministic fallback (LLM failure):**
```
"{topic_label_a} and {topic_label_b} have been active in overlapping periods since {peak_overlap_period.start}.
They share these recurring patterns: {shared_facets_joined}.
The {correlation_types[0]} connection between them has shown up {co_occurring_moment_count} times.
What would it mean to look at both threads at once?"
```

---

### New Mode: `whole_story`

Query-grounded, multi-topic. Triggered from the deep reflect row in chat when multiple correlated threads are active. Answers the current user query, using both thread histories as supporting context.

**LLM Prompt — `whole_story`:**

```
System:
  You are Sakhi — a friend who knows this person's history deeply.
  You are answering a specific question they just asked.
  You have context from MULTIPLE threads in their life that are relevant.

  Critical rules:
  - Answer the current question FIRST. History serves the answer, not the other way around.
  - Use multiple thread histories only where they add precision or reveal tradeoffs.
  - Do not summarize topic arcs. Extract only the parts relevant to the question.
  - Every historical reference must come from the evidence provided.
  - Do not introduce patterns not present in the packet.

User:
  Their question: "{user_query}"

  Primary thread — {primary_topic_label}:
  - Where it is now: {current_stage}
  - Recurring pattern: {recurring_tension}
  - Recent evidence: {evidence_anchors top 3}

  Related thread — {related_topic_label}:
  - Where it is now: {related_current_stage}
  - Recurring pattern: {related_recurring_tension}
  - Connection to primary: {bridge_insights[0].summary}
  - Shared moments (within 7 days of primary moments):
    {top 3 co-occurring pairs}

  How these threads connect:
  - {bridge_insights type and summary}
  - Shared facets: {shared_facets}

  Current state: emotion={emotion_hint}, load={load_hint}, energy={energy_hint}

  Response contract:
  - Voice: friend, warm, direct
  - Length: 150-250 words
  - Format: answer the question directly in the FIRST 1-2 sentences,
            then use the thread history to add depth and precision,
            end with one practical suggestion and one honest question
  - Priority: current answer > historical grounding
  - Avoid: leading with history, therapy-speak, generic motivation
  - Max questions: 1

  Return plain text only.
```

---

## Phase 3: Per-Turn Signal Extension

### Extended Signal Shape

The per-turn signal is extended to include two new optional fields. Both are `null` when not applicable. Backward compatible — existing clients ignore unknown fields.

```python
{
  # Existing fields — unchanged:
  "topic_key": "basketball",
  "topic_label": "Basketball",
  "deep_reflect": {
    "ready": bool,
    "reason": str,
    "mirror_allowed": bool,
    "detail_allowed": bool,
    "selected_count": int,
    "min_moments": int
  },

  # NEW — top 2-3 candidate topics ranked by query relevance + quality:
  # Only populated when there are multiple eligible topics
  # Capped at 3 to control payload weight
  "candidate_topics": [
    {
      "topic_key": str,
      "topic_label": str,
      "score": float,            # 0.45*query_sim + 0.20*recency + 0.20*depth + 0.15*confidence
      "selected_count": int,
      "detail_allowed": bool
    },
    ...                          # max 3 items
  ] | null,

  # NEW — cross-context readiness for the active topic + its top correlated pair:
  # Only present when a correlated pair exists with combined_score >= 0.35
  "cross_context": {
    "correlated_topic_key": str,
    "correlated_topic_label": str,
    "ready": bool,
    "reason": "ready" | "insufficient_overlap" | "insufficient_depth" | "threads_inactive",
    "correlation_score": float,
    "correlation_type": str      # dominant type: "temporal" | "semantic" | "facet"
  } | null,

  # NEW — whole_story readiness (multi-topic, query-grounded):
  # Only present when active topic has a ready correlated pair
  "whole_story": {
    "ready": bool,
    "reason": str,
    "selected_topics": list[str],  # topic_keys server has pre-selected
    "selected_count_total": int,
    "correlation_score": float
  } | null,

  # NEW — cross-cutting life dimension signals (null when insufficient data)
  # Each dimension only present when surface=True (gates: level threshold + ≥2 topics + ≥4 entries)
  # Never contains financial_pressure unless level >= 0.65
  "life_dimensions": {
    "time_availability": {
      "level": float,              # 0-1 (0=available, 1=fully pressured)
      "direction": "pressured" | "neutral" | "resourced",
      "affected_topics": list[str] # topic_keys where signal is visible
    } | null,
    "financial_pressure": {
      "level": float,
      "direction": "pressured" | "neutral" | "resourced",
      "affected_topics": list[str]
    } | null,
    "emotional_bandwidth": {
      "level": float,
      "direction": "pressured" | "neutral" | "resourced",
      "affected_topics": list[str]
    } | null
  } | null                         # outer null when no dimensions meet surfacing threshold
}
```

### Performance Note

`candidate_topics`, `cross_context`, `whole_story`, and `life_dimensions` are all derived from:
1. `get_top_correlations()` — one indexed read from the `continuity_topic_correlations` cache
2. `get_life_dimensions()` — one indexed read from the `continuity_life_dimensions` cache
3. Compiled topics already in-memory from `build_continuity_pack()`

No additional DB queries per turn. Both caches are recomputed lazily when new moments arrive, not per turn. Both reads happen in parallel.

### `candidate_topics` Payload Weight

`candidate_topics` is only populated when the person has ≥ 2 topics with `detail_allowed=True`. For new users with sparse data, it is null. Cap at 3 items.

---

## Phase 4: Mobile UX

### Chat — `converse/index.tsx`

**Current Deep Reflect row:**
```
[ info pill: "Ready for [thread]" ]  [ Run Deep ]
```

**When `whole_story.ready` is also true:**
```
[ info pill: "Ready for [thread A] + [thread B]" ]  [ Run Deep ]
```

`Run Deep` always triggers the same `mode: "whole_story"` reflection flow. When linked context is available it sends `topic_keys: [primary, related]`; otherwise it sends `topic_keys: [primary]` and runs a single-thread deep reflection.

When `whole_story.ready` is false, the button can still appear if `deep_reflect.ready` is true. In that case the run stays single-thread and skips linked-context weaving.

### Topic-Reflection — `soul/topic-reflection.tsx`

**Correlation lines in Life Occupancy bubble cloud:**
When two bubbles have `combined_score >= 0.5`, a faint connecting line is drawn between them. Line opacity scales with score. Tapping the line surface shows: correlation type, score, and peak overlap period.

**Sub-thread creation rule for Life Occupancy:**
Not every detail should become its own bubble. A sub-thread should earn a visible bubble only when it behaves like a distinct, recurring life arena rather than a one-off detail inside a parent thread.

Create a visible sub-thread only when all are true:
- it is specific enough to stand on its own
- it recurs across multiple moments over time
- it carries distinct emotional, logistical, or identity weight
- it is independently interpretable outside the parent thread

Three product stages:
- `mention`
  - isolated detail, remains inside parent thread
- `candidate_sub_thread`
  - repeated motif, tracked internally but not surfaced yet
- `visible_sub_thread`
  - repeated, consequential, and stable enough to earn its own bubble

Recommended visible threshold:
- at least `3-5` distinct moments
- spread across at least `2` different days or sessions
- plus at least one recurring stake:
  - planning / logistics
  - emotional charge
  - identity signal
  - tradeoff with another thread

Example:
- `family` remains the parent thread
- `daughter_basketball` becomes a visible sub-thread only after it repeatedly shows up as its own pressure, schedule, pride, conflict, or commitment pattern

**"Full Picture" button in thread modal:**
Below the existing `[ ✦ Basketball Story ]` button:
```
[ ✦ Basketball Story   ]    ← existing, unchanged
[ ◈ Full Picture       ]    ← new: cross_context mode
  "connects Basketball + Work"
```

`Full Picture` is only shown when `cross_context.ready` for this thread's pair. Tapping it runs `mode=cross_context`. Result displays in the same modal with two thread label pills at the top instead of one, and distinct warm-gold treatment.

---

## Bridge Data Invalidation

When a journal entry is deleted or a topic is explicitly excluded from the surface policy, any cached `continuity_topic_correlations` rows that reference that topic must be invalidated:

```python
# On journal entry delete or surface policy exclusion update:
await invalidate_correlations_for_topic(person_id, affected_topic_key)
# → DELETE FROM continuity_topic_correlations
#   WHERE person_id = $1 AND (topic_key_a = $2 OR topic_key_b = $2)
```

Correlations will be recomputed on next synthesis request or turn for that person.

---

## Data Flow: End to End

```
1. User sends message
   → turn_v2.py compiles all topics for person
   → build_continuity_pack() identifies active topic (basketball)
   → get_top_correlations() reads from continuity_topic_correlations cache (1 indexed read)
   → if active topic is in a top pair:
       cross_context and whole_story signals computed and added to response
   → signal emitted with candidate_topics, cross_context, whole_story

2. Mobile receives signal
   → activeContinuitySignal updated
   → cross_context.ready → "Full Picture" button activates in topic-reflection
   → whole_story.ready → linked-context version of "Run Deep" becomes available in chat row

3a. User taps "Full Picture" (from topic-reflection)
    → POST /continuity/reflection/run { mode: "cross_context", topic_key, topic_key_b }
    → build_cross_context_packet() → LLM → result stored
    → "Full Picture" bubble in topic-reflection modal

3b. User taps "Run Deep" with linked context available
    → POST /continuity/reflection/run { mode: "whole_story", topic_key, topic_keys, user_query }
    → server validates topic_keys against compiled candidates (reject unknown keys)
    → build_whole_story_packet() → LLM → result stored
    → Gold "Whole Story" bubble in chat

4. Both poll GET /continuity/reflection/status → result → display
```

---

## New Files Summary

```
New Python:
sakhi/apps/api/
├── routes/continuity_cross_topic.py          # GET correlations, POST packet
└── services/continuity/
    └── cross_topic.py                        # Correlation detection + packet builders

Modified Python:
sakhi/apps/api/
├── routes/turn_v2.py                         # Phase 3: add candidate_topics, cross_context, whole_story
└── services/continuity/
    └── reflection.py                         # Phase 2: add cross_context and whole_story mode branches

New migration:
sakhi/infra/scripts/migrations/
└── 0XXX_continuity_cross_topic.sql   # adds both continuity_topic_correlations and continuity_life_dimensions

New web simulation:
apps/web/app/
├── demo/cross-topic-simulation/
│   ├── page.tsx
│   ├── scenarioConfigs.ts
│   └── components/
│       ├── LifeDimensions.tsx                # three dimension bars + affected topics
│       ├── ThreadMap.tsx                     # bubble nodes + weighted edges
│       ├── CorrelationBreakdown.tsx          # per-type score bars
│       ├── TemporalAlignment.tsx             # weekly moment density timeline
│       └── SynthesisComparison.tsx           # single-topic vs cross-context side-by-side
└── api/continuity-cross-topic/
    ├── correlations/route.ts
    ├── packet/route.ts
    └── synthesize/route.ts

Mobile changes:
apps/mobile/app/
├── experience/converse/index.tsx             # Run Deep row with optional linked-context state
└── soul/topic-reflection.tsx                 # Correlation lines + "Full Picture" in thread modal
```

---

## What Doesn't Change

- Existing `topic_reflection` and `deep_answer` modes are **unchanged**
- The compilation pipeline (`compiler.py`, `taxonomy.py`, `thresholds.py`) is **untouched**
- The `deep_reflections` table stores all modes in `result_json` — no schema change to existing tables
- The `continuity_surface_policy` exclusion system is honoured identically for cross-topic

---

## Definition of Done — Phase 1 (Simulation)

**Correlation detection:**
- [ ] Top 3 thread pairs computed and displayed for Vidhya from real journal data
- [ ] Each pair shows per-type score breakdown (temporal / semantic / facet / directional)
- [ ] Co-occurring moments correctly identified using `journal_entries.ts` within 7-day window
- [ ] Temporal alignment visualization shows correct weekly moment density for both threads
- [ ] Excluded topics (from `continuity_surface_policy`) do not appear in any pair

**Synthesis — cross_context:**
- [ ] Synthesis runs and returns `chat_response` grounded in co-occurring evidence
- [ ] Side-by-side comparison: single-topic vs. cross-context clearly shows the difference
- [ ] LLM output names the relationship in the first sentence (not two separate thread summaries)
- [ ] Deterministic fallback fires when LLM fails and produces valid output
- [ ] `bridge_insights` populated with correct `evidence_refs` (journal UUIDs)

**Synthesis — whole_story:**
- [ ] Query-grounded synthesis answers the question first, uses threads as supporting context
- [ ] `topic_keys` validation rejects keys not in compiled topics (returns 400, not 500)

**Life dimensions:**
- [ ] All three dimensions computed from real Vidhya data and displayed in Panel 0
- [ ] Dimensions with `surface=False` (below threshold or < 2 affected topics) show as "below threshold" — not surfaced in synthesis
- [ ] Time-pressure dimension visible in synthesis output when level >= 0.5 across ≥ 2 topics
- [ ] Dimension context in LLM output is brief (1 sentence) and not dominant — thread relationship is still the main narrative
- [ ] Financial pressure omitted from synthesis unless level >= 0.65

**Resilience:**
- [ ] `insufficient_overlap` returned when `combined_score < 0.35`
- [ ] `insufficient_depth` returned when either topic has < 6 moments
- [ ] `threads_inactive` returned when no moment in last 90 days for either topic

---

## Definition of Done — Phase 4 (Mobile)

- [ ] "Run Deep" appears when `deep_reflect.ready`; linked-context copy upgrades when `whole_story.ready`
- [ ] "Whole Story" bubble renders with distinct treatment and can run with one or more selected topic pills
- [ ] Topic-reflection screen shows correlation lines between bubbles with `combined_score >= 0.5`
- [ ] "Full Picture" button appears in thread modal only when `cross_context.ready` for that thread
- [ ] "Full Picture" result clearly names the relationship (not two thread summaries)
- [ ] `topic_keys` never accepted from client without server-side re-validation
- [ ] `life_dimensions` in per-turn signal correctly null when no dimension clears surfacing threshold
- [ ] Life dimension context in cross-context synthesis is present when relevant, absent when not — model does not over-weight it

---

## Risks and Guardrails

| Risk | Guardrail |
|------|-----------|
| LLM summarizes threads side-by-side instead of finding relationship | Explicit "do NOT summarize each thread separately" in system prompt + simulation testing |
| Low-quality correlations surface prematurely | `combined_score >= 0.35` gate; "Full Picture" absent (not dimmed) when not ready |
| Token inflation from multi-topic packets | Max 3 topics; compact arc format; top 5 co-occurring moments only |
| Hallucinated connections between unrelated threads | Every claim must map to `evidence_refs` from co-occurring moments |
| Excluded topics appearing in cross-context | Surface policy exclusions checked before correlation computation |
| Stale correlations after entry deletion | Invalidate cache rows for affected topic on deletion |
| Life dimension dominates synthesis — model over-explains time/emotion pressure | Dimension block is after evidence, instruction says "omit if not directly relevant"; simulation validates model follows it |
| Financial dimension surfaces sensitive data | Higher threshold (0.65), omitted from synthesis by default, explicit `surface=True` flag |
| Dimension computed from sparse data — false signal | ≥ 4 journal entries required in 60-day window; below threshold → `surface=False` → never in prompt |
| Emotional framing overused in tactical questions | Emotion is secondary-only; mention only when priority-conflict evidence is present, max one sentence |

---

## Notes

- **Temporal correlation is the MVP.** Implement temporal score only in Phase 0. Semantic and facet scores add accuracy but require more compute. Ship temporal-only, iterate from there.
- **The prompt is the product.** The quality of cross-context synthesis depends almost entirely on the LLM prompt. The simulation page exists specifically to iterate on this before users see it.
- **This feature improves with usage.** Users need 3+ months of journaling across 2+ threads before cross-topic patterns are meaningful. The feature is simply absent for new users — not degraded.
- **`cross_context` and `whole_story` are different products.** `cross_context` is reflective and longitudinal (no current query). `whole_story` is practical and query-grounded. Don't conflate them in the UX.
- **Cap payload growth.** `candidate_topics` is capped at 3. `cross_context` is one pair only. `whole_story.selected_topics` is max 3 keys. `life_dimensions` is fixed at 3 keys regardless of data volume. The per-turn response must not grow unboundedly as threads accumulate.
- **Life dimensions are orthogonal to pairwise correlations.** A person can have a strong basketball ↔ work correlation AND high time pressure across all threads simultaneously. They are different model layers and must be surfaced as such — don't conflate them.
- **Dimensions are environmental, not causal.** Sakhi surfaces "time is running thin across these threads" — it does not say "work caused your basketball to drop." The dimension is observed context, not an explanation. Prompts enforce this.
