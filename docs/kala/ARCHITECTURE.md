# Kala — Architecture Reference

> Complete module reference for the kala governance kernel.
> 46 source files, 547 tests, zero external dependencies.

---

## Module Map

```
kala/
├── adapters/           # Phase 0 — External dependency interfaces
│   └── base.py              DatabaseAdapter, EmbeddingAdapter, LLMAdapter (ABCs)
│
├── signals/            # Phases 1, 6 — Signal extraction
│   ├── email/               Email intelligence detectors
│   │   ├── models.py             EmailEvent, SignalResult dataclasses
│   │   ├── subscription.py       Subscription/newsletter detection
│   │   ├── avoidance.py          Sender avoidance patterns
│   │   ├── boundary.py           Communication boundary signals
│   │   └── cognitive_load.py     Email overwhelm scoring
│   └── context_tags.py      Semantic context tag extraction
│
├── state/              # Phases 3, 6 — State computation
│   ├── drift.py             Drift math: compute_baseline_drift, classify_severity, classify_friction_state
│   ├── constitution.py      Constitution computation (Prakruti analysis)
│   ├── dosha.py             Dosha state engine (Vata/Pitta/Kapha scoring)
│   └── guna.py              Guna state engine (Sattva/Rajas/Tamas scoring)
│
├── context/            # Phase 2 — Context routing
│   └── classifier.py        classify_context() — deterministic context routing
│
├── memory/             # Phase 4 — Vector operations
│   └── vector_math.py       cosine_similarity, batch operations
│
├── timeline/           # Phase 7 — Temporal primitives
│   ├── core.py              Snapshot[T], Timeline[T] — generic temporal container
│   ├── trend.py             detect_trend, moving_average, rate_of_change
│   └── reconcile.py         Multi-source reconciliation with confidence weighting
│
├── pattern/            # Phase 8 — Pattern crystallization
│   ├── thresholds.py        should_crystallize, confidence scoring, decay
│   └── trajectory.py        Pattern trajectory analysis
│
├── graph/              # Phase 9 — Graph primitives
│   ├── core.py              create_node, create_edge, build_graph_from_enrichment, reason_about_graph
│   └── schema.py            VALID_KINDS, VALID_RELATIONS, sanitize_kind, sanitize_relation
│
├── decision/           # Phase 9 — Decision scoring
│   └── scoring.py           compute_fast_decision_frame — <5ms deterministic scoring
│
├── constraints/        # Phase 10 — Constraint engine
│   ├── operators.py         VALID_OPERATORS, check(), extract_field() — 11 comparison predicates
│   ├── core.py              Constraint, Violation, Verdict, ConstraintSet
│   └── evaluator.py         evaluate(), evaluate_single() — deterministic evaluation
│
├── ledger/             # Phase 11 — Event ledger
│   └── core.py              Event, Ledger, LedgerBackend (ABC), InMemoryBackend
│
├── governance/         # Phases 11, 12 — Governance gate
│   ├── drift_gate.py        check_drift_gate() → GateDecision, strictest_action()
│   ├── gate.py              GovernanceGate — unified checkpoint, Contradiction detection
│   ├── temporal.py          TemporalContext — Timeline features → enriched action_context
│   └── state.py             reduce() → StateSnapshot, diff() — replayable state
│
├── objectives/         # Phase 13 — Objective versioning
│   ├── core.py              ObjectiveVersion, ObjectiveStore — versioned lineage
│   └── staleness.py         parse_objective_source, find_stale_constraints, invalidated_by
│
└── tests/              # 547 tests across 22 files
    ├── test_constitution.py      16 tests
    ├── test_constraints.py       71 tests
    ├── test_context_classifier.py 57 tests
    ├── test_context_tags.py      17 tests
    ├── test_crystallization.py   26 tests
    ├── test_decision.py          15 tests
    ├── test_dosha.py             21 tests
    ├── test_drift.py             21 tests
    ├── test_email_signals.py     16 tests
    ├── test_governance.py        37 tests
    ├── test_graph.py             28 tests
    ├── test_guna.py              16 tests
    ├── test_ledger.py            27 tests
    ├── test_objectives.py        40 tests
    ├── test_reconcile.py         14 tests
    ├── test_state_reducer.py     20 tests
    ├── test_temporal.py          23 tests
    ├── test_timeline.py          30 tests
    ├── test_trend.py             18 tests
    └── test_vector_math.py       34 tests
```

---

## Governance Layer (The Kernel)

The core differentiator. Everything below this section is substrate — temporal containers and extracted math. The governance layer is what makes kala a kernel, not a library.

### Constraints (`kala/constraints/`)

Data-driven constraint evaluation. Constraints are **data** (serializable), not **code** (lambdas).

```python
# A constraint is a frozen dataclass
Constraint(
    id="sleep-boundary",
    constraint_type="time_boundary",      # time_boundary, value_alignment, drift_threshold, commitment, capacity, custom
    field="proposed_hour",                # dotted path into action_context
    operator="lte",                       # lt, gt, lte, gte, eq, neq, in, not_in, between, contains, not_contains
    value=22,
    description="Sleep by 10pm",
    source="objective:sleep-goal:v1",     # which objective created this
    priority=PRIORITY_HARD,               # SOFT=1, MEDIUM=2, HARD=3
)

# Evaluation is deterministic
verdict = evaluate(action_context, constraint_set)
# Verdict(action="allow"|"block"|"confirm", violations=(...))
```

**Priority logic:** Hard violation → `block`. Any violation (no hard) → `confirm`. No violations → `allow`.

**Field extraction:** Supports dotted paths (`"drift.drift_percentage"`), list indexing (`"items.0.title"`), and flat keys (`"dosha.moving_avg_14d.vata"`).

### Event Ledger (`kala/ledger/`)

Append-only event log with pluggable persistence.

```python
Event(
    id="evt-1",
    timestamp=datetime.now(UTC),
    entity_id="user-123",
    event_type="proposed",     # proposed, validated, committed, rejected, reconciled, observed
    action="suggest_routine",
    actor="llm",               # llm, user, system, crystallization, governance
    data={},
    reason="",
)
```

`LedgerBackend` is an ABC. kala ships `InMemoryBackend`. Production apps inject DB-backed backends.

### Governance Gate (`kala/governance/gate.py`)

The single checkpoint. Merges 4 sources into one `GateDecision`:

1. **Constraint evaluation** — field/operator/value against action_context
2. **Drift gate** — drift_percentage → allow/confirm/block
3. **Contradiction detection** — 5 typed categories against the ledger
4. **Objective staleness** — constraint references outdated objective version

**Contradiction types:**

| Type | What it detects |
|---|---|
| `previously_rejected` | Same action was rejected within time window |
| `contradicts_commitment` | Committed event conflicts with proposed action |
| `repetition_loop` | proposed → rejected → proposed cycle |
| `outdated_objective_version` | Constraint references stale objective |
| `violates_recent_override` | Reserved (not yet implemented) |

**Strictest wins:** `block > require_reconciliation > require_confirmation > allow`

### Temporal Context (`kala/governance/temporal.py`)

Bridges Timeline data into the constraint pipeline.

```python
tc = TemporalContext()
tc.add_timeline("dosha", dosha_timeline)
ctx = tc.build({"proposed_hour": 22})
# ctx now includes:
#   "dosha.latest.vata": 0.53
#   "dosha.moving_avg_7d.vata": 0.48
#   "dosha.moving_avg_14d.vata": 0.46
#   "dosha.trend_7d.vata": "rising"
#   "dosha.rate_7d.vata": 0.01
```

Constraints can then reference temporal features: `Constraint(field="dosha.moving_avg_14d.vata", operator="lt", value=0.6)`.

### State Reducer (`kala/governance/state.py`)

Replays events into deterministic state. Pure function — same events always produce the same snapshot.

```python
snapshot = reduce(ledger, entity_id="user-123")
# StateSnapshot(
#   entity_id="user-123",
#   active_commitments=("morning_meditation",),
#   pending_actions=("suggest_routine",),
#   rejected_actions=(),
#   last_drift_severity="moderate",
#   version=5,
# )
```

### Objective Versioning (`kala/objectives/`)

Versioned objectives with lineage and staleness detection.

```python
store = ObjectiveStore()
store.add(ObjectiveVersion(objective_id="sleep", version=1, title="Sleep by 10pm", ...))
store.add(ObjectiveVersion(objective_id="sleep", version=2, title="Sleep by 11pm",
                           parent_version=1, reason="10pm unrealistic on weekdays"))

# Constraint source convention: "objective:{id}:v{n}"
# find_stale_constraints(constraint_set, store) → [(stale_constraint, current_version)]
# invalidated_by(new_version, constraint_set) → [stale_constraints]
```

Sequential version enforcement (v1, v2, v3 — can't skip). `is_stale()` checks if a referenced version is outdated. GovernanceGate integrates this as the `outdated_objective_version` contradiction.

---

## Substrate Layer

Temporal containers and extracted pure math that the governance layer builds on.

### Timeline (`kala/timeline/`)

The fundamental temporal primitive. Generic over `T`.

- **`Snapshot[T]`** — Timestamped observation with confidence and source
- **`Timeline[T]`** — Bisect-sorted sequence with `at(t)`, `between(start, end)`, `window(duration)`, `latest()`, `earliest()`
- **`detect_trend(timeline, key, window)`** → `"rising"` | `"falling"` | `"stable"`
- **`moving_average(timeline, key, window)`** → `float`
- **`rate_of_change(timeline, key, window)`** → `float` per day
- **`reconcile(timelines, strategy)`** — Multi-source reconciliation with confidence weighting

### State (`kala/state/`)

Pure drift and constitution math.

- **`compute_baseline_drift(prakruti, vikriti)`** — Euclidean distance in 3D dosha space → `{drift_percentage, severity, primary_contributor, direction}`
- **`classify_severity(pct)`** → `"minimal"` | `"mild"` | `"moderate"` | `"significant"`
- **`classify_friction_state(drift, vikriti)`** → chaos | intensity | stagnation | balanced
- **Dosha/Guna state engines** — Score computation for Vata/Pitta/Kapha and Sattva/Rajas/Tamas

### Pattern (`kala/pattern/`)

Pattern crystallization — when observations become confirmed patterns.

- **`should_crystallize(observations, threshold)`** — Confidence-based crystallization check
- **Decay functions** — Pattern strength decays without reinforcement
- **Trajectory analysis** — Pattern direction over time

### Graph (`kala/graph/`)

In-memory graph construction for enrichment data.

- **`create_node(kind, label, data)`** — 13 valid kinds (theme, goal, emotion, etc.)
- **`create_edge(src, dst, relation)`** — 11 valid relations (supports, blocks, etc.)
- **`build_graph_from_enrichment(enrichment)`** — Enrichment dict → node/edge graph
- **Schema validation** — `sanitize_kind()`, `sanitize_relation()` with safe defaults

### Decision (`kala/decision/`)

Fast deterministic decision scoring (<5ms).

- **`compute_fast_decision_frame(goals, values, intents, tasks, soul_state)`** — Produces active_nodes, micro_links, friction_points, energy_path

### Signals (`kala/signals/`)

Signal extraction from external data sources.

- **Email signals** — subscription, avoidance, boundary, cognitive_load detectors
- **Context tags** — Semantic tag extraction for context classification

### Context (`kala/context/`)

- **`classify_context()`** — Deterministic context routing based on input signals

### Memory (`kala/memory/`)

- **`cosine_similarity(a, b)`** — Vector similarity for embedding-based recall

### Adapters (`kala/adapters/`)

ABCs for external dependencies. kala defines the interfaces; consuming apps provide implementations.

- `DatabaseAdapter` — fetch, fetch_one, execute
- `EmbeddingAdapter` — embed, embed_batch
- `LLMAdapter` — complete

---

## Dependency Graph

No circular dependencies. Each module depends only on modules above it (or stdlib).

```
adapters/          (zero deps)
signals/           (zero kala deps)
state/             (zero kala deps)
context/           (zero kala deps)
memory/            (zero kala deps)
timeline/          (zero kala deps)
pattern/           (→ timeline)
graph/             (zero kala deps)
decision/          (zero kala deps)
constraints/       (zero kala deps)
ledger/            (zero kala deps)
governance/        (→ constraints, ledger, timeline, objectives)
objectives/        (→ constraints)
```

---

## Build Phases

| Phase | What | Tests added |
|---|---|---|
| 0 | Adapter ABCs | — |
| 1 | Email signal detectors | 16 |
| 2 | Context classifier | 57 |
| 3 | Drift + constitution math | 37 |
| 4 | Vector math | 34 |
| 5 | Sakhi shims (re-exports) | — |
| 6 | Dosha/guna/context-tags state engines | 54 |
| 7 | Timeline[T] + trend + reconcile | 62 |
| 8 | Pattern crystallization | 26 |
| 9 | Graph + decision primitives | 43 |
| 10 | Constraint engine | 71 |
| 11 | Event ledger + governance gate | 64 |
| 12 | Temporal context + state reducer | 43 |
| 13 | Objective versioning | 40 |
| **Total** | | **547** |

---

## Safety Guarantees

- **kala never imports sakhi.** Enforced by convention and verified in CI.
- **All code is pure computation.** No DB, no LLM, no I/O, no async, no network.
- **Frozen dataclasses.** Governance decisions, events, violations, snapshots, objective versions — all immutable.
- **Deterministic.** Same inputs always produce same outputs. State reducer is replayable.
- **ABCs at boundaries.** `LedgerBackend`, `DatabaseAdapter` define persistence contracts without implementing I/O.

---

*Last updated: 2026-02-20*
