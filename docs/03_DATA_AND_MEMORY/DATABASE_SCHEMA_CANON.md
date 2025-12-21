# Sakhi — Database Schema Canon

### Meaning, Ownership, and Lifecycle of All Data

This document defines the **canonical interpretation** of Sakhi’s database.

Supabase is the **structural truth** (tables, columns, constraints).
This document is the **semantic truth** (what the data *means*, how it lives, and how it must be treated).

If a table’s meaning is unclear here, it is **not allowed to silently evolve**.

---

## 0. Canonical Principles (Non-Negotiable)

1. **Data is Sakhi’s intelligence. Prompts are only its voice.**
2. No table is both **source-of-truth** and **cache**.
3. LLMs **never write** to identity, memory, or planning tables.
4. Temporal behavior (append, overwrite, recompute) defines trust level.
5. If meaning changes, the canon must change first.

---

## 1. Canonical Data Categories

Every table belongs to exactly one category.

### A. Source of Truth

* Represents lived reality or explicit user input
* Append-only or carefully versioned
* Never inferred or hallucinated

### B. Derived Intelligence

* Deterministic interpretation of source data
* Recomputable
* Must be explainable

### C. Cache / Rollup

* Time-boxed summaries or scaffolds
* Safe to overwrite
* Never authoritative

### D. Ephemeral / Observability

* Runtime or debugging state
* Not part of the Inner Mirror unless explicitly promoted

---

## 2. Identity & Long-Term Self (Core Spine)

### `personal_model`

**Category:** Source of Truth (Consolidated Identity)
**Lifecycle:** Rolling state (`updated_at`)
**Writes:** Deterministic workers only
**Reads:** `/v2/turn`, all engines, planner, tone/empathy

**Meaning:**
The **single living model of who the person is becoming**.

Contains:

* Long-term layers: emotion, mind, soul, rhythm, goals
* Identity anchors, graphs, narratives
* Alignment, coherence, forecast states
* Mirrored snapshots of daily/micro scaffolds

**Rules:**

* ❌ LLMs must never write here
* ❌ No append-only history inside this table
* ✅ History lives elsewhere; this is *current understanding*

**Status:** ACTIVE (critical)

---

## 3. Conversation as Lived Record

### `conversation_turns`

**Category:** Source of Truth
**Lifecycle:** Append-only
**Meaning:**
Raw conversational history (what was said, when, and in what tone).

Used for:

* gap detection
* continuity
* memory ingestion
* observability

---

### `conversation_sessions`

**Category:** Source of Truth
**Lifecycle:** Append + rolling metadata
**Meaning:**
Groups turns into coherent conversational arcs.

---

### `conversation_state`

**Category:** Ephemeral / Contextual
**Lifecycle:** Rolling state
**Meaning:**
Current conversational snapshot (emotion, tone, clarity, energy).

This is **not identity** — it is *momentary presence*.

---

### `conversation_suggestions`

**Category:** Derived Intelligence
**Meaning:**
Non-authoritative language suggestions.
Safe to discard.

---

## 4. Memory System (How Sakhi Remembers)

### `memory_short_term`

**Category:** Ephemeral → feeds intelligence
**Lifecycle:** Append + dedup
**Meaning:**
Recent cleaned inputs for immediate recall.

---

### `memory_episodic`

**Category:** Source of Truth
**Lifecycle:** Append-only
**Meaning:**
Time-stamped lived experiences with emotional, narrative, and context tags.

This is the **psychological past**.

---

### `episodes`

**Category:** Source of Truth (legacy-compatible)
**Meaning:**
Earlier episodic structure with salience, vividness, karmic weight.

**Status:** SUPPORTING / TRANSITIONAL
(Not fully retired, but conceptually overlaps with `memory_episodic`.)

---

### `memory_context_cache`

**Category:** Cache / Rollup
**Meaning:**
Pre-stitched recall window injected into `/v2/turn`.

Safe to recompute.

---

### `context_recalls`, `context_compact_summaries`

**Category:** Derived Intelligence
**Meaning:**
Interpretive recall artifacts — *how Sakhi chose to remember*.

Important for future **Reflection Trace**, not identity.

---

## 5. Emotion, Energy, Body, Environment

These tables prove Sakhi already thinks beyond “mind”.

### `emotional_signature`

**Category:** Derived Intelligence
**Lifecycle:** Append-only
**Meaning:**
Detected emotional patterns from lived data.

---

### `energetic_state`

**Category:** Derived Intelligence
**Meaning:**
Energy quality and stability derived from emotion + rhythm.

---

### `energy_cycles`

**Category:** Derived Intelligence
**Lifecycle:** Daily append
**Meaning:**
Day-level energy and mood phases.

---

### `body_metrics`

**Category:** Source of Truth (Optional / User-provided)
**Meaning:**
Physiological signals (manual or sensor-based).

**Status:** LATENT (not fully productized)

---

### `breath_sessions`

**Category:** Source of Truth
**Meaning:**
Explicit breath practices.

**Important:**
This is *embodied awareness*, not wellness gamification.

---

### `environment_context`

**Category:** Source of Truth (Contextual)
**Lifecycle:** Rolling
**Meaning:**
External constraints (calendar, weather, travel).

---

## 6. Rhythm, Alignment, Coherence, Forecast

### `rhythm_state`

**Category:** Derived Intelligence
**Lifecycle:** Rolling daily baseline
**Meaning:**
Energy, focus, fatigue, stress — time-aware but deterministic.

---

### `daily_alignment_cache`

### `coherence_cache`

### `forecast_cache`

**Category:** Derived Intelligence
**Lifecycle:** Rolling recompute
**Meaning:**
Multi-signal synthesis used for tone, pacing, and nudges.

**Rules:**

* Never authoritative
* Always explainable
* Recomputable from source

---

## 7. Daily & Micro Scaffolding (Hands Layer)

These are **support structures**, not memory.

### Daily rhythm caches

* `daily_reflection_cache`
* `daily_closure_cache`
* `morning_preview_cache`
* `morning_ask_cache`
* `morning_momentum_cache`
* `micro_momentum_cache`
* `micro_recovery_cache`

**Category:** Cache / Rollup
**Lifecycle:** Overwritten per date
**Meaning:**
Temporal scaffolding for awareness and pacing.

---

### Action scaffolds

* `focus_path_cache`
* `mini_flow_cache`
* `micro_journey_cache`

**Category:** Cache / Rollup
**Meaning:**
Deterministic, rhythm-aware guidance.

**Rules:**

* ❌ Not identity
* ❌ Not commitments
* ✅ Pure support

---

## 8. Goals, Tasks, and Action Routing

### `tasks`

**Category:** Source of Truth
**Meaning:**
User commitments with deterministic enrichment.

**Rules:**

* LLMs may suggest, never mutate
* No calendar control
* No auto-completion

---

### `task_routing_cache`

**Category:** Derived Intelligence
**Meaning:**
Recommended windows and reasoning.

---

### `micro_goals`

**Category:** Source of Truth (lightweight)
**Meaning:**
Explicit small intentions extracted from user input.

---

## 9. Identity Graphs, Anchors, Aspects

These tables are **deep but under-used** — important to name honestly.

* `anchor_weights`
* `anchor_feature_map`
* `aspect_features`
* `aspect_kinds`
* `brain_goals_themes`

**Category:** Derived Intelligence
**Meaning:**
Latent identity modeling infrastructure.

**Status:** LATENT (powerful, not fully surfaced)

This is where **Personal Brain 2.0** will evolve from.

---

## 10. Conflict, Narrative, Awareness

### `conflict_records`

**Category:** Source of Truth (Detected tension)
**Meaning:**
Explicitly modeled internal conflicts.

---

### `bridging_reflections`

**Category:** Derived Intelligence
**Meaning:**
High-salience reflections that connect themes across time.

---

### `aw_event`, `aw_episode`, `aw_edge`, `aw_redaction`

**Category:** Observability / Awareness Graph
**Meaning:**
Internal audit & awareness graph.

**Status:** LATENT / INTERNAL
(Not yet part of user-facing Inner Mirror.)

---

## 11. Observability & Debug

### `debug_traces`

### `system_events`

### `dialog_states`

**Category:** Ephemeral / Observability
**Meaning:**
System introspection and debugging.

**Rule:**
Never treated as user memory unless explicitly promoted.

---

## 12. Canonical Safety Rules (Final)

* ❌ LLMs never write to:

  * `personal_model`
  * memory tables
  * tasks or goals
* ✅ Deterministic engines own intelligence
* ✅ Caches are disposable
* ❌ Identity is never reconstructed from prompts

---

## 13. Honest Assessment (No Sugar Coating)

* This schema is **deep, rare, and future-proof**
* Some tables are **ahead of product**
* Some overlap exists due to evolution
* Nothing here blocks the Inner Human Mirror
* Most teams never get this far structurally

What’s missing is **orchestration**, not data.

---

## 14. Canonical Law

> **If a table’s meaning is unclear, the system is not allowed to rely on it.**

This document exists to ensure Sakhi scales **without losing coherence, trust, or humanity**.

---

**Status:** Canonical
**Owner:** Founding team
**Last updated:** *(add build/date)*
