Sakhi Deterministic Rhythm Engine  
Architecture, Invariants, and Elemental Intelligence Integration
===============================================================

1. Purpose & Philosophy
- The engine tracks balance, drift, and rhythm over time so we can notice patterns without diagnosing or advising.
- Rhythm is foundational because daily timing and pacing shape how effort, rest, and emotion accumulate.
- Determinism matters so every signal and conclusion is reproducible and auditable.
- Explainability is non-negotiable: every output must point back to concrete evidence and rules.
- The system observes first, interprets second, and only reflects—never acts—without explicit user consent.

2. Non-Negotiable System Invariants
- Raw evidence immutability: journals and activity facts are stored without edits; any transform creates a new record with lineage.
- Separation of evidence, signals, interpretation: facts → deterministic signals → interpreted summaries; layers never overwrite each other.
- No LLMs updating state: LLMs may render language but cannot write or mutate signals or stores.
- Reversibility of every insight: given outputs and rules, the same inputs always reconstruct the same result.
- No medical or prescriptive claims: outputs avoid diagnosis, treatment, or health guidance.

3. Memory Architecture Overview
- Short-term memory (STM): holds recent, volatile signals and hypotheses; exists to let fast-changing cues settle; expires to avoid stale assumptions.
- Episodic memory: stores compressed meaning of notable events, not raw mechanics; captures summaries with evidence anchors.
- Personal model: a slow-changing ledger of durable traits and baselines; integrates only vetted, stable signals.
- Flow (text diagram):
```
Journals/Activity -> STM (volatile signals, elemental projections)
    -> Episodic summaries (meaningful events)
    -> Personal model (slow traits, baselines)
```

4. Signal Extraction Layer (Deterministic)
- Journals and activity patterns are parsed with rule-based extractors; no culture-specific assumptions.
- Example neutral signals:
  - Overactivation: dense task spans with minimal gaps.
  - Recovery gaps: long stretches without rest markers.
  - Emotional steadiness masking strain: flat affect with concurrent fatigue keywords.
  - Rhythm irregularity: alternating late and early days without stable slots.
  - Physical discomfort indicators: repeated mentions of soreness, stiffness, or headaches.
- All signals are recorded with source spans and timestamps.

5. Elemental Projection Layer (Ayurveda Integration)
- Five Elements are internal coordinates, not labels; used as an interpretive lens across body, mind, and emotion.
- Separate mappings per domain (body/mind/emotion) to avoid collapsing context.
- Vectors, not types: each element is a float with decay; no fixed typing.
- Decay and volatility: scores fade unless refreshed by new evidence; sudden swings are marked as volatile.
- Sample JSON:
```json
{
  "body": {"earth": 0.2, "water": 0.1, "fire": 0.35, "air": 0.25, "space": 0.1, "volatility": 0.3},
  "mind": {"earth": 0.15, "water": 0.2, "fire": 0.25, "air": 0.25, "space": 0.15, "volatility": 0.2},
  "emotion": {"earth": 0.1, "water": 0.25, "fire": 0.2, "air": 0.3, "space": 0.15, "volatility": 0.25}
}
```

6. Why Elemental Signals Live in Short-Term Memory
- Elemental cues are volatile; STM lets them stabilize before turning into meaning.
- Premature abstraction risks locking in noise; STM is the sandbox for these hypotheses.
- STM expires (e.g., ~14 days) to prevent stale projections; expired cues must be re-earned by fresh evidence.
- Summaries and promotions run before expiry to capture only recurring patterns.

7. Aggregation & Promotion Pathways
- Weekly summaries: roll up STM signals into seven-day aggregates with decay and confidence.
- Trend detection: look for repeated direction (e.g., rising fire in body) with minimum count thresholds.
- Promotion thresholds: require recurrence plus stability; volatile spikes are held back.
- Examples:
  - Promoted: consistent evening overactivation with matching fatigue cues → “evening load is common.”
  - Not promoted: one-off late night or single mention of soreness.

8. Personal Model Extensions (Elemental Physics)
- Elemental baseline: average vectors over stable periods.
- Volatility: how often vectors swing beyond a small band.
- Recovery rate: speed at which stressed elements return to baseline after rest.
- Cross-dimension coupling: observed co-movement (e.g., mind fire rising when body air drops).
- These are traits (slow-changing), not momentary states.

9. Knowledge Graph Role (Constraint, Not Advice)
- Contains: relationships between elemental imbalances, generic lifestyle contexts, and consistency checks.
- Does not contain: food, herbs, treatments, or prescriptive actions.
- Uses: constrains interpretations, flags uncertainty, and guides prompt planning to keep language consistent.
- Serves as a reasoning aid and guardrail, not a recommendation engine.

10. LLM Boundary Contract
- Allowed: language rendering, metaphors, tone adjustments, and restating deterministic outputs.
- Forbidden: updating state, changing signals, making decisions, or adding new evidence.
- Separation exists to keep determinism intact and audits possible.

11. Explainability & Progressive Disclosure
- Reflection layer: plain-language narration of patterns without advice.
- Evidence layer: show which journals or events contributed, with timestamps.
- Pattern logic layer: show which deterministic rules fired and why.
- Optional conceptual lens: display elemental projections as a lens, not a label.
- Example flow: journal entries → signals (overactivation, discomfort) → reflection notes “evenings stayed packed and felt tiring” → user asks “why?” → system shows evening clusters and fatigue mentions across several days.

12. Explicit Non-Claims Charter
- No diagnosis.
- No medical advice.
- No authoritative claim over Ayurveda.
- No fixed typing of users.
- No replacement of lived experience or professional judgment.

13. Future Extension Path (Expert Plug-In Model)
- Domain experts can add or swap rule packs without changing the deterministic core.
- Rule versioning keeps lineage clear; old and new rules can be audited side by side.
- Swappable modules allow alternate mappings while preserving the same invariants.
- The founder is not the authority; governance comes from transparent, reviewable rule sets.

Validation Checklist
- No section implies diagnosis or prescription.
- Ayurveda is described as a lens, not a truth claim.
- Every insight can be traced back to evidence and deterministic rules.
- Determinism is preserved throughout.
