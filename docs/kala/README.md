# Kala

> काल — Sanskrit for *time*

**A governance kernel for AI agents — deterministic state management layered over probabilistic inference.**

---

## What Kala Is

Kala is a pure-computation library that gives AI agents deterministic governance: constraints that enforce boundaries, drift detection that gates behavior, an event ledger that provides audit trails, and objective versioning that tracks how goals evolve.

It sits between your agent's reasoning and its actions. Before any action reaches the user, it passes through Kala's governance gate — a single checkpoint that evaluates constraints, checks drift, detects contradictions, and enforces objective staleness.

**Origin:** Extracted from [Sakhi](https://github.com/fanantics/sakhi), a personal wellness AI. The governance layer turned out to be domain-agnostic.

---

## What Makes It Different

Most AI apps do none of this:

| Capability | Typical AI App | Kala |
|---|---|---|
| Memory | Chat history | Timeline with moving averages, trends, rates of change |
| Constraints | Prompt text ("be careful") | Deterministic evaluation: field/operator/value → Verdict |
| Drift | Metric on a dashboard | Behavioral gate: allow → confirm → block |
| Audit | Application logs | Append-only event ledger with provenance |
| State | Mutable DB row | Replayable reducer: same events → same snapshot |
| Objectives | Overwrite a field | Versioned lineage with staleness detection + constraint invalidation |

**The contrast:** Prompting an LLM to "respect the user's sleep schedule" is a suggestion. A `Constraint(field="proposed_hour", operator="lte", value=22, priority=HARD)` that returns `Verdict(action="block")` is enforcement.

---

## Architecture

```
kala/
├── signals/          # Signal extraction (email, context tags)
├── state/            # Drift math, dosha/guna state, constitution
├── context/          # Context classification and routing
├── memory/           # Vector math (cosine similarity)
├── timeline/         # Snapshot[T], Timeline[T], trends, reconciliation
├── pattern/          # Crystallization thresholds, trajectory analysis
├── graph/            # In-memory graph primitives, schema validation
├── decision/         # Deterministic decision scoring
├── constraints/      # Data-driven constraint engine → Verdict
├── ledger/           # Append-only event log, LedgerBackend ABC
├── governance/       # GovernanceGate, drift gate, temporal features, state reducer
├── objectives/       # Versioned objectives, lineage, staleness detection
├── adapters/         # ABCs for DB, embedding, LLM (no implementations)
└── tests/            # 547 tests across 22 test files
```

46 source files. Zero external dependencies beyond Python stdlib. No DB, no LLM, no I/O.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full module reference.

---

## The Governance Gate

The single entry-point for all governance checks:

```python
from kala.governance import GovernanceGate
from kala.constraints import Constraint, ConstraintSet, PRIORITY_HARD
from kala.ledger import Ledger
from kala.objectives import ObjectiveStore

gate = GovernanceGate(constraints, ledger, objectives=store)
decision = gate.evaluate(action_context, drift_data=drift)

# decision.action: "allow" | "block" | "require_confirmation" | "require_reconciliation"
# decision.triggers: ("constraints", "drift", "contradictions")
# decision.violations: tuple of constraint violations
# decision.reasons: human-readable explanations
```

What the gate checks:
1. **Constraints** — Data-driven rules (field/operator/value). Hard violation → block. Soft → confirm.
2. **Drift** — How far from baseline? High drift → block proactive suggestions.
3. **Contradictions** — Was this action previously rejected? Does it conflict with a commitment? Is it a propose→reject loop?
4. **Objective staleness** — Does a constraint reference an outdated objective version?

Strictest wins: `block > require_reconciliation > require_confirmation > allow`

---

## Key Primitives

### Timeline[T]
Generic temporal container. Bisect-sorted snapshots with temporal queries (`.at(t)`, `.window(duration)`, `.between(start, end)`). Supports moving averages, trend detection, rate of change.

### Constraint → Verdict
Serializable constraints (not lambdas). Deterministic evaluation: `evaluate(action_context, constraints) → Verdict(action="allow"|"block"|"confirm")`. Priority-based: hard violation blocks, soft confirms.

### Event Ledger
Append-only, never modify. `LedgerBackend` ABC for persistence. Default `InMemoryBackend`. Events are immutable frozen dataclasses.

### State Reducer
`reduce(events, entity_id) → StateSnapshot`. Pure, deterministic, replayable. Same events always produce the same snapshot.

### Objective Versioning
`ObjectiveVersion` with lineage (parent_version, reason). `ObjectiveStore` enforces sequential versions. Staleness detection: constraint source `"objective:sleep-goal:v1"` checked against current version.

### Temporal Context
Extracts Timeline features (moving averages, trends, rates) into flat action_context dict. Constraints can reference `"dosha.moving_avg_14d.vata"` — temporal intelligence drives governance.

---

## Design Principles

1. **Pure computation.** No DB, no LLM, no I/O, no async. Every function is deterministic. Same inputs → same outputs.
2. **kala never imports sakhi.** The dependency boundary is absolute. Sakhi imports kala, never the reverse.
3. **Data, not code.** Constraints are serializable data (field/operator/value), not lambdas. Objectives are frozen dataclasses, not classes with methods.
4. **Frozen by default.** Governance decisions, events, violations, snapshots, objective versions — all immutable. You can't accidentally mutate a verdict.
5. **ABCs at the boundary.** `LedgerBackend`, `DatabaseAdapter`, `EmbeddingAdapter` — kala defines interfaces, consuming apps provide implementations.

---

## Status

**Phase: Kernel complete. Integration pending.**

547 tests passing. 46 source files. Built across 14 phases of extraction and construction on `feat/kala-extraction`.

Next step: Route a real Sakhi conversation flow through GovernanceGate to demonstrate behavioral differentiation.

---

## Documentation

| Document | What's Inside |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full module reference — every file, every primitive, every function |
| [VISION.md](VISION.md) | Strategic positioning, competitive differentiation, design philosophy |
| [BUSINESS_STRATEGY.md](BUSINESS_STRATEGY.md) | Distribution strategy, monetization model, go-to-market |

---

*Last updated: 2026-02-20*
