# Sakhi — Canonical Index

### Single Source of Truth for System Understanding

This document is the **entry point** to Sakhi’s canonical technical and conceptual knowledge.

Its purpose is simple:

> **At any point in time, this file should allow a human or an AI to quickly reconstruct what Sakhi is, how it works, and where to look next.**

If a document, concept, or system is **not referenced here**, it is not canonical.

---

## 1. What Sakhi Is (High-Level Definition)

Sakhi is a **Personal Intelligence System** designed to act as an **Inner Human Mirror**.

It does not:

* decide for the user
* optimize behavior
* diagnose psychological states
* enforce routines
* act autonomously in the world

It does:

* understand a human across **body, mind, emotion, energy, rhythm, goals, and identity**
* track people **across time**, not just conversations
* surface patterns, contradictions, and drift
* scaffold action **without authority**
* help users arrive at **their own clarity**

Foundational documents:

* `01_VISION/INNER_MIRROR_CANONICAL_SPEC.md`
* `01_VISION/SAKHI_PRODUCT_PHILOSOPHY.md`
* `01_VISION/SAFETY_ETHICS_BOUNDARIES.md`

---

## 2. How Sakhi Works (System Overview)

Sakhi operates as a **layered system**, not a chat pipeline.

**Conceptual flow:**

```
Observe
  → Remember
    → Interpret
      → Scaffold
        → Reflect
          → Respond
```

Key architectural properties:

* Deterministic engines handle understanding and safety
* LLMs are used **only for language and reflection**
* All long-term intelligence lives outside the LLM
* Time, rhythm, and continuity are first-class dimensions

Core architecture references:

* `02_ARCHITECTURE/SYSTEM_ARCHITECTURE_OVERVIEW.md`
* `02_ARCHITECTURE/TURN_LIFECYCLE.md`
* `02_ARCHITECTURE/WORKER_QUEUE_MAP.md`

---

## 3. Layers of the System (Mental Model)

Use this section to orient yourself before diving into details.

### Layer 1 — Input & Observation

* Conversations
* Journals
* Behavioral timing (gaps, restarts)
* Task and intent signals

📄 Docs:

* `02_ARCHITECTURE/TURN_LIFECYCLE.md`

---

### Layer 2 — Memory & Identity

* Short-term memory
* Episodic memory
* Semantic rollups
* Long-term personal model (identity, values, rhythm, goals)

📄 Docs:

* `03_DATA_AND_MEMORY/MEMORY_MODEL.md`
* `03_DATA_AND_MEMORY/PERSONAL_MODEL_SCHEMA.md`

---

### Layer 3 — Deterministic Intelligence

* Emotion & energy trends
* Rhythm & temporal scaffolding
* Alignment, coherence, drift
* Pattern sense and narrative evolution
* Forecasting risk windows

📄 Docs:

* `04_INTELLIGENCE_LAYERS/EMOTION_ENERGY_MODELS.md`
* `04_INTELLIGENCE_LAYERS/RHYTHM_AND_TEMPORAL_INTELLIGENCE.md`
* `04_INTELLIGENCE_LAYERS/ALIGNMENT_COHERENCE_FORECAST.md`
* `04_INTELLIGENCE_LAYERS/PATTERN_AND_NARRATIVE_ENGINES.md`

---

### Layer 4 — Hands / Action Scaffolding

* Focus paths
* Mini-flows
* Micro-journeys
* Task routing and daily stacks

**Important:**
This layer scaffolds action but never executes it.

📄 Docs:

* `05_HANDS_AND_ACTION/PLANNER_HANDS_LAYER.md`
* `05_HANDS_AND_ACTION/TASK_ROUTING_LOGIC.md`
* `05_HANDS_AND_ACTION/ACTION_BOUNDARIES.md`

---

### Layer 5 — Language & Reflection

* Tone selection
* Empathy and micro-regulation
* Reflective questioning
* Suggestive guidance

📄 Docs:

* `02_ARCHITECTURE/ENGINE_RESPONSIBILITY_MATRIX.md`

---

## 4. Data as the Spine of Sakhi

Sakhi’s intelligence lives in data, not prompts.

All tables fall into one of four categories:

* Source of truth
* Derived intelligence
* Cached rollups
* Ephemeral context

📄 Canonical references:

* `03_DATA_AND_MEMORY/DATABASE_SCHEMA_CANON.md`
* `03_DATA_AND_MEMORY/CACHE_AND_ROLLUP_TABLES.md`

---

## 5. Safety, Ethics, and Control Boundaries

These constraints override all features and engines.

Non-negotiables:

* No diagnosis
* No manipulation
* No authority over decisions
* No LLM-based state mutation
* Deterministic > generative for intelligence

📄 Docs:

* `01_VISION/SAFETY_ETHICS_BOUNDARIES.md`
* `05_HANDS_AND_ACTION/ACTION_BOUNDARIES.md`

---

## 6. Observability, Trust, and Explainability

Sakhi must be understandable **without becoming surveillance**.

Current state and future direction:

* Limited per-turn observability
* No persistent reflection trace (yet)
* Replayability is intentionally bounded

📄 Docs:

* `06_OBSERVABILITY_AND_TRUST/OBSERVABILITY_CURRENT_STATE.md`
* `06_OBSERVABILITY_AND_TRUST/REFLECTION_TRACE_SPEC.md`
* `06_OBSERVABILITY_AND_TRUST/REPLAYABILITY_AND_DEBUG.md`

---

## 7. Roadmap and Evolution

This section tracks what is **intentionally incomplete**.

The remaining gap to the Inner Human Mirror is not infrastructural — it is relational.

Key roadmap references:

* `07_ROADMAP/INNER_MIRROR_COMPLETION_PLAN.md`
* `07_ROADMAP/FUTURE_FEATURE_CONTRACT.md`
* `07_ROADMAP/BUILD_LOG.md`

---

## 8. How to Use This Canonical Set

When working on Sakhi:

* Start here
* Follow links downward
* Update documents as part of builds
* Never introduce a new concept without anchoring it here

When working with AI tools:

* Reference this index explicitly
* Treat it as authoritative context
* Assume all reasoning must align with these documents

---

## 9. Canonical Rule

> **If it’s not in this index, it’s not part of Sakhi’s truth.**

This file exists so Sakhi can scale **without losing coherence** — technically, philosophically, or ethically.

---

**Last updated:** *(fill with build number/date)*
**Owner:** Founding team
**Status:** Canonical
