# Sakhi — Cache and Rollup Tables Canon

### Temporal Scaffolding, Not Memory. Support, Not Identity.

This document defines the **canonical meaning, lifecycle, and constraints** of all cache and rollup tables in Sakhi.

These tables are powerful — and dangerous if misunderstood.

They exist to **support the human in the moment**,
not to define who the human is.

---

## 1. Canonical Definition

> **Caches and rollups are temporary interpretations of reality — never reality itself.**

They:

* summarize
* scaffold
* pace
* remind
* support continuity

They do **not**:

* define identity
* store lived experience
* carry long-term meaning
* accumulate authority

---

## 2. Why Cache Tables Exist at All

Without cache/rollups:

* Every turn would recompute everything
* The system would feel inconsistent
* Temporal support (morning, recovery, closure) would collapse
* The user experience would feel chaotic

Caches exist to give Sakhi:

* temporal coherence
* rhythm awareness
* gentle continuity
* non-invasive guidance

They are **performance + experience primitives**, not intelligence primitives.

---

## 3. Canonical Categories of Cache Tables

All cache/rollup tables fall into one of four groups.

---

### 3.1 Daily Reflection & Closure

**Tables:**

* `daily_reflection_cache`
* `daily_closure_cache`

**Purpose:**
Help the human *see* the day — not judge it.

**Lifecycle:**

* One row per person per date
* Overwritten daily
* Derived from episodic memory + tasks

**Rules:**

* ❌ Never used as evidence of identity
* ❌ Never accumulate across days
* ✅ Safe to recompute
* ✅ Can be discarded without loss of truth

**Human experience:**

> “This helps me notice my day — then let it go.”

---

### 3.2 Morning, Momentum & Recovery Scaffolds

**Tables:**

* `morning_preview_cache`
* `morning_ask_cache`
* `morning_momentum_cache`
* `micro_momentum_cache`
* `micro_recovery_cache`

**Purpose:**
Support *temporal pacing* and *emotional regulation*.

**Lifecycle:**

* Generated on schedule or event
* Valid for limited time windows
* Replaced frequently

**Rules:**

* ❌ Never treated as obligations
* ❌ Never enforced
* ❌ Never persisted as memory
* ✅ Only advisory

**Human experience:**

> “This is helpful right now — not something I owe.”

---

### 3.3 Action Scaffolding (Hands Layer)

**Tables:**

* `focus_path_cache`
* `mini_flow_cache`
* `micro_journey_cache`

**Purpose:**
Break overwhelming intention into humane steps.

**Lifecycle:**

* Generated per day or per trigger
* Overwritten freely
* Mirrored into `personal_model` for continuity

**Rules:**

* ❌ Not commitments
* ❌ Not plans
* ❌ Not goals
* ✅ Support structures only

**Key rule:**
If a user ignores these, **nothing breaks**.

---

### 3.4 Alignment, Coherence, Forecast & Pattern Rollups

**Tables:**

* `daily_alignment_cache`
* `coherence_cache`
* `forecast_cache`
* `pattern_sense_cache`
* `brain_goals_themes`
* `narrative_arc_cache`

**Purpose:**
Provide **interpreted signals** for reflection, tone, and pacing.

**Lifecycle:**

* Rolling recomputation
* Sliding windows
* Overwritten safely

**Rules:**

* Always explainable
* Always probabilistic
* Always replaceable

**Important:**
These are *models of understanding*, not truths.

---

## 4. Cache vs Memory vs Personal Model (Hard Boundary)

| Layer          | Question Answered                | Persistence | Authority |
| -------------- | -------------------------------- | ----------- | --------- |
| Memory         | What happened?                   | Permanent   | High      |
| Cache          | What’s helpful now?              | Temporary   | Low       |
| Personal Model | What does this seem to mean now? | Rolling     | Medium    |

If a cache starts influencing identity, it is a bug.

---

## 5. Write Rules

### Who can write to cache tables?

* ✅ Deterministic workers
* ✅ Scheduled jobs
* ✅ Event-triggered engines

### Who can NEVER write?

* ❌ LLMs
* ❌ Prompt logic
* ❌ Clients
* ❌ Ad-hoc scripts

### Write characteristics:

* Overwrite allowed
* No append-only semantics
* No history guarantees
* Recomputable at any time

---

## 6. Read Rules

Read by:

* `/v2/turn`
* planner / routing logic
* tone / empathy engines
* nudge workers

Read semantics:

* Advisory only
* Optional
* Contextual

If a cache is missing, Sakhi must still function.

---

## 7. Promotion Rules (Very Important)

Caches may influence:

* tone
* pacing
* reflection framing

Caches may **never**:

* be promoted directly to memory
* be promoted directly to identity
* be cited as evidence without validation

Promotion path must always be:

```
lived experience → episodic memory → pattern → identity
```

Never:

```
cache → identity
```

---

## 8. Failure Modes to Guard Against

If misused, caches become:

* silent control mechanisms ❌
* pseudo-obligations ❌
* hidden nudges ❌
* authority by repetition ❌

**Canonical warning:**
Repeated suggestion is still pressure.

---

## 9. Known Gaps (Honest)

* No user-facing visibility into active caches
* No explanation of *why* a scaffold exists
* No expiration UI cues
* Some overlap between pattern caches and narrative caches

These are **UX + orchestration gaps**, not architectural flaws.

---

## 10. Why This Matters for the Inner Human Mirror

The Inner Mirror works only if:

* support is light
* authority stays human
* guidance can be ignored without consequence

Cache tables allow Sakhi to be **present without being heavy**.

---

## 11. Canonical Law

> **Caches must make it easier to act —
> never harder to choose.**

If a cache makes the user feel behind, obligated, or judged — it is wrong.

---

**Status:** Canonical
**Applies to:** All current and future builds
**Owner:** Founding team
**Last updated:** *(add build/date)*
