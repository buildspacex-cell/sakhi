# Kala - API Design

> The developer experience: what it looks like to use Kala.

---

## Design Principle

**20 lines to temporal awareness.** A developer should go from "my agent has no memory" to "my agent understands temporal state" in under 20 lines of meaningful code.

The API should feel like a natural extension of how you already build agents, not a new paradigm to learn.

---

## Quick Start: The 20-Line Experience

```python
import kala

# Initialize Kala with a PostgreSQL backend
engine = kala.Engine(database_url="postgresql://...")

# Define your entity (a user, a customer, a process — anything)
entity = await engine.entity("user-123")

# Set a baseline (what "normal" looks like)
await entity.set_baseline({
    "energy": 0.7,
    "focus": 0.6,
    "stress": 0.3,
    "motivation": 0.8
})

# Record observations over time
await entity.observe("Felt really scattered today, couldn't focus on anything")

# Later... record more
await entity.observe("Had a great workout, feeling energized but still anxious about the deadline")

# Ask: how are they doing relative to their baseline?
drift = await entity.drift()
# DriftResult(percentage=28.5, severity="moderate", primary="focus", direction="depleted")

# Get temporal context for an LLM call
context = await entity.context("How should I prioritize my day?")
# Returns structured temporal state: baseline, current, drift, recent memories, patterns

# Build your prompt with temporal awareness
messages = [
    {"role": "system", "content": f"User context:\n{context.summary}"},
    {"role": "user", "content": "How should I prioritize my day?"}
]
```

That's it. Your agent now knows what's normal for this user, what's different right now, and what patterns have emerged over time.

---

## Core API Surface

### Engine

The entry point. Manages database connections and configuration.

```python
engine = kala.Engine(
    database_url="postgresql://...",
    embedding_fn=my_embedding_function,       # Optional: custom embedding function
    embedding_dim=1536,                       # Embedding dimensionality
)

# Setup: create tables if they don't exist
await engine.setup()

# Get or create an entity
entity = await engine.entity("user-123")

# List all entities
entities = await engine.list_entities()

# Shutdown cleanly
await engine.close()
```

**`embedding_fn`**: Kala needs vectors for recall and similarity. By default it expects an async function `(text: str) -> List[float]`. If not provided, Kala uses a lightweight local model or raises an error.

---

### Entity

Represents anything you're tracking over time — a person, a customer, a workflow, a process.

```python
entity = await engine.entity("user-123")

# Identity
entity.id          # "user-123"
entity.created_at  # When first observed
entity.age_days    # Days since first observation
```

---

### Baseline & State

```python
# Set baseline (immutable reference — what "normal" looks like)
await entity.set_baseline({
    "energy": 0.7,
    "focus": 0.6,
    "stress": 0.3,
    "motivation": 0.8
})

# Get baseline
baseline = await entity.baseline()
# Baseline(dimensions={"energy": 0.7, ...}, source="explicit", computed_at=...)

# Get current state (windowed aggregation with decay)
current = await entity.current_state(window_days=7)
# CurrentState(dimensions={"energy": 0.5, ...}, confidence=0.75, observation_count=12)

# Get drift (deviation from baseline)
drift = await entity.drift()
# DriftResult(
#     percentage=28.5,
#     severity="moderate",
#     primary_contributor="focus",
#     direction="depleted",
#     per_dimension={"energy": -0.15, "focus": -0.25, "stress": +0.10, "motivation": -0.05},
#     confidence=0.75
# )

# Configure drift detection
drift = await entity.drift(
    distance_metric="euclidean",     # or "cosine", "manhattan"
    severity_thresholds=[15, 25, 40] # minimal/mild/moderate/significant boundaries
)
```

---

### Observation & Memory

```python
# Record an observation (the primary input to Kala)
await entity.observe(
    "Had a terrible night's sleep, woke up at 3am and couldn't fall back asleep",
    timestamp=datetime.now(),        # Optional: defaults to now
    source="journal",                # Optional: categorize the source
    metadata={"mood": "anxious"}     # Optional: structured metadata
)

# Record with explicit state dimensions (when you have structured data)
await entity.observe(
    "Morning health check",
    dimensions={"energy": 0.3, "stress": 0.8},   # Direct state measurement
    source="wearable"
)

# Recall relevant memories
memories = await entity.recall(
    "Why am I so tired lately?",
    k=5,                             # Number of results
    recency_halflife_days=45,        # Temporal decay half-life
)
# [Memory(text="Had terrible sleep...", age_days=2, relevance=0.89), ...]

# Get recent observations
recent = await entity.recent(days=7)
# [Observation(text="...", timestamp=..., source="journal"), ...]

# "Last time" queries
result = await entity.last_time("exercised")
# LastTimeResult(found=True, when=datetime(...), days_ago=4, context="Went for a 30min run")
```

---

### Patterns

```python
# Register a pattern extractor (domain-specific)
@entity.pattern_extractor
async def extract_behaviors_and_effects(text: str):
    """Extract causes and effects from observation text."""
    # Use LLM, regex, NLP — whatever works for your domain
    return {
        "causes": [("behavior", "skipped_lunch"), ("behavior", "worked_late")],
        "effects": [("symptom", "afternoon_fatigue"), ("symptom", "irritability")]
    }

# Patterns are learned automatically from observations
# After sufficient observations, query them:
patterns = await entity.patterns()
# [TemporalPattern(
#     cause=("behavior", "skipped_lunch"),
#     effect=("symptom", "afternoon_fatigue"),
#     observation_count=7,
#     confidence=0.78,
#     first_observed_at=...,
#     last_observed_at=...
# ), ...]

# Query specific patterns
patterns = await entity.patterns(cause_type="behavior", min_confidence=0.6)
```

---

### Signals

```python
# Register an event source
source = entity.event_source("email")

# Record events from the source
await source.record(kala.Event(
    event_id="msg-456",
    timestamp=datetime.now(),
    direction="incoming",
    participants=[{"name": "Alice", "id": "alice@co.com"}],
    metadata={"subject": "Q4 Planning", "thread_id": "thread-789"}
))

# Register signal detectors (or use built-in ones)
source.add_detector(kala.detectors.RhythmDetector(window_days=90))
source.add_detector(kala.detectors.TrendDetector(period_days=7))
source.add_detector(kala.detectors.LoadDetector(period_days=7))

# Extract signals
signals = await source.extract()
# {
#     "rhythm": [RhythmSignal(group="alice@co.com", cadence="daily", confidence=0.85), ...],
#     "trend": TrendResult(direction="worsening", delta=0.15, ...),
#     "load": LoadResult(score=0.65, risk="moderate", active_count=15, ...)
# }

# Custom detector
class MyDetector(kala.Detector):
    def detect(self, events: List[kala.Event]) -> Any:
        # Your custom signal extraction logic
        pass

source.add_detector(MyDetector())
```

---

### Context (for LLM calls)

```python
# Get assembled temporal context for an LLM call
context = await entity.context(
    query="How should I prioritize today?",
    modules=None,          # Auto-route based on query, or specify: ["state", "memory", "signals"]
)

# context.summary — Human-readable summary for system prompt injection
# context.baseline — Baseline state
# context.current — Current state with confidence
# context.drift — Drift result
# context.memories — Relevant recalled memories
# context.patterns — Active patterns
# context.signals — Recent signal extractions
# context.session — Session continuity summary

# Use in your LLM call
messages = [
    {"role": "system", "content": f"""You are a helpful assistant.

User temporal context:
{context.summary}

Active patterns:
{context.patterns_summary}

Recent drift: {context.drift.severity} ({context.drift.percentage:.0f}% from baseline,
primary: {context.drift.primary_contributor} {context.drift.direction})
"""},
    {"role": "user", "content": user_message}
]

response = await llm.chat(messages)
```

---

### Sessions

```python
# Manage conversation continuity
session = await entity.session(slug="planning")

# Record turns
await session.turn("user", "I've been feeling overwhelmed with work")
await session.turn("assistant", "I can see from your recent patterns that...")

# Get session summary (compressed older turns)
summary = await session.summary()

# Find best session for a query
best = await entity.best_session("How's my project going?")
# Matches by semantic similarity + recency boost
```

---

## Timeline API (Testing)

### Define a Persona

```python
import kala.timeline as timeline

# From code
persona = timeline.Persona(
    id="burned-out-manager",
    name="Jordan",
    baseline={"energy": 0.7, "focus": 0.6, "stress": 0.3, "motivation": 0.8},
    traits=[
        timeline.Trait("perfectionist", intensity=0.8),
        timeline.Trait("people-pleaser", intensity=0.7),
    ],
    life_context=timeline.LifeContext(
        occupation="Engineering Manager",
        challenges=["too many direct reports", "launch deadline in 3 weeks"]
    ),
    arc=timeline.Arc(phases=[
        timeline.Phase(
            name="building_pressure",
            emotional_state="driven but stretched thin",
            duration_days=14,
            state_shift={"stress": +0.2, "energy": -0.1},
            themes=["deadline pressure", "skipping lunch", "late nights"],
        ),
        timeline.Phase(
            name="breaking_point",
            emotional_state="exhausted and overwhelmed",
            duration_days=10,
            state_shift={"stress": +0.3, "energy": -0.3, "focus": -0.2},
            themes=["can't concentrate", "snapping at team", "insomnia"],
        ),
        timeline.Phase(
            name="recovery",
            emotional_state="intentionally slowing down",
            duration_days=14,
            state_shift={"stress": -0.15, "energy": +0.1},
            themes=["delegating", "setting boundaries", "taking walks"],
        ),
    ]),
    checkpoints=[
        timeline.Checkpoint(day=14, assertions={
            "drift_state": {"severity_in": ["moderate", "significant"]},
            "theme_emerged": {"keywords": ["deadline", "pressure"], "min_occurrences": 3},
        }),
        timeline.Checkpoint(day=24, assertions={
            "drift_state": {"severity": "significant"},
            "pattern_learned": {"cause": "late_night", "effect": "poor_focus", "min_count": 2},
        }),
        timeline.Checkpoint(day=38, assertions={
            "drift_direction": {"dimension": "stress", "direction": "depleted"},
        }),
    ]
)

# Or from YAML
persona = timeline.Persona.from_yaml("personas/burned-out-manager.yaml")
```

### Run a Simulation

```python
# Create the harness
harness = timeline.Harness(
    engine=engine,
    persona=persona,
    entry_generator=my_llm_entry_generator,  # Function that generates synthetic entries
    worker_fn=my_process_observation,         # Your per-observation pipeline
    daily_worker_fn=my_daily_aggregation,     # Your daily aggregation pipeline (optional)
    snapshot_interval=7,                       # Capture state every 7 days
    daily_worker_interval=3,                   # Run daily workers every 3 simulated days
)

# Setup test entity
user_id = await harness.setup()

# Run the simulation
result = await harness.run(max_days=38)

# Check results
print(f"Simulated {result.total_days} days, {result.total_entries} entries")
print(f"Snapshots: {len(result.snapshots)}")
print(f"All checkpoints passed: {result.all_checkpoints_passed}")

# Inspect evolution
for snapshot in result.snapshots:
    drift = snapshot.drift_state
    print(f"Day {snapshot.day}: drift={drift['percentage']:.0f}% ({drift['severity']})")

# Day 1:  drift=5%  (minimal)
# Day 7:  drift=18% (mild)
# Day 14: drift=31% (moderate)    ← checkpoint: moderate ✓
# Day 21: drift=45% (significant)
# Day 24: drift=48% (significant) ← checkpoint: significant ✓, pattern learned ✓
# Day 31: drift=35% (moderate)    ← recovery starting
# Day 38: drift=22% (mild)        ← checkpoint: stress depleted ✓

# Export for visualization
result.save("simulation_output.json")

# Cleanup test data
await harness.cleanup()
```

### In pytest

```python
import pytest
import kala.timeline as timeline

@pytest.mark.asyncio
async def test_burnout_detection():
    engine = kala.Engine(database_url=TEST_DB_URL)
    persona = timeline.Persona.from_yaml("personas/burned-out-manager.yaml")

    harness = timeline.Harness(engine=engine, persona=persona, ...)
    await harness.setup()

    result = await harness.run(max_days=24)

    # Verify temporal understanding evolved correctly
    assert result.all_checkpoints_passed
    assert result.snapshots[-1].drift_state["severity"] == "significant"
    assert any(
        p.cause == ("behavior", "late_night") and p.confidence > 0.6
        for p in result.patterns
    )

    await harness.cleanup()
```

---

## Configuration

### Sensible Defaults

Kala ships with defaults that work for most use cases. Everything is overridable.

```python
engine = kala.Engine(
    database_url="postgresql://...",

    # Memory defaults
    memory=kala.MemoryConfig(
        stm_ttl_days=14,                    # Short-term memory expiry
        recency_halflife_days=45,           # Recall recency decay
        vector_weight=0.7,                  # Hybrid recall: vector proportion
        keyword_weight=0.3,                 # Hybrid recall: keyword proportion
        diversity_threshold=0.92,           # Max similarity between recall results
        graph_merge_threshold=0.93,         # Auto-merge nodes above this similarity
    ),

    # State defaults
    state=kala.StateConfig(
        current_window_days=7,              # Window for current state computation
        decay_lambda=0.5,                   # Exponential decay rate
        distance_metric="euclidean",        # Drift distance function
        severity_thresholds=[15, 25, 40],   # Drift severity boundaries
    ),

    # Signal defaults
    signals=kala.SignalConfig(
        cache_ttl_seconds=21600,            # 6 hours signal extraction cache
        rhythm_window_days=90,              # Cadence detection lookback
        trend_period_days=7,                # Trend comparison period
        load_period_days=7,                 # Load analysis window
    ),

    # Pattern defaults
    patterns=kala.PatternConfig(
        correlation_window_hours=48,        # Cause → effect time window
        min_observations=2,                 # Minimum co-occurrences
        confidence_fn="logarithmic",        # How confidence grows
    ),
)
```

### Per-Entity Overrides

```python
# Override defaults for a specific entity
entity = await engine.entity("user-123", config=kala.EntityConfig(
    state=kala.StateConfig(
        current_window_days=14,             # Longer window for this entity
        decay_lambda=0.3,                   # Slower decay
    )
))
```

---

## Extension Points

### Custom Embedding Function

```python
async def my_embeddings(text: str) -> List[float]:
    response = await openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

engine = kala.Engine(
    database_url="...",
    embedding_fn=my_embeddings,
    embedding_dim=1536,
)
```

### Custom Pattern Extractor

```python
@entity.pattern_extractor
async def extract_sales_patterns(text: str):
    """Domain-specific: extract sales behaviors and outcomes."""
    return {
        "causes": [("action", "cold_outreach"), ("action", "demo_scheduled")],
        "effects": [("outcome", "deal_advanced"), ("outcome", "ghosted")]
    }
```

### Custom Signal Detector

```python
class ResponseTimeDetector(kala.Detector):
    """Detect if response times are getting slower."""

    def __init__(self, threshold_hours=24):
        self.threshold_hours = threshold_hours

    def detect(self, events: List[kala.Event]) -> Dict:
        # Group by conversation, measure response gaps
        # Return trend analysis
        return {"avg_response_hours": 12.5, "trend": "worsening"}

source.add_detector(ResponseTimeDetector(threshold_hours=12))
```

### Custom State Dimensions

```python
# For a sales pipeline
await entity.set_baseline({
    "deal_velocity": 0.6,
    "engagement_quality": 0.7,
    "pipeline_coverage": 0.8,
    "win_rate": 0.35,
})

# For a customer health score
await entity.set_baseline({
    "product_usage": 0.7,
    "support_sentiment": 0.8,
    "feature_adoption": 0.5,
    "nps_likelihood": 0.75,
})

# For a codebase health tracker
await entity.set_baseline({
    "test_coverage": 0.82,
    "build_stability": 0.95,
    "dependency_freshness": 0.7,
    "incident_rate": 0.1,
})
```

---

## Domain Examples

### Personal Wellness (Sakhi's domain)

```python
# Sakhi uses Kala with Ayurvedic dimensions
await entity.set_baseline({
    "vata": 0.45,       # Air/Space: creativity, anxiety, variability
    "pitta": 0.40,      # Fire/Water: drive, intensity, metabolism
    "kapha": 0.15,      # Earth/Water: stability, groundedness, inertia
})

# Sakhi's pattern extractor detects wellness behaviors → symptoms
@entity.pattern_extractor
async def extract_wellness(text):
    return {
        "causes": [("behavior", "irregular_sleep"), ("behavior", "skipped_meals")],
        "effects": [("symptom", "anxiety"), ("symptom", "fatigue")]
    }

# Sakhi maps drift to user-facing friction states
drift = await entity.drift()
if drift.primary_contributor == "vata" and drift.direction == "elevated":
    friction = "chaos"      # Scattered, anxious, overwhelmed
elif drift.primary_contributor == "pitta" and drift.direction == "elevated":
    friction = "intensity"  # Driven, irritable, burning out
elif drift.primary_contributor == "kapha" and drift.direction == "elevated":
    friction = "stagnation" # Stuck, sluggish, unmotivated
```

### Customer Success

```python
await entity.set_baseline({
    "product_usage": 0.7,
    "support_sentiment": 0.8,
    "feature_adoption": 0.5,
    "nps_likelihood": 0.75,
})

# Signal source: support tickets
source = entity.event_source("support")
source.add_detector(kala.detectors.TrendDetector(period_days=30))
source.add_detector(kala.detectors.LoadDetector(period_days=7))

# Check for churn risk (drift = declining engagement)
drift = await entity.drift()
if drift.severity in ("moderate", "significant") and drift.primary_contributor == "product_usage":
    alert_csm(f"Customer {entity.id} showing {drift.severity} usage decline")
```

### Sales Pipeline

```python
await entity.set_baseline({
    "deal_velocity": 0.6,
    "engagement_quality": 0.7,
    "pipeline_coverage": 0.8,
})

# Detect patterns: what actions lead to what outcomes
@entity.pattern_extractor
async def extract_sales_actions(text):
    return {
        "causes": [("action", "demo_delivered")],
        "effects": [("outcome", "deal_advanced")]
    }

# Over time, Kala learns: demo_delivered → deal_advanced (confidence: 0.82)
# And also: no_followup_7d → deal_stalled (confidence: 0.71)
```

### DevOps / Incident Response

```python
await entity.set_baseline({
    "deploy_success_rate": 0.95,
    "mean_time_to_recover": 0.2,     # Normalized: lower is better
    "alert_volume": 0.3,
    "change_failure_rate": 0.1,
})

# Signal source: alerts and incidents
source = entity.event_source("pagerduty")
source.add_detector(kala.detectors.LoadDetector(period_days=7))
source.add_detector(kala.detectors.RhythmDetector(window_days=30))

# Detect: is alert volume trending up?
signals = await source.extract()
if signals["trend"].direction == "worsening":
    # Alert volume increasing — something is degrading
    pass
```

---

## What Kala Does NOT Do

- **Orchestrate agents.** Kala provides temporal context. Your framework (LangChain, CrewAI, custom) decides what to do with it.
- **Call LLMs.** Kala structures context. You call your own LLM with it.
- **Define domain semantics.** Kala doesn't know what "energy" or "vata" means. Your domain layer defines the dimensions and what they mean.
- **Replace your database.** Kala uses PostgreSQL for its own state. Your application keeps its own data wherever it wants.
- **Do real-time streaming.** Kala works on observation-by-observation processing. It's designed for interactions (conversations, events, measurements), not continuous data streams.

---

## Package Structure

```
kala/
├── __init__.py              # Engine, Entity, Config exports
├── engine.py                # Engine: connection management, entity factory
├── entity.py                # Entity: the main developer interface
├── config.py                # Configuration dataclasses
│
├── memory/
│   ├── __init__.py
│   ├── short_term.py        # STM with TTL
│   ├── episodic.py          # Write-once episodes
│   ├── long_term.py         # EMA consolidation
│   ├── recall.py            # Hybrid retrieval
│   └── graph.py             # Associative graph
│
├── state/
│   ├── __init__.py
│   ├── baseline.py          # Immutable baseline
│   ├── current.py           # Windowed aggregation
│   ├── drift.py             # Deviation detection
│   ├── patterns.py          # Cause-effect learning
│   └── fusion.py            # Multi-source sensing
│
├── signals/
│   ├── __init__.py
│   ├── accumulator.py       # Event store + detector orchestration
│   ├── rhythm.py            # Cadence detection
│   ├── trend.py             # Period comparison
│   ├── load.py              # Capacity scoring
│   └── detectors.py         # Built-in detector implementations
│
├── awareness/
│   ├── __init__.py
│   ├── router.py            # Context module gating
│   ├── assembler.py         # Temporal context builder
│   └── session.py           # Conversation continuity
│
├── timeline/
│   ├── __init__.py
│   ├── harness.py           # Simulation engine
│   ├── persona.py           # Entity specification
│   ├── snapshot.py          # State capture
│   └── checkpoint.py        # Temporal assertions
│
├── storage/
│   ├── __init__.py
│   ├── base.py              # Abstract storage interface
│   └── postgresql.py        # PostgreSQL implementation
│
└── py.typed                 # PEP 561 type marker
```

---

*Last updated: 2026-02-20*
