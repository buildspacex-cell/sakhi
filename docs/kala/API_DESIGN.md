# Kala — API Reference

> Complete API reference for all public functions, classes, and constants.
> 46 source files, 547 tests, zero external dependencies.

---

## Governance Layer

The core of kala. Everything below this section is substrate that the governance layer builds on.

### Constraints (`kala/constraints/`)

Data-driven constraint evaluation. Constraints are **data** (serializable), not **code** (lambdas).

#### Data Types

```python
from kala.constraints import (
    Constraint,        # Frozen dataclass — a single rule
    ConstraintSet,     # Mutable collection of constraints
    Violation,         # Frozen dataclass — a failed check
    Verdict,           # Frozen dataclass — the evaluation result
    PRIORITY_SOFT,     # 1
    PRIORITY_MEDIUM,   # 2
    PRIORITY_HARD,     # 3
)
```

**`Constraint`** — A single evaluable rule.

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique identifier |
| `constraint_type` | `str` | Category: `time_boundary`, `value_alignment`, `drift_threshold`, `commitment`, `capacity`, `custom` |
| `field` | `str` | Dotted path into action_context (e.g., `"proposed_hour"`, `"drift.drift_percentage"`) |
| `operator` | `str` | One of 11 operators (see below) |
| `value` | `Any` | Expected value to compare against |
| `description` | `str` | Human-readable description |
| `source` | `str` | What created this constraint (e.g., `"objective:sleep-goal:v2"`) |
| `priority` | `int` | `PRIORITY_SOFT` (1), `PRIORITY_MEDIUM` (2), or `PRIORITY_HARD` (3) |
| `active` | `bool` | Whether this constraint is active (default `True`) |
| `metadata` | `dict` | Arbitrary extra data |

**`Violation`** — A constraint that failed.

| Field | Type | Description |
|---|---|---|
| `constraint` | `Constraint` | The constraint that was violated |
| `actual_value` | `Any` | The value that was found |
| `message` | `str` | Human-readable violation description |

**`Verdict`** — The result of evaluating all constraints.

| Field | Type | Description |
|---|---|---|
| `action` | `str` | `"allow"`, `"block"`, or `"confirm"` |
| `violations` | `tuple[Violation, ...]` | All violations found |

Static factories: `Verdict.allow()`, `Verdict.block(violations)`, `Verdict.confirm(violations)`.

**`ConstraintSet`** — Mutable collection with query methods.

```python
cs = ConstraintSet()
cs.add(constraint)
cs.remove("constraint-id")
cs.get("constraint-id")        # -> Constraint | None
cs.active()                     # -> list[Constraint] (active only)
cs.by_type("time_boundary")    # -> list[Constraint]
cs.by_priority(PRIORITY_HARD)  # -> list[Constraint]
len(cs)                         # number of constraints
```

#### Operators

11 comparison predicates available via `VALID_OPERATORS`:

| Operator | Meaning | Example |
|---|---|---|
| `lt` | Less than | `field < value` |
| `gt` | Greater than | `field > value` |
| `lte` | Less than or equal | `field <= value` |
| `gte` | Greater than or equal | `field >= value` |
| `eq` | Equal | `field == value` |
| `neq` | Not equal | `field != value` |
| `in` | In collection | `field in value` |
| `not_in` | Not in collection | `field not in value` |
| `between` | Between range | `value[0] <= field <= value[1]` |
| `contains` | Contains element | `element in field` |
| `not_contains` | Does not contain | `element not in field` |

```python
from kala.constraints import check, extract_field, VALID_OPERATORS

check("lte", 22, 23)           # True (22 <= 23)
check("between", 5, [1, 10])   # True (1 <= 5 <= 10)
check("in", "vata", ["vata", "pitta"])  # True

extract_field({"a": {"b": 3}}, "a.b")  # 3
extract_field({"dosha.trend_7d.vata": "rising"}, "dosha.trend_7d.vata")  # "rising" (flat key match)
```

#### Evaluation

```python
from kala.constraints import evaluate, evaluate_single

# Evaluate a single constraint
violation = evaluate_single(action_context, constraint)
# Returns Violation or None

# Evaluate all active constraints
verdict = evaluate(action_context, constraint_set)
# Returns Verdict(action="allow"|"block"|"confirm", violations=(...))
```

**Priority logic:** Hard violation → `block`. Any violation (no hard) → `confirm`. No violations → `allow`.

**Missing fields:** Hard constraint + missing field → violation. Soft/medium constraint + missing field → skip (no violation).

---

### Event Ledger (`kala/ledger/`)

Append-only event log with pluggable persistence.

```python
from kala.ledger import Event, Ledger, InMemoryBackend, LedgerBackend
```

**`Event`** — An immutable record of something that happened.

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique event identifier |
| `timestamp` | `datetime` | When it happened (UTC) |
| `entity_id` | `str` | Who/what it applies to |
| `event_type` | `str` | `proposed`, `validated`, `committed`, `rejected`, `reconciled`, `observed` |
| `action` | `str` | What was proposed/done (e.g., `"suggest_routine"`) |
| `actor` | `str` | `llm`, `user`, `system`, `crystallization`, `governance` |
| `data` | `dict` | Arbitrary payload |
| `reason` | `str` | Why this event happened |

**`Ledger`** — Main API for event storage and query.

```python
ledger = Ledger()                       # Uses InMemoryBackend
ledger = Ledger(backend=my_backend)     # Custom persistence

ledger.append(event)
events = ledger.query(entity_id="user-123")
events = ledger.query(entity_id="user-123", event_type="committed")
events = ledger.query(entity_id="user-123", after=some_datetime)
latest = ledger.latest(entity_id="user-123")
len(ledger)
```

**`LedgerBackend`** — ABC for persistence. Implement `append()` and `query()` for database-backed storage.

---

### Governance Gate (`kala/governance/gate.py`)

The single checkpoint. Merges 4 sources into one `GateDecision`.

```python
from kala.governance import GovernanceGate, GateDecision, Contradiction

gate = GovernanceGate(
    constraints=constraint_set,
    ledger=ledger,
    objectives=objective_store,   # Optional — enables staleness detection
)

decision = gate.evaluate(
    action_context={"proposed_hour": 23, "entity_id": "user-123"},
    drift_data={"drift_percentage": 30, "severity": "moderate"},  # Optional
)
# GateDecision(
#     action="block"|"require_confirmation"|"require_reconciliation"|"allow",
#     reasons=("...",),
#     triggers=("constraint"|"drift"|"contradiction",),
#     drift_data={...},
#     violations=(Violation(...),),
# )

decision.is_allowed       # True if action == "allow"
decision.is_blocked       # True if action == "block"
decision.requires_confirmation  # True if action in ("require_confirmation", "require_reconciliation")
```

**Strictest wins:** `block > require_reconciliation > require_confirmation > allow`

#### Contradiction Detection

```python
contradictions = gate.detect_contradictions(
    entity_id="user-123",
    proposed_action="suggest_routine",
    window=timedelta(hours=24),   # Optional lookback window
)
# [Contradiction(type="previously_rejected", event=Event(...), message="...")]
```

**5 contradiction types:**

| Type | What it detects |
|---|---|
| `previously_rejected` | Same action was rejected within time window |
| `contradicts_commitment` | Committed event conflicts with proposed action |
| `repetition_loop` | proposed → rejected → proposed cycle |
| `outdated_objective_version` | Constraint references stale objective version |
| `violates_recent_override` | Reserved (not yet implemented) |

#### Drift Gate

```python
from kala.governance import check_drift_gate, DEFAULT_DRIFT_THRESHOLDS

decision = check_drift_gate(
    drift_data={"drift_percentage": 30, "severity": "moderate"},
    thresholds=DEFAULT_DRIFT_THRESHOLDS,  # Optional
)
# DEFAULT_DRIFT_THRESHOLDS = {"block_proactive": 40.0, "require_confirmation": 25.0}
```

---

### Temporal Context (`kala/governance/temporal.py`)

Bridges Timeline data into the constraint pipeline.

```python
from kala.governance import TemporalContext

tc = TemporalContext()
tc.add_timeline("dosha", dosha_timeline)
tc.set_ledger(ledger)

ctx = tc.build({"proposed_hour": 22, "entity_id": "user-123"})
# ctx now includes:
#   "proposed_hour": 22
#   "entity_id": "user-123"
#   "dosha.latest.vata": 0.53
#   "dosha.moving_avg_7d.vata": 0.48
#   "dosha.moving_avg_14d.vata": 0.46
#   "dosha.trend_7d.vata": "rising"
#   "dosha.rate_7d.vata": 0.01
#   ... (same for pitta, kapha, and for 14d windows)
```

Constraints can then reference temporal features directly:

```python
Constraint(field="dosha.moving_avg_14d.vata", operator="lt", value=0.6)
Constraint(field="dosha.trend_7d.vata", operator="neq", value="rising")
```

---

### State Reducer (`kala/governance/state.py`)

Replays events into deterministic state. Pure function — same events always produce the same snapshot.

```python
from kala.governance import StateSnapshot, reduce, diff

snapshot = reduce(ledger, entity_id="user-123")
# StateSnapshot(
#     entity_id="user-123",
#     as_of=datetime(...),
#     active_commitments=("morning_meditation",),
#     pending_actions=("suggest_routine",),
#     rejected_actions=(),
#     active_constraints=(),
#     last_drift_severity="moderate",
#     version=5,
# )

# Compare two snapshots
changes = diff(before_snapshot, after_snapshot)
# {"active_commitments": {"added": ("evening_walk",), "removed": ()}, ...}
```

---

### Objective Versioning (`kala/objectives/`)

Versioned objectives with lineage and staleness detection.

```python
from kala.objectives import (
    ObjectiveVersion,
    ObjectiveStore,
    parse_objective_source,
    find_stale_constraints,
    invalidated_by,
    format_source,
)
```

**`ObjectiveVersion`** — Immutable snapshot of an objective at a specific version.

| Field | Type | Description |
|---|---|---|
| `objective_id` | `str` | Stable identity across versions |
| `version` | `int` | Monotonic: 1, 2, 3, ... |
| `timestamp` | `datetime` | When this version was created |
| `title` | `str` | Human-readable (e.g., "Sleep by 10pm") |
| `description` | `str` | Optional longer description |
| `data` | `dict` | Structured payload |
| `source` | `str` | What triggered this version (e.g., `"user_input"`, `"feedback"`) |
| `reason` | `str` | Why it changed (e.g., "10pm unrealistic on weekdays") |
| `parent_version` | `int \| None` | Which version this evolved from (`None` for v1) |

**`ObjectiveStore`** — Registry with version lineage.

```python
store = ObjectiveStore()
store.add(ObjectiveVersion(objective_id="sleep", version=1, title="Sleep by 10pm", ...))
store.add(ObjectiveVersion(objective_id="sleep", version=2, title="Sleep by 11pm",
                           parent_version=1, reason="10pm unrealistic on weekdays"))

store.current("sleep")          # -> ObjectiveVersion (v2)
store.get_version("sleep", 1)   # -> ObjectiveVersion (v1)
store.history("sleep")          # -> [v1, v2]
store.is_stale("sleep", 1)     # -> True (v1 < v2)
store.objectives()              # -> ["sleep"]
len(store)                      # -> 2
```

**Sequential enforcement:** Versions must be added in order (v1, v2, v3 — can't skip).

#### Staleness Detection

```python
# Source convention: "objective:{id}:v{n}"
format_source("sleep-goal", 2)                      # "objective:sleep-goal:v2"
parse_objective_source("objective:sleep-goal:v2")    # ("sleep-goal", 2)
parse_objective_source("onboarding")                 # None

# Find constraints referencing outdated objective versions
stale = find_stale_constraints(constraint_set, store)
# [(stale_constraint, current_version), ...]

# Find constraints invalidated by a new version
invalidated = invalidated_by(new_version, constraint_set)
# [constraint_for_old_version, ...]
```

---

## Substrate Layer

Temporal containers and extracted pure math that the governance layer builds on.

### Timeline (`kala/timeline/`)

The fundamental temporal primitive. Generic over `T`.

```python
from kala.timeline import Snapshot, Timeline
from kala.timeline.trend import detect_trend, moving_average, rate_of_change
from kala.timeline.reconcile import reconcile
```

**`Snapshot[T]`** — Timestamped observation with confidence and source.

| Field | Type | Description |
|---|---|---|
| `timestamp` | `datetime` | When observed |
| `value` | `T` | The observation (typically `dict[str, float]`) |
| `confidence` | `float` | 0.0–1.0 (default 1.0) |
| `source` | `str` | Where this came from (default `""`) |

**`Timeline[T]`** — Bisect-sorted sequence.

```python
tl = Timeline()
tl.add(Snapshot(timestamp=t1, value={"vata": 0.45}))
tl.add(Snapshot(timestamp=t2, value={"vata": 0.53}))

tl.latest()                  # Most recent snapshot
tl.earliest()                # Oldest snapshot
tl.at(t)                     # Snapshot at or before time t
tl.between(start, end)       # Snapshots in range
tl.window(timedelta(days=7)) # Last 7 days of snapshots
len(tl)                      # Number of snapshots
```

**Trend functions:**

```python
detect_trend(timeline, key="vata", window=timedelta(days=7))
# -> "rising" | "falling" | "stable"

moving_average(timeline, key="vata", window=timedelta(days=7))
# -> float

rate_of_change(timeline, key="vata", window=timedelta(days=7))
# -> float (per day)
```

**Reconciliation:**

```python
result = reconcile([timeline_a, timeline_b], strategy="confidence_weighted")
# Merged Timeline with confidence-weighted values from multiple sources
```

---

### State (`kala/state/`)

Pure drift and constitution math.

```python
from kala.state.drift import compute_baseline_drift, classify_severity, classify_friction_state
from kala.state.constitution import compute_constitution
from kala.state.dosha import compute_dosha_state
from kala.state.guna import compute_guna_state
```

**Drift:**

```python
result = compute_baseline_drift(
    prakruti={"vata": 0.45, "pitta": 0.40, "kapha": 0.15},
    vikriti={"vata": 0.60, "pitta": 0.35, "kapha": 0.05},
)
# {
#     "drift_percentage": 28.5,
#     "severity": "moderate",        # minimal | mild | moderate | significant
#     "primary_contributor": "vata",
#     "direction": {...},
# }

classify_severity(28.5)    # "moderate"
classify_friction_state(drift_result, vikriti)
# "chaos" | "intensity" | "stagnation" | "balanced"
```

---

### Pattern (`kala/pattern/`)

Pattern crystallization — when observations become confirmed patterns.

```python
from kala.pattern.thresholds import should_crystallize
from kala.pattern.trajectory import analyze_trajectory

should_crystallize(observations, threshold=0.7)
# True if accumulated confidence exceeds threshold

# Pattern strength decays without reinforcement
# Trajectory analysis tracks pattern direction over time
```

---

### Graph (`kala/graph/`)

In-memory graph construction for enrichment data.

```python
from kala.graph import create_node, create_edge, build_graph_from_enrichment
from kala.graph.schema import VALID_KINDS, VALID_RELATIONS, sanitize_kind, sanitize_relation

node = create_node(kind="theme", label="anxiety", data={"intensity": 0.8})
edge = create_edge(src=node_a, dst=node_b, relation="supports")
graph = build_graph_from_enrichment(enrichment_dict)
```

**13 valid kinds:** theme, goal, emotion, behavior, symptom, trigger, value, need, strength, obstacle, relationship, activity, context

**11 valid relations:** supports, blocks, triggers, soothes, amplifies, requires, conflicts_with, precedes, follows, co_occurs, part_of

---

### Decision (`kala/decision/`)

Fast deterministic decision scoring (<5ms).

```python
from kala.decision import compute_fast_decision_frame

frame = compute_fast_decision_frame(
    goals=[...],
    values=[...],
    intents=[...],
    tasks=[...],
    soul_state={...},
)
# frame.active_nodes, frame.micro_links, frame.friction_points, frame.energy_path
```

---

### Signals (`kala/signals/`)

Signal extraction from external data sources.

```python
from kala.signals.email.subscription import detect_subscription
from kala.signals.email.avoidance import detect_avoidance
from kala.signals.email.boundary import detect_boundary
from kala.signals.email.cognitive_load import detect_cognitive_load
from kala.signals.context_tags import extract_context_tags
```

---

### Context (`kala/context/`)

```python
from kala.context.classifier import classify_context
# Deterministic context routing based on input signals
```

---

### Memory (`kala/memory/`)

```python
from kala.memory.vector_math import cosine_similarity
# Vector similarity for embedding-based recall
```

---

### Adapters (`kala/adapters/`)

ABCs for external dependencies. kala defines the interfaces; consuming apps provide implementations.

```python
from kala.adapters.base import DatabaseAdapter, EmbeddingAdapter, LLMAdapter
```

| Adapter | Methods |
|---|---|
| `DatabaseAdapter` | `fetch()`, `fetch_one()`, `execute()` |
| `EmbeddingAdapter` | `embed()`, `embed_batch()` |
| `LLMAdapter` | `complete()` |

---

## End-to-End Example

A complete governance evaluation flow:

```python
from datetime import datetime, timedelta, UTC
from kala.constraints import Constraint, ConstraintSet, PRIORITY_HARD, PRIORITY_SOFT, evaluate
from kala.ledger import Event, Ledger
from kala.governance import GovernanceGate, TemporalContext
from kala.objectives import ObjectiveVersion, ObjectiveStore
from kala.objectives.staleness import format_source
from kala.timeline import Snapshot, Timeline

# 1. Build temporal state
dosha_timeline = Timeline()
dosha_timeline.add(Snapshot(
    timestamp=datetime.now(UTC) - timedelta(days=7),
    value={"vata": 0.45, "pitta": 0.40, "kapha": 0.15},
))
dosha_timeline.add(Snapshot(
    timestamp=datetime.now(UTC),
    value={"vata": 0.60, "pitta": 0.35, "kapha": 0.05},
))

tc = TemporalContext()
tc.add_timeline("dosha", dosha_timeline)

# 2. Define objective and constraints
store = ObjectiveStore()
store.add(ObjectiveVersion(
    objective_id="sleep", version=1,
    timestamp=datetime.now(UTC),
    title="Sleep by 10pm",
))

constraints = ConstraintSet()
constraints.add(Constraint(
    id="sleep-boundary",
    constraint_type="time_boundary",
    field="proposed_hour",
    operator="lte",
    value=22,
    description="Sleep by 10pm",
    source=format_source("sleep", 1),
    priority=PRIORITY_HARD,
))
constraints.add(Constraint(
    id="vata-check",
    constraint_type="drift_threshold",
    field="dosha.moving_avg_7d.vata",
    operator="lt",
    value=0.6,
    description="Vata should stay below 0.6",
    source="system",
    priority=PRIORITY_SOFT,
))

# 3. Build event history
ledger = Ledger()
ledger.append(Event(
    id="evt-1",
    timestamp=datetime.now(UTC) - timedelta(hours=2),
    entity_id="user-123",
    event_type="committed",
    action="evening_meditation",
    actor="user",
    data={},
    reason="User committed to evening meditation",
))

# 4. Evaluate a proposed action
gate = GovernanceGate(constraints=constraints, ledger=ledger, objectives=store)

action_context = tc.build({
    "proposed_hour": 23,
    "entity_id": "user-123",
    "proposed_action": "suggest_routine",
})

decision = gate.evaluate(
    action_context=action_context,
    drift_data={"drift_percentage": 30, "severity": "moderate"},
)

print(decision.action)       # "block" — proposed_hour 23 > 22 (hard constraint)
print(decision.violations)   # (Violation(constraint=sleep-boundary, actual=23, ...),)
print(decision.is_blocked)   # True
```

---

## Safety Guarantees

- **kala never imports sakhi.** Enforced by convention and verified in CI.
- **All code is pure computation.** No DB, no LLM, no I/O, no async, no network.
- **Frozen dataclasses.** Governance decisions, events, violations, snapshots, objective versions — all immutable.
- **Deterministic.** Same inputs always produce same outputs. State reducer is replayable.
- **Zero external dependencies.** Only Python stdlib. No numpy, no pydantic, no third-party libraries.
- **ABCs at boundaries.** `LedgerBackend`, `DatabaseAdapter` define persistence contracts without implementing I/O.

---

*Last updated: 2026-02-20*
