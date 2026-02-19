# Kala - Architecture & Extraction Map

> Technical architecture of Kala's temporal intelligence primitives and their origin in Sakhi.

---

## Module Structure

```
kala/
├── memory/          # How living systems remember
│   ├── short_term       # Working memory with TTL decay
│   ├── episodic         # Significant moments, write-once
│   ├── long_term        # Consolidated knowledge via EMA blending
│   ├── recall           # Hybrid retrieval with recency weighting
│   └── graph            # Associative connections, strengthened by use
│
├── state/           # How living systems maintain identity
│   ├── baseline         # Constitutional reference (who you are)
│   ├── current          # Windowed aggregation (how you are now)
│   ├── drift            # Deviation from baseline (what's off)
│   ├── patterns         # Cause-effect learning over time
│   └── fusion           # Multi-source sensing with confidence
│
├── signals/         # How living systems sense the environment
│   ├── accumulator      # Collect events, extract patterns
│   ├── rhythm           # Detect cadence and regularity
│   ├── trend            # Period-over-period direction
│   └── load             # Capacity and overwhelm scoring
│
├── awareness/       # How living systems pay attention
│   ├── router           # What's relevant right now
│   ├── assembler        # Build temporal context for LLM calls
│   └── session          # Continuity across interactions
│
└── timeline/        # How you prove it works
    ├── harness          # Simulate days/weeks/months in minutes
    ├── persona          # Define entities with evolving arcs
    ├── snapshot         # Capture state at any point in time
    └── checkpoint       # "By day N, the system should know X"
```

Every module name maps to something a biology student would recognize. No "pipeline," no "orchestrator," no "service." Memory. State. Signals. Awareness. Timeline.

---

## Module 1: Memory

*How living systems remember.*

Memory in Kala is not a flat store. It's a tiered system where information flows from volatile short-term storage to consolidated long-term knowledge, with temporal decay governing what survives.

### 1.1 Short-Term Memory

**What it does:** Ephemeral evidence cache. Stores recent observations with automatic TTL-based expiry.

**Biological analog:** Working memory — holds recent items, fades naturally.

**Core mechanics:**
- Entries have a configurable TTL (default: 14 days)
- Each entry carries: text, embedding vector, metadata (sentiment, entities, tags)
- Auto-cleanup removes expired entries
- Triggers consolidation into long-term on insert

**Key parameters:**
| Parameter | Default | Purpose |
|---|---|---|
| `ttl_days` | 14 | How long before entries expire |
| `max_entries` | None | Optional cap on stored entries |

**Sakhi origin:** `sakhi/apps/api/services/memory/memory_short_term.py`
- `merge_into_short_term(person_id, record, vec)` — enriches + stores + triggers consolidation
- `memory_short_term` table — id, person_id, record (JSONB), vector_vec, expires_at

**Extraction notes:** Fully domain-agnostic. Remove sentiment/entity enrichment (make it pluggable). Keep TTL, vector storage, and consolidation trigger.

---

### 1.2 Episodic Memory

**What it does:** Write-once record of significant moments. Explicitly promoted from short-term, never mutated after creation.

**Biological analog:** Episodic memory — specific events you remember distinctly.

**Core mechanics:**
- Entries are promoted explicitly (not automatically) from STM
- Each entry carries: summary, source entry IDs, embedding, context tags
- Content-hashed to prevent duplicates
- Immutable after creation — the contract is "stable record"

**Key parameters:**
| Parameter | Default | Purpose |
|---|---|---|
| `dedup_by_hash` | true | Prevent duplicate episodes |

**Sakhi origin:** `sakhi/apps/api/services/memory/memory_episodic.py`
- `promote_to_episode(person_id, source_entry_ids, summary, embedding, context_tags)` — creates episodic row
- `memory_episodic` table — id, person_id, record (JSONB), vector_vec, content_hash, context_tags

**Extraction notes:** Fully domain-agnostic. The promotion logic (when to promote) is domain-specific and should be a callback.

---

### 1.3 Long-Term Memory

**What it does:** Consolidated knowledge that evolves slowly over time via exponential moving average (EMA) blending.

**Biological analog:** Semantic memory — general knowledge, personality, stable traits.

**Core mechanics:**
- Blends new observations into existing representation via EMA
- Decay factor prevents rapid drift from established identity
- Formula: `new_vector = (old_vector * count + embedding) / (count + 1)`
- Updates only significant dimensions, preserves stability

**Key parameters:**
| Parameter | Default | Purpose |
|---|---|---|
| `ema_decay` | count-based | Controls how fast new data influences long-term |
| `min_observations` | 1 | Minimum observations before consolidation |

**Sakhi origin:** `sakhi/apps/api/services/memory/memory_long_term.py`
- `consolidate_long_term(person_id)` — blends STM vector into LTM via EMA

**Extraction notes:** Fully domain-agnostic. The vector blending logic is pure math.

---

### 1.4 Recall

**What it does:** Hybrid memory retrieval combining semantic similarity (vectors) and keyword matching (BM25), weighted by recency.

**Biological analog:** Memory recall — more recent and more relevant memories surface first.

**Core mechanics:**
- Hybrid scoring: `score = (vector_sim * vector_weight) + (keyword_sim * keyword_weight)`
- Default weights: 70% vector, 30% keyword
- Recency weighting: `recency_weight = 0.5 ^ (age_days / halflife_days)`
- Diversity filter: removes results with >0.92 similarity to already-selected results
- Surface type weighting: configurable weights per source type
- Side effect: reinforces memory graph connections on recall

**Key parameters:**
| Parameter | Default | Purpose |
|---|---|---|
| `vector_weight` | 0.7 | Weight for semantic similarity |
| `keyword_weight` | 0.3 | Weight for keyword/BM25 matching |
| `recency_halflife_days` | 45 | Half-life for temporal decay |
| `diversity_threshold` | 0.92 | Max similarity between returned results |
| `k` | 8 | Number of results to return |

**Sakhi origin:** `sakhi/apps/api/services/memory/recall.py`, `bm25.py`
- `recall_advanced(person_id, query, k, vector_weight, keyword_weight, use_hybrid)` — main entry point
- `recall_with_keyword_boost()` — 50/50 vector/keyword split
- `recall_semantic_only()` — pure vector
- `bm25_search_all()` — PostgreSQL ts_rank_cd across all sources

**Extraction notes:** Fully domain-agnostic. Surface type weights should be configurable. BM25 implementation depends on PostgreSQL; abstract behind a search interface.

---

### 1.5 Graph

**What it does:** Associative knowledge graph where nodes represent concepts and edges represent relationships, strengthened by recall (use-dependent reinforcement).

**Biological analog:** Neural pathways — connections strengthen with use, weaken without.

**Core mechanics:**
- Node types: reflection, memory, person, place, topic, concept, insight, opportunity, contradiction, open_loop (extensible)
- Edge types: supports, relates_to (extensible)
- Edges carry weight = recall score at time of reinforcement
- Automatic consolidation: nodes with >0.93 cosine similarity are merged
- Candidates flagged at 0.87 similarity

**Key parameters:**
| Parameter | Default | Purpose |
|---|---|---|
| `merge_threshold` | 0.93 | Auto-merge nodes above this similarity |
| `candidate_threshold` | 0.87 | Flag as merge candidate |
| `max_batch` | 200 | Max nodes per consolidation run |

**Sakhi origin:** `sakhi/apps/api/services/memory/consolidation.py`, `graph_reinforcement.py`
- `consolidate_memory(person_id)` — pairwise comparison + merge
- `reinforce_recall_graph(person_id, query, recalled_items)` — strengthens connections on use

**Extraction notes:** Fully domain-agnostic. Node/edge types should be extensible. Merge logic is pure vector math.

---

## Module 2: State

*How living systems maintain identity.*

State in Kala represents the evolving model of an entity — what's normal for it, how it is right now, and how far it's drifted from normal.

### 2.1 Baseline

**What it does:** Immutable constitutional reference. Set once (from assessment, onboarding, or inference), rarely changed. Represents "what normal looks like" for this entity.

**Biological analog:** Homeostatic set point — the body's natural resting state.

**Core mechanics:**
- Defined as an N-dimensional vector (dimensions are domain-specific)
- Set from initial assessment or inferred from sufficient historical data
- Immutable after establishment (can be re-computed, not continuously updated)
- Stores source (how it was determined) and timestamp

**Data structure:**
```python
Baseline:
    dimensions: Dict[str, float]     # {"energy": 0.7, "focus": 0.5, "stress": 0.3}
    source: str                      # "assessment", "inferred_from_history"
    computed_at: datetime
    confidence: float                # Based on quality of input data
```

**Sakhi origin:** `sakhi/apps/api/services/ayurveda/prakruti.py`
- Prakruti = constitutional dosha baseline (3D: vata, pitta, kapha)
- Stored in `personal_model.operating_system.dosha_baseline`
- Computed once from onboarding quiz or inferred from history

**Extraction notes:** Generalize from 3D dosha space to N-dimensional arbitrary space. The concept is fully domain-agnostic; only the dimension names and computation source are domain-specific.

---

### 2.2 Current

**What it does:** Windowed aggregation of recent signals with exponential decay weighting. Represents "how the entity is right now."

**Biological analog:** Current physiological state — your body temperature, heart rate, cortisol levels *right now*.

**Core mechanics:**
- Aggregates observations within a configurable window (default: 7 days)
- Applies exponential decay: `weight = exp(-lambda * days_ago)`
- More recent observations contribute more to current state
- Normalizes to same dimensional space as baseline
- Reports confidence based on observation count and data freshness

**Key parameters:**
| Parameter | Default | Purpose |
|---|---|---|
| `window_days` | 7 | Lookback period for aggregation |
| `decay_lambda` | 0.5 | Controls decay rate (half-life ~1.4 days at 0.5) |
| `min_observations` | 3 | Minimum observations for confident state |

**Formula:**
```
For each observation i within window:
    weight_i = exp(-lambda * days_since(observation_i))

current_state[dim] = sum(observation_i[dim] * weight_i) / sum(weight_i)

confidence = min(1.0, observation_count / 10) * freshness_factor
```

**Sakhi origin:** `sakhi/apps/api/services/ayurveda/vikriti.py`
- Vikriti = current dosha state (3D: vata, pitta, kapha)
- 7-day window, decay_lambda=0.5
- Fuses journal episodes (70%) + body data (40% relative weight)
- Computed on-demand, not persisted

**Extraction notes:** Generalize to N-dimensional space. Make data source fusion configurable. The math is fully domain-agnostic.

---

### 2.3 Drift

**What it does:** Measures deviation between baseline and current state. The core "something is off" detector.

**Biological analog:** Homeostatic imbalance — fever, elevated cortisol, fatigue.

**Core mechanics:**
- Computes distance in N-dimensional space between baseline and current
- Supports multiple distance metrics (Euclidean default)
- Scales to 0-100% for interpretability
- Classifies severity into configurable buckets
- Identifies primary contributing dimension (which dimension is most deviated)

**Key parameters:**
| Parameter | Default | Purpose |
|---|---|---|
| `distance_metric` | "euclidean" | Distance function (euclidean, manhattan, cosine) |
| `scale_factor` | 87 | Normalization to 0-100% (depends on dimensionality) |
| `severity_thresholds` | [15, 25, 40] | Bucket boundaries for minimal/mild/moderate/significant |

**Data structure:**
```python
DriftResult:
    drift_percentage: float              # 0-100
    severity: str                        # "minimal", "mild", "moderate", "significant"
    primary_contributor: str             # Which dimension is most deviated
    direction: str                       # "elevated" or "depleted"
    per_dimension: Dict[str, float]      # Raw delta per dimension
    confidence: float                    # Based on current state confidence
```

**Sakhi origin:** `sakhi/apps/api/services/ayurveda/vikriti.py`
- `drift_percentage = min(100, euclidean_distance * 87)`
- Identifies which dosha is elevated/depleted
- Maps to friction states (chaos/intensity/stagnation)

**Extraction notes:** Fully domain-agnostic. Remove friction mapping (that's a domain layer). Keep distance math and severity classification.

---

### 2.4 Patterns

**What it does:** Learns cause-effect relationships over time by detecting temporal correlations between events.

**Biological analog:** Conditioned response — your body learns that late-night coffee → poor sleep.

**Core mechanics:**
- Extracts "causes" (behaviors, events) and "effects" (outcomes, symptoms) from observations
- Detects co-occurrence within a temporal window (default: 48 hours)
- Confidence grows logarithmically with observation count: `0.5 + 0.15 * log(count + 1)`
- Patterns are upserted (strengthened on re-observation, not duplicated)
- Old patterns decay if not re-observed

**Key parameters:**
| Parameter | Default | Purpose |
|---|---|---|
| `correlation_window_hours` | 48 | Max time between cause and effect |
| `min_observations` | 2 | Minimum co-occurrences to establish pattern |
| `confidence_fn` | log-growth | How confidence grows with observations |

**Data structure:**
```python
TemporalPattern:
    cause: Tuple[str, str]               # (type, value) e.g. ("behavior", "skipped_lunch")
    effect: Tuple[str, str]              # (type, value) e.g. ("symptom", "afternoon_fatigue")
    observation_count: int
    correlation_strength: float          # 0-1, log-growth
    confidence: float                    # 0-1, log-growth
    first_observed_at: datetime
    last_observed_at: datetime
```

**Sakhi origin:** `sakhi/apps/api/services/ayurveda/pattern_learning.py`
- Extracts behaviors + symptoms from journal text
- Detects behavior→symptom co-occurrence within 48h
- Upserts to `personal_patterns` table
- `correlation_strength = 0.5 + 0.15 * log(count + 1)`

**Extraction notes:** Mostly domain-agnostic. The extraction of causes/effects from text is domain-specific (pluggable). The temporal correlation and confidence math is universal.

---

### 2.5 Fusion

**What it does:** Combines signals from multiple data sources into a unified state representation, weighted by source reliability and availability.

**Biological analog:** Sensory integration — your brain fuses vision, hearing, and touch into one coherent perception.

**Core mechanics:**
- Each data source has a weight and a confidence factor
- Missing sources degrade gracefully (confidence adjusts, doesn't break)
- Supports source-specific credibility scoring
- Handles multi-modal data (narrative, physiological, behavioral)

**Key parameters:**
| Parameter | Default | Purpose |
|---|---|---|
| `source_weights` | configurable | Relative weight per data source |
| `missing_strategy` | "degrade" | How to handle missing sources |
| `confidence_boost` | true | Boost confidence when more sources available |

**Sakhi origin:** `sakhi/apps/api/services/ayurveda/vikriti.py`
- Fuses journal episodes (narrative) + body_state_history (physiological)
- Body data at 40% relative weight
- Confidence boosted when body data is available

**Extraction notes:** Fully domain-agnostic. Define a `DataSource` interface; let domains register their sources.

---

## Module 3: Signals

*How living systems sense the environment.*

Signals in Kala represent the accumulation of events over time and the patterns that emerge from them. Unlike memory (which stores what happened), signals detect *what's happening* — ongoing trends, rhythms, and load.

### 3.1 Accumulator

**What it does:** Stores normalized events from any source and provides them to independent signal detectors for pattern extraction.

**Biological analog:** Sensory receptor — collects raw stimuli before interpretation.

**Core mechanics:**
- Normalizes events to a common schema (timestamp, direction, source, metadata)
- Stores accumulated events in a time-indexed table
- Provides windowed access to detectors (e.g., "last 7 days", "last 90 days")
- Signal extraction is cached (default: 6 hours) to avoid redundant computation
- Detectors are independent — each gets the same event list and produces typed output

**Event schema:**
```python
TemporalEvent:
    event_id: str
    entity_id: str                   # Who this event belongs to
    source: str                      # "email", "slack", "calendar", "custom"
    timestamp: datetime
    direction: str                   # "incoming", "outgoing", "internal"
    participants: List[Participant]
    metadata: Dict[str, Any]         # Source-specific fields
    tags: List[str]                  # Auto-classified tags
```

**Sakhi origin:** `sakhi/apps/api/services/email/models.py`, `integration.py`
- `EmailEvent` — normalized email metadata (message_id, thread_id, direction, sender, subject, headers)
- `email_events` table — accumulated events
- `extract_all_signals()` — runs all detectors, caches for 6 hours
- Each detector independently analyzes accumulated events

**Extraction notes:** Abstract `EmailEvent` to `TemporalEvent`. The accumulator + independent detector pattern is fully domain-agnostic. Source-specific adapters (Gmail, Slack, etc.) are pluggable.

---

### 3.2 Rhythm

**What it does:** Detects regularity and cadence in event streams — distinguishing between regular patterns (daily newsletters, weekly meetings) and irregular noise.

**Biological analog:** Circadian rhythm detection — recognizing cyclical patterns.

**Core mechanics:**
- Groups events by relevant dimension (sender, category, topic)
- Computes inter-event gaps
- Calculates coefficient of variation (CV) to measure regularity
- Classifies cadence: daily, weekly, biweekly, monthly, yearly, irregular
- Confidence based on regularity: CV < 0.3 = 0.9 confidence, CV > 1.0 = 0.3

**Key parameters:**
| Parameter | Default | Purpose |
|---|---|---|
| `window_days` | 90 | Lookback period for cadence detection |
| `min_occurrences` | 2 | Minimum events to detect pattern |
| `cadence_thresholds` | [1.5, 8, 16, 35, 400] | Gap thresholds for daily/weekly/etc. |

**Sakhi origin:** `sakhi/apps/api/services/email/signals/subscription.py`
- `_detect_cadence()` — gap analysis + CV calculation
- Groups by sender domain, classifies as daily/weekly/monthly
- Cadence confidence from coefficient of variation

**Extraction notes:** Fully domain-agnostic. The cadence detection algorithm works on any event stream grouped by any dimension.

---

### 3.3 Trend

**What it does:** Compares metrics across time periods to detect direction — improving, stable, or worsening.

**Biological analog:** Trend perception — "I've been sleeping worse this week than last week."

**Core mechanics:**
- Divides events into current period and comparison period
- Computes metrics for each period (configurable metric functions)
- Calculates delta between periods
- Classifies direction: improving (delta < -threshold), stable, worsening (delta > threshold)
- Produces composite score from weighted sub-metrics

**Key parameters:**
| Parameter | Default | Purpose |
|---|---|---|
| `period_days` | 7 | Length of current and comparison period |
| `direction_threshold` | 0.1 | Minimum delta to classify as improving/worsening |
| `metric_weights` | configurable | Weights per sub-metric in composite score |

**Data structure:**
```python
TrendResult:
    period_start: datetime
    period_end: datetime
    current_score: float                 # 0-1 composite
    previous_score: float                # 0-1 composite
    delta: float                         # current - previous
    direction: str                       # "improving", "stable", "worsening"
    sub_metrics: Dict[str, float]        # Individual metric scores
    confidence: float
```

**Sakhi origin:** `sakhi/apps/api/services/email/signals/boundary.py`
- Computes after_hours_pct, weekend_pct, late_night_pct for current vs previous 7 days
- Erosion score = 0.5 * after_hours + 0.3 * weekend + 0.2 * late_night
- Delta > 0.1 = "worsening", < -0.1 = "improving"

**Extraction notes:** Fully domain-agnostic. Replace email-specific metrics (after_hours, weekend) with pluggable metric functions. The period comparison and direction classification is universal.

---

### 3.4 Load

**What it does:** Measures current capacity utilization and overwhelm risk from event volume and complexity.

**Biological analog:** Cognitive load — the mental burden of active tasks and responsibilities.

**Core mechanics:**
- Counts active items (recent activity within a sub-window)
- Identifies "heavy" items (high message count or participant count)
- Combines volume, activity, and complexity into a composite load score
- Classifies overwhelm risk: low, moderate, high

**Key parameters:**
| Parameter | Default | Purpose |
|---|---|---|
| `period_days` | 7 | Analysis window |
| `active_recency_days` | 3 | Sub-window for "active" classification |
| `heavy_threshold_messages` | 10 | Messages to classify as "heavy" |
| `heavy_threshold_participants` | 5 | Participants to classify as "heavy" |

**Formula:**
```
load_score = (
    min(1.0, active_count / 20) * 0.4 +     # Activity factor
    min(1.0, heavy_count / 5)  * 0.4 +       # Complexity factor
    min(1.0, total_count / 200) * 0.2        # Volume factor
)

overwhelm_risk = "high" if load_score >= 0.7 else "moderate" if load_score >= 0.4 else "low"
```

**Sakhi origin:** `sakhi/apps/api/services/email/signals/cognitive_load.py`
- `compute_cognitive_load()` — active threads, heavy threads, volume
- Thread building: group by thread_id, count participants + messages
- Load score = 0.4 * active_factor + 0.4 * heavy_factor + 0.2 * volume_factor

**Extraction notes:** Fully domain-agnostic. Replace "thread" with "conversation" or "item." The load scoring formula works for any domain with countable active items.

---

## Module 4: Awareness

*How living systems pay attention.*

Awareness in Kala decides what temporal context matters right now and how to assemble it for an LLM call. This is the bridge between Kala's temporal state and the model that acts on it.

### 4.1 Router

**What it does:** Determines which temporal contexts are relevant for a given interaction, gating expensive lookups behind cheap classification.

**Biological analog:** Attentional filtering — your brain doesn't process every sensory input, it selects what's relevant.

**Core mechanics:**
- Tier 1 (always): Cheap, fast context scan — one-liner summary per temporal module
- Tier 2 (gated): Expensive deep context — LLM calls, database reads, complex computation
- Gating via: keyword matching → intent classification → time-of-day → LLM fallback
- Returns set of active modules for Tier 2 loading

**Context modules (extensible):**
- identity, emotional, scheduling, patterns, body, signals, causal, recommendations

**Sakhi origin:** `sakhi/apps/api/services/conversation_v2/context_router.py`
- `classify_context_needs(text, intents, topics, emotion, hour)` — returns active modules
- Keyword matching: `_EMAIL_KEYWORDS`, `_SCHEDULING_KEYWORDS`, etc.
- LLM fallback if confidence < 0.5

**Extraction notes:** The two-tier gating pattern is fully domain-agnostic. Module names and keyword lists are domain-specific (pluggable).

---

### 4.2 Assembler

**What it does:** Builds structured temporal context for LLM calls by pulling from all active Kala modules.

**Biological analog:** Consciousness — the integrated representation of relevant state that guides action.

**Core mechanics:**
- Loads deterministic context (personal model, state vectors) in a single DB query
- Adds memory recall (vector + keyword, recency-weighted)
- Adds signal summaries (drift, patterns, load)
- Adds session continuity (compressed prior conversation)
- Structures everything as system message(s) for the LLM
- Tier 1 scan is always included; Tier 2 sections are gated by router

**Output structure:**
```python
TemporalContext:
    scan: str                    # One-liner per module (always present)
    deep_sections: Dict[str, str]   # Module-specific deep context (gated)
    recall: str                  # Relevant memories
    session_summary: str         # Prior conversation compressed
    metadata: Dict[str, Any]     # Confidence, timing, active modules
```

**Sakhi origin:** `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py`, `conversation_context_builder.py`, `deterministic_context_loader.py`
- Loads 14 fields from `personal_model` in single query
- Builds tiered prompt: scan + deep sections + recall + session summary
- Assembles as system messages for `call_llm()`

**Extraction notes:** The assembly pattern is domain-agnostic. The prompt structure and section content are domain-specific. Kala should provide the structured data; the application formats it for their LLM.

---

### 4.3 Session

**What it does:** Maintains continuity across interactions within a session — compressing older turns, tracking entity references, preserving conversational state.

**Biological analog:** Working narrative — the story you're holding in mind during a conversation.

**Core mechanics:**
- Session lifecycle: create, activate, archive
- Turn appending with metadata (role, text, tone, source)
- Session matching: find best session for a query (cosine similarity + recency boost)
- Compression: older turns → semantic summary (preserves pronouns, topics, emotional arc)
- Max active sessions: configurable (default: 6), oldest auto-archived

**Key parameters:**
| Parameter | Default | Purpose |
|---|---|---|
| `max_active_sessions` | 6 | Auto-archive oldest when exceeded |
| `recency_boost_1h` | 0.10 | Similarity boost for sessions within 1 hour |
| `recency_boost_6h` | 0.05 | Similarity boost for sessions within 6 hours |
| `compression_trigger` | 8 turns | When to compress older turns |

**Sakhi origin:** `sakhi/apps/api/services/memory/sessions.py`, `session_match.py`
- `ensure_session(user_id, slug)` — get or create active session
- `best_match(user_id, text)` — cosine similarity + recency boost
- Session compression: LLM summary of older turns preserving entities + emotional thread

**Extraction notes:** Fully domain-agnostic. Session management is pure conversation infrastructure.

---

## Module 5: Timeline

*How you prove it works.*

Timeline is Kala's built-in testing framework for temporal systems. Traditional tests verify a function returns the right value. Timeline tests verify that a system's understanding evolves correctly over simulated time.

### 5.1 Harness

**What it does:** Simulates the passage of days/weeks/months by processing synthetic entries through the full temporal pipeline, with deterministic time progression.

**Biological analog:** Longitudinal study — observe a subject over an extended period under controlled conditions.

**Core mechanics:**
- Day-by-day sequential processing
- Entries are backdated to simulated timestamps (not wall-clock time)
- Workers run synchronously for deterministic behavior
- Daily aggregate workers run at configurable intervals
- Background task drainage ensures async operations complete before next step
- Supports "production parity" mode: route through real API endpoints

**Key parameters:**
| Parameter | Default | Purpose |
|---|---|---|
| `snapshot_interval` | 7 | Days between state snapshots |
| `daily_worker_interval` | 3 | Run aggregate workers every N simulated days |
| `run_workers` | true | Whether to run the processing pipeline |
| `production_parity` | false | Route through real API for exact production behavior |

**Sakhi origin:** `sakhi/tests/longitudinal/simulation_harness.py`
- `SimulationHarness` — main orchestrator
- `_run_day(day)` — generate + process entries for one simulated day
- `_process_entry(entry_id)` — run 5 per-turn workers synchronously
- `_run_daily_workers(day)` — run 15 daily aggregate workers
- Backdates all created rows to simulated timestamps

**Extraction notes:** The simulation framework is domain-agnostic. Worker definitions and table schemas are domain-specific (pluggable via configuration). The core loop (generate → process → snapshot → assert) is universal.

---

### 5.2 Persona

**What it does:** Defines synthetic test entities with personality traits, life context, and multi-phase emotional/behavioral arcs that evolve over simulated time.

**Biological analog:** Case study subject — a defined individual whose journey you trace.

**Core mechanics:**
- Traits with intensity (0-1 scale) and behavioral patterns
- Life context: occupation, relationships, challenges, values
- Multi-phase arcs: each phase has emotional state, themes, events, duration
- Phase transitions define the expected evolution
- Entry generation uses full persona context for realistic synthetic data

**Data structure:**
```python
PersonaSpec:
    id: str
    name: str
    baseline: Dict[str, float]           # State dimensions + starting values
    traits: List[PersonaTrait]           # Personality traits with intensity
    life_context: LifeContext            # Occupation, relationships, etc.
    arc: PersonaArc                      # Multi-phase journey
        phases: List[ArcPhase]
            emotional_state: str
            duration_days: int
            state_shift: Dict[str, float]   # Dimension adjustments for this phase
            themes: List[str]
            events: List[str]
            entry_frequency: float          # Entries per day multiplier
    checkpoints: List[Checkpoint]        # What the system should know by when
```

**Sakhi origin:** `sakhi/tests/longitudinal/persona_spec.py`
- `PersonaSpec` with `DoshaProfile`, `RhythmProfile`, `PersonaTrait`, `LifeContext`, `ArcPhase`
- YAML personas: anxious_achiever (66 days), stuck_creative (70 days), hormonal_harmony (68 days)
- `get_phase_at_day(day)` — returns which arc phase is active

**Extraction notes:** Mostly domain-agnostic. Replace `DoshaProfile` with generic `BaselineProfile`. Keep trait system, life context, arc phases, and checkpoint definitions.

---

### 5.3 Snapshot

**What it does:** Captures the complete temporal state of an entity at a point in simulated time, enabling before/after comparison and evolution visualization.

**Core mechanics:**
- Captures: full model state, memory count, pattern count, drift state
- Includes provenance: row counts proving the pipeline actually ran
- Includes brain/module states for all registered modules
- Serializable to JSON for export and visualization

**Data structure:**
```python
StateSnapshot:
    day: int
    timestamp: datetime
    model_state: Dict[str, Any]          # Full entity model
    memory_count: int                    # Episodic memories
    pattern_count: int                   # Learned patterns
    drift_state: DriftResult             # Current drift from baseline
    recent_memories: List[Dict]          # Last N episodic memories
    provenance: Dict[str, int]           # Row counts proving pipeline ran
    module_states: Dict[str, Any]        # Per-module state snapshots
    worker_results: Dict[str, Any]       # Results from last worker run
```

**Sakhi origin:** `sakhi/tests/longitudinal/simulation_harness.py` (`StateSnapshot` dataclass)
- Queries `personal_model` for full brain state
- Counts `memory_episodic`, `pattern_occurrences`
- Extracts theme_states, crystallized_patterns, brain module states

**Extraction notes:** Domain-agnostic structure. Module names and specific queries are domain-specific.

---

### 5.4 Checkpoint

**What it does:** Defines temporal assertions — "by day N, the system should understand X" — and verifies them against actual state.

**Biological analog:** Clinical milestone — "by week 6, the patient should show improved markers."

**Core mechanics:**
- Assertions are defined per checkpoint day
- Each assertion has a type and expected value
- Assertions run against actual state (queries DB or computes on-demand)
- Results: passed/failed with actual vs expected and explanation
- Non-fatal: individual assertion failures don't stop the simulation

**Supported assertion types:**
| Type | What it checks |
|---|---|
| `drift_state` | Is drift at expected severity? (minimal/mild/moderate/significant) |
| `drift_direction` | Is a specific dimension elevated or depleted? |
| `pattern_learned` | Has a cause-effect pattern been observed N times with M confidence? |
| `theme_emerged` | Do N episodic memories mention keywords related to theme? |
| `state_shift` | Has a specific dimension changed by a minimum percentage? |

**Sakhi origin:** `sakhi/tests/longitudinal/assertions.py`
- `assert_friction_state()`, `assert_pattern_crystallized()`, `assert_theme_emerged()`
- `assert_rhythm_learned()`, `assert_dosha_drift()`
- `run_checkpoint_assertions()` — routes each to appropriate function

**Extraction notes:** The assertion framework is domain-agnostic. Replace dosha/friction assertions with generic state/drift/pattern assertions. The checkpoint concept is universal.

---

## Extraction Map: Sakhi → Kala

### Fully Extractable (~75% of codebase)

| Sakhi Component | Kala Module | Extraction Effort |
|---|---|---|
| `memory/memory_short_term.py` | `memory.short_term` | Low — remove wellness enrichment |
| `memory/memory_episodic.py` | `memory.episodic` | Low — direct mapping |
| `memory/memory_long_term.py` | `memory.long_term` | Low — pure math |
| `memory/recall.py` + `bm25.py` | `memory.recall` | Medium — abstract search backend |
| `memory/consolidation.py` + `graph_reinforcement.py` | `memory.graph` | Low — direct mapping |
| `ayurveda/vikriti.py` (state computation) | `state.current` + `state.drift` | Medium — generalize from 3D to N-D |
| `ayurveda/pattern_learning.py` (correlation engine) | `state.patterns` | Medium — make extraction pluggable |
| `email/signals/*.py` (all 4 detectors) | `signals.*` | Medium — abstract from email to generic events |
| `email/integration.py` (orchestration) | `signals.accumulator` | Low — direct mapping |
| `conversation_v2/context_router.py` | `awareness.router` | Medium — make modules pluggable |
| `conversation_v2/conversation_reasoner.py` | `awareness.assembler` | Medium — separate data from formatting |
| `memory/sessions.py` + `session_match.py` | `awareness.session` | Low — direct mapping |
| `tests/longitudinal/simulation_harness.py` | `timeline.harness` | Medium — abstract worker interface |
| `tests/longitudinal/persona_spec.py` | `timeline.persona` | Low — replace dosha with generic baseline |
| `tests/longitudinal/assertions.py` | `timeline.checkpoint` | Low — generalize assertion types |

### Stays in Sakhi (~25% of codebase)

| Sakhi Component | Why It Stays |
|---|---|
| `ayurveda/prakruti.py` (dosha computation) | Ayurvedic-specific: quiz→dosha scoring, dosha taxonomy |
| `ayurveda/causal_reasoning.py` | Dosha-based causal chains, Ayurvedic pathophysiology |
| `ayurveda/graph_reasoning.py` | `ay_nodes`/`ay_edges` with classical Ayurvedic citations |
| `ayurveda/food_recommendations.py` | Dosha-specific food guidance, rasa/virya/vipaka |
| `memory/food_memory.py` | Food/restaurant domain model |
| `memory/sensory_preferences.py` | Temperature/texture/spice/ambiance (dining domain) |
| `memory/emotion_tagging.py` | Wellness-specific emotion detection |
| `email/adapters/gmail.py` | Gmail OAuth + incremental sync (channel-specific) |
| Friction state naming (chaos/intensity/stagnation) | Ayurvedic domain mapping |
| Personal model wellness_state, soul_state | Sakhi's wellness domain model |

### Sakhi Becomes First Domain Implementation

After extraction, Sakhi's Ayurvedic layer becomes the first "domain implementation" on top of Kala:

```
kala/                           # The library (domain-agnostic)
└── [all modules above]

sakhi/
├── domains/
│   └── ayurveda/
│       ├── baseline.py         # Dosha-based baseline (implements kala.state.Baseline)
│       ├── dimensions.py       # 3D dosha space definition
│       ├── drift_mapping.py    # Drift → friction state naming
│       ├── knowledge_graph.py  # ay_nodes, ay_edges, classical citations
│       ├── causal.py           # Dosha-based causal reasoning
│       └── food.py             # Dosha-specific food recommendations
├── adapters/
│   ├── gmail.py                # Gmail adapter (implements kala.signals.EventSource)
│   └── healthkit.py            # HealthKit adapter (implements kala.state.DataSource)
└── app/                        # Sakhi application layer
```

---

## Database Dependencies

Kala will need a storage backend. Initial implementation will target PostgreSQL (matching Sakhi), with the schema abstracted behind repository interfaces for future backend flexibility.

### Core Tables (Kala owns)

| Table | Module | Purpose |
|---|---|---|
| `kala_short_term_memory` | memory.short_term | Ephemeral evidence with TTL |
| `kala_episodic_memory` | memory.episodic | Write-once significant moments |
| `kala_memory_nodes` | memory.graph | Knowledge graph nodes |
| `kala_memory_edges` | memory.graph | Knowledge graph edges |
| `kala_entity_model` | state.* | Baseline, current, long-term state |
| `kala_temporal_events` | signals.accumulator | Accumulated events from any source |
| `kala_signals` | signals.* | Extracted signal snapshots |
| `kala_patterns` | state.patterns | Learned cause-effect relationships |
| `kala_sessions` | awareness.session | Conversation sessions + turns |

### Extension Tables (Domain provides)

Domains can register additional tables that Kala's pipeline will include in snapshots and cleanup, but doesn't directly manage.

---

*Last updated: 2026-02-20*
