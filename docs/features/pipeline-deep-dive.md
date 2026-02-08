# Sakhi Pipeline: Journal Entry → Personal Graph → Personalized Response

> **Audience:** Cofounder / Technical Leadership
> **Last Updated:** 2026-02-07

---

## The Big Picture

When a user sends a message, **three things happen in sequence**:

1. **Synchronous** (during the request, ~1-2s): Observe → Enrich → Load personal state → Route context → Build prompt → Generate reply
2. **Async workers** (after response returns): Memory ingestion, episodic consolidation, preference/pattern learning
3. **Scheduled workers** (daily/weekly): Deep state updates, crystallization, rhythm forecasting, identity evolution

The result: every subsequent conversation is more personalized because the personal graph grows with each turn.

---

## Phase 1: Synchronous Turn Processing

**Entry point:** `POST /v2/turn` → `turn_v2()` in `sakhi/apps/api/routes/turn_v2.py`

**Input:**
```python
class TurnIn(BaseModel):
    text: str                  # User's message/journal entry
    clarity_phrase: str | None # Optional clarity hint
    capture_only: bool         # If True, minimal processing
    image_data: str | None     # Base64 image (optional)
    media_ids: list | None     # Previously uploaded media IDs
    source: str = "text"       # "text", "voice", "vision"
```

### Step-by-step execution:

```
User: "I skipped breakfast again and feel scattered"
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  1. RESOLVE USER + VALIDATE INPUT                       │
│     resolve_person(request) → user_id                   │
│     Validate text not empty                             │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  2. SESSION + HISTORY                                   │
│     ensure_session() → session_id                       │
│     load_context_with_summary()                         │
│       → Last 8 turns verbatim                           │
│       → Compressed summary if >16 turns                 │
│     TABLES READ: conversation_sessions,                 │
│                  conversation_turns                      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  3. JOURNAL ORCHESTRATION (the "observe" pipeline)      │
│                                                         │
│  a. observe_entry()                                     │
│     → WRITE: journal_entries                            │
│                                                         │
│  b. generate_journal_embedding()                        │
│     → OpenAI text-embedding-3-small (1536 dims)         │
│     → WRITE: journal_embeddings                         │
│                                                         │
│  c. extract_topics_for_entry()   [LLM call]             │
│     → WRITE: journal_topics                             │
│                                                         │
│  d. detect_emotion_for_entry()   [LLM call]             │
│     → {"label": "scattered", "confidence": 0.85}        │
│     → WRITE: journal_emotions                           │
│                                                         │
│  e. enrich_short_term_memory()                          │
│     → WRITE: memory_short_term, personal_model          │
│                                                         │
│  f. extract_intents() + store_intent()  [LLM call]      │
│     → WRITE: user_intents                               │
│                                                         │
│  g. plan_from_intents() + store_planned_items()          │
│     → WRITE: user_plans                                 │
│                                                         │
│  h. detect_rhythm_related_intents()                     │
│     → WRITE: rhythm_events (if triggered)               │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  4. LOAD BRAIN STATE                                    │
│     _get_brain_state_from_personal_model()              │
│     READ: personal_model →                              │
│       operating_system (prakruti / baseline dosha)       │
│       emotion_state, soul_state, rhythm_state           │
│       longitudinal_state, identity_momentum_state       │
│                                                         │
│     _load_internal_state()                              │
│     READ: personal_model →                              │
│       cognitive_load, priorities, soul_values            │
│       life_themes, identity_graph, decision_profile     │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  5. CONTEXT ROUTER (determines what to compute)         │
│     route_context(text, intents, topics, emotion, hour) │
│                                                         │
│  File: sakhi/apps/api/services/context_router.py        │
│                                                         │
│     Deterministic rules:                                │
│       "scattered" → emotional_depth, causal             │
│       hour=14 → (no morning/evening ritual)             │
│       "skipped breakfast" → recommendations             │
│                                                         │
│     If confidence < 0.5 → LLM fallback classifier      │
│                                                         │
│     OUTPUT: active_modules = {"emotional_depth",        │
│              "causal", "recommendations"}               │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  6. TIER 1: ALWAYS COMPUTE (cheap, ~0ms each)           │
│                                                         │
│  Pure functions on brain_state (no DB, no LLM):         │
│    compute_fast_narrative()        → dominant theme      │
│    compute_alignment()             → values alignment    │
│    compute_fast_rhythm_soul()      → circadian coherence │
│    compute_fast_esr_frame()        → emotion pattern     │
│    compute_fast_identity_momentum()→ growth trajectory   │
│    compute_fast_identity_timeline()→ current life phase  │
│                                                         │
│  Always-run DB reads (cheap, have side effects):        │
│    compute_microreg()   → emotional regulation state    │
│    compute_empathy()    → empathy pattern               │
│    compute_tone()       → response tone                 │
│    compute_moment_model()→ companion mode, load, energy │
│                                                         │
│  Cache reads (daily precomputed):                       │
│    morning_preview_cache, morning_ask_cache              │
│    evening_closure_cache, daily_reflection_cache         │
│    micro_momentum_cache, micro_recovery_cache           │
│    focus_path_cache, mini_flow_cache,                   │
│    micro_journey_cache                                  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  7. TIER 2: GATED BY ROUTER (expensive, only if needed) │
│                                                         │
│  IF "emotional_depth" in active_modules:                │
│    inner_dialogue_engine.compute_inner_dialogue() [LLM] │
│    load nudge_state from personal_model                 │
│                                                         │
│  IF "moment" in active_modules:                         │
│    select_evidence_anchors()  [DB+LLM]                  │
│    compute_deliberation_scaffold()                      │
│    persist_reflection_trace()                           │
│    → WRITE: reflection_traces                           │
│                                                         │
│  IF "recommendations" OR drift > 25%:                   │
│    compute_current_vikriti() → current dosha state      │
│    compute_baseline_drift() → drift percentage          │
│    classify_friction_state()                            │
│    → Chaos / Intensity / Stagnation / Balanced          │
│    build_recommendation_context() [DB reads]            │
│    generate_personalized_recommendations() [KG + LLM]   │
│                                                         │
│  IF "causal" OR drift > 15%:                            │
│    explain_friction_state()                             │
│    → why you feel this way                              │
│                                                         │
│  IF "email": email context + contact preferences        │
│  IF "scheduling": calendar queries + relationship nudges│
│  IF "micro_flow": generate_focus_path() / mini_flow()   │
│  IF "vision": process_image() pipeline                  │
│  IF "agentic": web_search() + tool detection            │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  8. BUILD METADATA PAYLOAD (60+ fields)                 │
│                                                         │
│  metadata_payload = {                                   │
│    active_modules,                                      │
│    entry_id, topics, emotion, intents, plans,           │
│    internal_state, brain_state,                         │
│                                                         │
│    # Tier 1 (always):                                   │
│    narrative_trace, alignment_frame,                    │
│    rhythm_soul_frame, esr_frame,                        │
│    identity_momentum, identity_timeline,                │
│    microreg_state, empathy_state, tone_state,           │
│    moment_model,                                        │
│                                                         │
│    # Tier 2 (gated):                                    │
│    inner_dialogue, nudge_state, evidence_pack,          │
│    deliberation_scaffold, friction_state,               │
│    personalized_recommendations,                        │
│    causal_explanation, email_context,                   │
│    scheduling_context, ...                              │
│                                                         │
│    # Continuity:                                        │
│    conversation_history, session_summary,               │
│                                                         │
│    # Guards:                                            │
│    recommendation_guard, scheduling_guard, ...          │
│  }                                                      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  9. GENERATE REPLY (LLM call)                           │
│                                                         │
│  build_prompt() assembles:                              │
│  ┌───────────────────────────────────────────┐          │
│  │ [PERSONA] warm, reflective               │          │
│  │                                           │          │
│  │ [CONTEXT SCAN — 360° awareness]  ← Tier 1│          │
│  │ Identity: momentum=fwd, align=0.7        │          │
│  │ Emotional: empathy=mirror, risk=low      │          │
│  │ Moment: mode=supportive, load=med        │          │
│  │ Friction: Chaos (drift=35%)              │          │
│  │                                           │          │
│  │ [EMOTIONAL ATTUNEMENT]           ← Tier 2│          │
│  │ Inner voice: gentle grounding            │          │
│  │ Empathy: mirror emotion first            │          │
│  │                                           │          │
│  │ [AYURVEDIC INSIGHT]              ← Causal│          │
│  │ Vata elevated. Pattern: skipping         │          │
│  │ breakfast → scattered (seen 5x).         │          │
│  │ Winter amplifies this.                   │          │
│  │                                           │          │
│  │ [RECOMMENDATIONS - PROACTIVE]    ← Recs  │          │
│  │ Foods: warm oats, ghee, ginger tea       │          │
│  │ Practice: 5min grounding breathwork      │          │
│  │ Personal: warm milk worked before        │          │
│  │                                           │          │
│  │ [SHORT-TERM MEMORY]                      │          │
│  │ [CONVERSATION HISTORY]                   │          │
│  │ [RESPONSE INSTRUCTIONS]                  │          │
│  └───────────────────────────────────────────┘          │
│                                                         │
│  → GPT-4o-mini generates response                       │
│  → WRITE: conversation_turns (user + assistant)         │
│  → WRITE: personal_model (short_term, persona, topics)  │
│  → WRITE: session_continuity                            │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  RETURN TO USER      │
              │  (~1-2 seconds)      │
              └──────────────────────┘
```

---

## Phase 2: Async Per-Turn Workers

Three jobs are enqueued for every turn. When `SAKHI_DISABLE_QUEUE=1` (dev), they run inline in the FastAPI process. In production, they go to Redis/RQ.

**File:** `sakhi/apps/worker/pipelines/turn_updates/runner.py`

### Worker 1: turn_memory_update

**What it does:** Ingests journal text into the unified memory system via `ingest_heavy()`.

| Writes to | What |
|-----------|------|
| `memory_short_term` | STM entry with embedding, content hash, expiry |
| `personal_model` | Long-term state (emotion/mind/soul summaries) |
| `wellness_state_cache` | Body/mind/emotion/energy rollup |
| `narrative_arc_cache` | Active life themes/arcs |
| `memory_context_cache` | Invalidation for next turn refresh |

**Key algorithms:** Wellness scoring from keywords, emotion loop state computation, arc detection via word clustering, soul relevance detection.

### Worker 2: episodic_consolidation_v21

**File:** `sakhi/apps/worker/tasks/episodic_consolidation_v21.py` (1379 lines)

**What it does:** Summarizes the day's journal entries into a single episode with soul signals, state vectors, and memory graph links.

**Process:**

| Step | What | Method |
|------|------|--------|
| 1 | Bin all journal entries to UTC calendar day window | Deterministic |
| 2 | Dedup via content hash (skip if same entries as before) | Deterministic |
| 3 | Summarize day → episode text | LLM |
| 4 | Extract soul, soul_shadow, soul_light | LLM |
| 5 | Compute emotional_state (tone, valence, activation) | LLM |
| 6 | Compute rhythm_state (energy_trend, load_balance) | LLM |
| 7 | Compute state_vector (vata/pitta/kapha scores) | Deterministic (keyword-based) |
| 8 | Compute guna_vector (sattva/rajas/tamas) | Deterministic |
| 9 | Detect soul_conflict (value vs value tension) | LLM, requires 3+ episodes |
| 10 | Detect soul_friction (value vs reality blocks) | LLM, requires 3+ episodes |
| 11 | Detect emotion_loop (recurring emotional pattern) | LLM |
| 12 | Extract activities + time slots | LLM |
| 13 | Wire to memory graph (nodes, edges for values/conflicts) | Deterministic |
| 14 | Log pattern occurrences for crystallization | Deterministic |
| 15 | Generate embedding (1536 dims) | OpenAI |

| Writes to | What |
|-----------|------|
| `memory_episodic` | Daily episode with all computed vectors |
| `pattern_occurrences` | Raw pattern observations |
| `memory_nodes` / `memory_edges` | Soul signals, activity links |

**Confidence gates:**
- Soul conflict/friction: 0.6+ confidence required
- Emotion loop: 0.65+ confidence required
- Requires 2+ journals in day window to consolidate

### Worker 3: preference_learning (3 phases)

**Files:** `runner.py` → `preference_learning.py`, `feedback.py`, `pattern_learning.py`

#### Phase 1: Preference Extraction

**Trigger:** Text contains "I like", "I prefer", "I hate", etc. (min 15 chars)

LLM extracts preferences by domain (food, wellness, social, environment) with dimensions (spiciness, noise level, formality) and values (-1.0 hate to +1.0 love).

| Writes to | What |
|-----------|------|
| `preferences` | Updated preference profile |
| `preference_events` | Audit log of what was learned |

#### Phase 2: Feedback Extraction

**Trigger:** "too spicy", "loved it", "that was perfect", etc.

Maps user reaction to the recommendation that triggered it. Closes the loop: recommendation → user reaction → preference adjustment.

| Writes to | What |
|-----------|------|
| `recommendation_feedback` | Feedback record (type, rating, affected dimensions) |
| `preferences` | Updated via `apply_feedback_to_preferences()` |

#### Phase 3: Pattern Learning

**File:** `sakhi/apps/api/services/ayurveda/pattern_learning.py`

LLM extracts behaviors and symptoms from text:

- **Behaviors:** `{type, name, intensity, dosha_effect, direction}`
  - Example: `{name: "late_dinner", dosha_effect: "vata", direction: "aggravates"}`
- **Symptoms:** `{type, name, severity, likely_dosha}`
  - Example: `{name: "anxiety", severity: 0.8, likely_dosha: "vata"}`

**Pattern detection:** Looks back 48 hours from each symptom for preceding behaviors. If `behavior.dosha_effect == symptom.likely_dosha AND direction == "aggravates"` → pattern detected.

| Writes to | What |
|-----------|------|
| `behavior_log` | Each extracted behavior |
| `symptom_log` | Each extracted symptom |
| `personal_patterns` | Detected cause→effect patterns (upserted) |

**Pattern confidence growth (logarithmic):**

| Observations | Confidence | Strength |
|-------------|------------|----------|
| 1st | 0.30 | 0.50 |
| 3rd | 0.53 | 0.64 |
| 7th | 0.64 | 0.79 |
| 12th | 0.74 | 0.87 |

Formula:
```
strength  = min(0.95, 0.5 + 0.15 * log(observation_count))
confidence = min(0.9, 0.3 + 0.1 * log(observation_count))
```

---

## Phase 3: Scheduled Workers

### Daily Workers

| Time (UTC) | Worker | What it does |
|------------|--------|-------------|
| 3 AM | Pattern Crystallization (daily) | `pattern_occurrences` → `crystallized_patterns` (frequency & recurrence focus) |
| 4 AM | Emotion-Soul-Rhythm sync | ESR state refresh, emotion loop refresh |
| 5 AM | Rhythm rollup | Deterministic capacity patterns |
| 6 AM | Identity momentum | Track identity evolution patterns |
| 6 AM | Ayurvedic pipeline | Dosha state computation from episodes |
| 6 AM | Soul refresh | Prakruti state refresh |
| 6 AM | Rhythm-soul deep sync | Circadian-identity alignment |
| 6 AM | Task weaver | Auto-prioritize tasks |
| 6 AM | Theme uprank | Crystallized patterns → theme promotion |
| 7 AM | Intent decay | Prevent stale intents |
| 7 AM | Forecast refresh + nudge check | Predict next day's energy/mood |

**Daily reflective jobs:** daily_reflection, persona_updater, persona_mode_detector, tone_continuity, reflective_loop, life_phase_mapper, reinforcement_calibration, meta_reflection

**Daily presence jobs:** outreach, morning_presence, rhythm_nudge, evening_state_summary, inactive_user_check

### Weekly Workers (Mondays)

| Time (UTC) | Worker | What it does |
|------------|--------|-------------|
| 3 AM | Weekly signals | Language-free signals aggregation |
| 4 AM | Pattern crystallization (weekly) | Trajectory + consistency focus |
| 5 AM | Rhythm rollup weekly | Weekly energy/focus patterns |
| 6 AM | Longitudinal learning | Episodes → `longitudinal_state` |
| 8 AM | Goal evolver | Goals vs reflections alignment |
| 8 AM | Rhythm-soul weekly | Deep rhythm-soul sync |

**Sunday:** Theme inference, theme-rhythm correlation links

### Monthly Workers (1st of month)

| Time (UTC) | Worker | What it does |
|------------|--------|-------------|
| 5 AM | Pattern crystallization (monthly) | Identity + traits focus. Promotes patterns to identity-level traits |

---

## How the Personal Graph Gets Built

Each layer feeds the next. Data flows **upward** from raw events to high-level intelligence:

```
Layer 6: CONVERSATION PROMPT
         ┌────────────────────────────────────────────────────────┐
         │ 360° Context Scan + Tier 2 Deep Sections               │
         │ + Personalized Recommendations                         │
         │ + Causal Explanation ("why you feel this")              │
         └─────────────────────────┬──────────────────────────────┘
                                   │ reads from

Layer 5: PERSONALIZED INTELLIGENCE
         ┌────────────────────────────────────────────────────────┐
         │ Recommendations (KG + personal patterns + effectiveness)│
         │ Causal Reasoning (patterns + behaviors + seasonal)      │
         │ Last-Time Lookup (symptom_log + episodic memory)        │
         │ Rhythm Forecasts (predicted energy/mood)                │
         │ Identity Momentum (growth trajectory)                   │
         └─────────────────────────┬──────────────────────────────┘
                                   │ reads from

Layer 4: CRYSTALLIZED KNOWLEDGE
         ┌────────────────────────────────────────────────────────┐
         │ personal_patterns    (cause→effect, observation_count)  │
         │ crystallized_patterns (high-confidence promoted)        │
         │ preferences          (learned likes/dislikes)           │
         │ persona_traits       (personality dimensions)           │
         │ soul_values          (core values + evidence)           │
         │ longitudinal_state   (long-term trends)                 │
         └─────────────────────────┬──────────────────────────────┘
                                   │ built from

Layer 3: EPISODIC SUMMARIES
         ┌────────────────────────────────────────────────────────┐
         │ memory_episodic       (daily episodes)                  │
         │   soul, soul_shadow, soul_light, soul_conflict          │
         │   emotional_state, rhythm_state                         │
         │   state_vector (vata/pitta/kapha)                       │
         │   guna_vector (sattva/rajas/tamas)                      │
         │   emotion_loop                                          │
         │ memory_weekly_summaries / monthly_recaps                │
         │ memory_nodes + memory_edges (semantic graph)            │
         └─────────────────────────┬──────────────────────────────┘
                                   │ consolidated from

Layer 2: RAW BEHAVIORAL DATA
         ┌────────────────────────────────────────────────────────┐
         │ behavior_log         (skipped_breakfast, meditation)    │
         │ symptom_log          (anxiety, fatigue, brain_fog)      │
         │ recommendation_feedback (thumbs up/down on suggestions) │
         │ intervention_outcomes (what actually helped)            │
         │ intervention_checkins (did user follow through)         │
         │ preference_events    (explicit preference changes)      │
         └─────────────────────────┬──────────────────────────────┘
                                   │ extracted from

Layer 1: RAW INPUT
         ┌────────────────────────────────────────────────────────┐
         │ journal_entries      (user's text + voice transcripts)  │
         │ journal_embeddings   (1536-dim vectors)                 │
         │ journal_emotions     (detected emotion)                 │
         │ journal_topics       (extracted topics)                 │
         │ conversation_turns   (full dialogue history)            │
         │ email_events         (email metadata)                   │
         │ email_signals        (inbox patterns)                   │
         │ memory_short_term    (14-day working memory)            │
         └────────────────────────────────────────────────────────┘
```

---

## How Recommendations Use Personal Data

### Step 1: Context Builder

**File:** `sakhi/apps/api/services/recommendations/context_builder.py`

Reads 6 data sources to build `RecommendationContext`:

| Data Source | Table | What |
|-------------|-------|------|
| Prakruti (constitution) | `personal_model.operating_system` | Baseline dosha percentages (e.g., Vata 60%, Pitta 30%, Kapha 10%) |
| Vikriti (current state) | Computed via `compute_current_vikriti()` | Current imbalance + drift % from baseline |
| Seasonal context | `get_current_season()` | Season + amplification factor (winter → Vata +1.2x) |
| Personal patterns | `personal_patterns` | User's cause→effect correlations (e.g., "late_dinner → scattered", 0.8 correlation) |
| Recent behaviors | `behavior_log` (48h window) | What user has been doing (worked late, skipped gym) |
| Historical effectiveness | `recommendation_feedback` | What foods/practices worked or didn't (warm milk: effective 5x, raw salad: ineffective 3x) |

**Output:**
```python
RecommendationContext(
    constitution=ConstitutionContext(type="vata_primary", vata=0.6, pitta=0.3, kapha=0.1),
    current_state=CurrentStateContext(friction_state="Chaos", drift_percentage=35),
    temporal=TemporalContext(season="winter", amplification=1.2),
    personal_patterns=[5 patterns with correlation > 0.5],
    recent_activities=[worked late, skipped gym],
    historical_effectiveness=HistoricalEffectiveness(effective=["warm_milk"], ineffective=["raw_salad"]),
    urgency_level="high",                # 35% drift
    personalization_confidence=0.72,      # Enough data to personalize strongly
)
```

**Confidence scoring:**
```
confidence = (pattern_score * 0.4) + (activity_score * 0.3) + (feedback_score * 0.3)
           = min(0.95, max(0.3, confidence))
```

**Urgency levels:**

| Drift % | Urgency |
|---------|---------|
| 40%+ | Critical |
| 25-39% | High |
| 10-24% | Normal |
| <10% | Low |

### Step 2: Recommendation Generator

**File:** `sakhi/apps/api/services/recommendations/generator.py`

Queries the Ayurvedic knowledge graph (`ay_nodes` + `ay_edges`) for the target dosha:

```sql
SELECT n.name, n.display_name, n.attrs, n.citations, e.weight
FROM ay_nodes n
JOIN ay_edges e ON n.id = e.src
JOIN ay_nodes d ON e.dst = d.id
WHERE n.kind = 'food' AND d.name = 'vata' AND e.rel = 'PACIFIES'
ORDER BY e.weight DESC
```

Then scores each recommendation on **6 factors**:

| Factor | Effect | When |
|--------|--------|------|
| Base knowledge graph weight | 0.7 (typical) | Always |
| Personal effectiveness | +0.2 | User tried & liked before |
| Personal ineffectiveness | -0.3 | User avoided before |
| Pattern relevance | +0.05 per | Per strong pattern (correlation > 0.6) |
| Time-of-day match | +0.1 | Matches current time window |
| Season match | +0.1 / -0.05 | Matches or conflicts with season |
| Urgency amplifier | x1.2 (critical) / x1.1 (high) | Final multiplier |

**Example:**
```
"warm milk" = 0.7 (base) + 0.2 (personal effective) + 0.1 (evening match) = 1.0 → capped at 0.95
"raw salad" = 0.7 (base) - 0.3 (personal ineffective) = 0.4 → filtered out
```

### Step 3: Causal Reasoning

**File:** `sakhi/apps/api/services/ayurveda/causal_reasoning.py`

Answers "why am I feeling [X]?" using 4 sources:

| Source | How |
|--------|-----|
| `personal_patterns` | Direct cause→effect matches (e.g., "late_dinner → scattered", 0.8 correlation) |
| `behavior_log` (48h) | Recent behaviors whose dosha_effect matches symptom's dosha |
| Seasonal influence | `get_seasonal_amplification(dosha)` — winter amplifies Vata |
| Ayurvedic knowledge graph | General causes from `ay_edges` WHERE rel IN ('AGGRAVATES', 'CAUSES') |

**Output:** Natural language explanation (no LLM call — synthesized deterministically):
> "You're experiencing elevated Vata energy. Based on your patterns: late dinners tend to increase scattered feeling for you (observed 5 times). Contributing: recent late work nights. Winter naturally amplifies Vata sensitivity."

### Step 4: Prompt Integration

**File:** `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py`

The trigger type determines how recommendations are framed in the prompt:

| Trigger | Framing | When |
|---------|---------|------|
| **Reactive** | "Here are personalized suggestions" — share directly | User explicitly asked |
| **Proactive** | "Gently weave in 1-2 suggestions" | High friction detected (drift > 25%) |
| **Contextual** | "Mention one if natural" | Good moment (morning, evening) |
| **Nudge** | "Only if it feels right" | Moderate drift (15-25%) |

---

## Key Tables Summary

| Layer | Tables | Written by | Read by |
|-------|--------|------------|---------|
| **Master State** | `personal_model` (50+ JSONB columns) | Every worker | Every turn |
| **Raw Input** | `journal_entries`, `journal_embeddings`, `conversation_turns` | Turn handler | Workers, memory recall |
| **Working Memory** | `memory_short_term` (14-day TTL) | turn_memory_update | Conversation engine |
| **Episodes** | `memory_episodic` (daily summaries + state vectors) | episodic_consolidation | Causal reasoning, recommendations |
| **Semantic Graph** | `memory_nodes`, `memory_edges` | episodic_consolidation | Context builder |
| **Behaviors** | `behavior_log` | preference_learning (Phase 3) | Causal reasoning, context builder |
| **Symptoms** | `symptom_log` | preference_learning (Phase 3) | Causal reasoning, last-time lookup |
| **Patterns** | `personal_patterns` | preference_learning (Phase 3) | Recommendations, causal reasoning |
| **Preferences** | `preferences`, `preference_events` | preference_learning (Phase 1) | Recommendation scoring |
| **Feedback** | `recommendation_feedback` | preference_learning (Phase 2) | Recommendation scoring (+/- boost) |
| **Interventions** | `intervention_plans`, `intervention_outcomes` | Learning service | Last-time lookup |
| **Email** | `email_events`, `email_signals`, `email_digests` | Email sync worker | Conversation (email module) |
| **Knowledge Graph** | `ay_nodes`, `ay_edges` (NOT personal) | Migration/seed | Recommendation generator |
| **Rhythm** | `rhythm_forecasts`, `rhythm_insights` | Daily forecast worker | Conversation, scheduling |
| **Crystallized** | `crystallized_patterns` | Daily/weekly/monthly workers | Long-term identity |

---

## The Flywheel: How Each Turn Makes the Next Better

```
Turn N:   User says "I skipped breakfast and feel scattered"
          → behavior_log: "skipped_breakfast" (vata, aggravates)
          → symptom_log: "scattered" (vata)
          → personal_patterns: "skipped_breakfast → scattered" (obs=1, conf=0.3)
          → Response: General Ayurvedic advice about Vata

Turn N+3: User says "Feeling scattered again, had a late dinner"
          → behavior_log: "late_dinner" (vata, aggravates)
          → symptom_log: "scattered" (vata)
          → personal_patterns updated:
              "skipped_breakfast → scattered" (obs=2, conf=0.43)
              "late_dinner → scattered" (obs=1, conf=0.3)
          → Response: "I notice a pattern — both late meals and
            skipped meals seem to trigger this for you"

Turn N+7: User says "I'm scattered"
          → personal_patterns now has 5+ observations
          → Causal reasoning: "Late/irregular meals → scattered
            (high confidence)"
          → Recommendation: warm oats scored 0.95
            (personal + seasonal boost)
          → Response: "Your pattern shows irregular eating triggers
            this. Try warm oats tomorrow morning — that's worked
            well for you. Winter makes Vata sensitivity higher."

Week 4:   Pattern crystallized → identity-level trait:
          "Meal regularity is a key factor in your Vata stability"
          → Proactive morning nudge: "Good morning! Don't skip
            breakfast today — your pattern data shows it matters."
```

---

## Environment Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `SAKHI_DISABLE_QUEUE` | `1` (dev) | `1` = run workers inline (required on macOS dev). `0` = enqueue to Redis/RQ |
| `SAKHI_CONVERSATION_RECENT_LIMIT` | 8 | Verbatim recent turns in context |
| `SAKHI_CONVERSATION_COMPRESS_THRESHOLD` | 16 | When to compress older context |
| `SAKHI_USE_ADAPTIVE_RESPONSE` | `1` | Enable adaptive response pipeline |
| `MODEL_CONVERSATION` | `gpt-4o-mini` | LLM model for conversation |
| `TURN_JOBS_QUEUE` | `turn_updates` | RQ queue name |
| `TURN_JOBS_TIMEOUT` | 300 | Job timeout (seconds) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for job queues |

---

## Key Source Files

| File | Purpose |
|------|---------|
| `sakhi/apps/api/routes/turn_v2.py` | Main turn handler (synchronous pipeline) |
| `sakhi/apps/api/services/context_router.py` | Context module router (tier 1 vs tier 2) |
| `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` | Prompt builder (context scan + tier 2 sections) |
| `sakhi/apps/api/services/conversation_v2/conversation_engine.py` | LLM call orchestration |
| `sakhi/apps/worker/pipelines/turn_updates/runner.py` | Per-turn worker dispatcher |
| `sakhi/apps/worker/tasks/episodic_consolidation_v21.py` | Episodic memory consolidation (1379 lines) |
| `sakhi/apps/api/services/memory/preference_learning.py` | Preference extraction |
| `sakhi/apps/api/services/learning/feedback.py` | Feedback loop |
| `sakhi/apps/api/services/ayurveda/pattern_learning.py` | Behavior/symptom extraction + pattern detection |
| `sakhi/apps/api/services/ayurveda/causal_reasoning.py` | "Why am I feeling X?" engine |
| `sakhi/apps/api/services/recommendations/context_builder.py` | Recommendation context aggregation |
| `sakhi/apps/api/services/recommendations/generator.py` | Knowledge graph scoring + ranking |
| `sakhi/apps/api/services/ayurveda/food_recommendations.py` | Dosha-specific food profiles |
| `sakhi/apps/worker/scheduler.py` | Daily/weekly/monthly worker scheduling |
| `sakhi/apps/api/services/ingestion/unified_ingest.py` | Memory ingestion pipeline |
