# Sakhi — Personal Model Schema

### The Living Spine of the Inner Human Mirror

This document defines the **canonical meaning, structure, and rules** of Sakhi’s `personal_model`.

If memory is Sakhi’s *past*,
the personal model is Sakhi’s **present understanding** of the human.

This table is not a database convenience.
It is the **single living self-model** Sakhi uses to mirror a person.

---

## 1. Canonical Definition

> **The personal model represents Sakhi’s best current understanding of who the person is becoming.**

It is:

* consolidated
* rolling
* revisable
* evidence-based
* explicitly *not permanent truth*

It is **never**:

* raw memory
* historical record
* personality typing
* diagnosis
* destiny

---

## 2. Role in the System (Why This Table Exists)

The `personal_model` exists to solve one problem:

> *How does Sakhi stay consistent over time without becoming rigid or judgmental?*

Without this layer:

* Sakhi forgets who the person is
* Or worse — reinterprets them differently every turn

With this layer:

* Sakhi feels grounded
* Responses align across days and weeks
* Reflection deepens instead of resetting

---

## 3. What the Personal Model Is — and Is Not

### It **IS**

* A rolling synthesis of memory
* A present-tense interpretation
* A hypothesis about the self
* A coordination layer for all engines

### It **IS NOT**

* A permanent identity label
* A psychological profile
* A personality test result
* A source of historical facts

This distinction protects the user’s ability to change.

---

## 4. Structural Overview (High-Level)

`personal_model` is a **single row per person** containing multiple **semantic layers**, each updated independently.

Conceptually:

```
personal_model
├── emotion_state
├── mind_state
├── soul_state
├── rhythm_state
├── goals_state
├── alignment / coherence / forecast
├── identity_graph
├── narrative_state
├── action_scaffolds (mirrored)
└── meta (timestamps, confidence, provenance)
```

Each layer answers a different question.

---

## 5. Canonical Layers (One Level Down)

### 5.1 Emotion Layer

**Question answered:**

> *How does this person generally feel and regulate emotion right now?*

Derived from:

* episodic emotion tags
* emotion_loop trends
* recent volatility / stability

Includes:

* dominant emotional patterns
* reactivity vs steadiness
* recovery capacity

**Rules:**

* No fixed traits
* No “you are X”
* Always trend-based, not absolute

---

### 5.2 Mind Layer

**Question answered:**

> *How does this person think, focus, and process load right now?*

Includes:

* cognitive load
* focus fragmentation
* clarity level
* priority pressure

Used by:

* tone modulation
* pacing decisions
* reflection depth

---

### 5.3 Soul Layer

**Question answered:**

> *What matters to this person, and where is there alignment or tension?*

Includes:

* values (current)
* identity anchors
* life themes
* contradictions (held gently)

This is **meaning**, not morality.

**Critical rule:**
Sakhi may *reflect* values — never enforce them.

---

### 5.4 Rhythm Layer

**Question answered:**

> *How does this person move through time and energy right now?*

Includes:

* daily energy baselines
* fatigue / stress trends
* rhythm-soul coherence
* ESR (emotion-soul-rhythm)

This is **temporal intelligence**, not biology (yet).

---

### 5.5 Goals & Intent Layer

**Question answered:**

> *What is this person oriented toward right now?*

Includes:

* active goals
* micro-goals meta
* intent strength
* friction points

Used to:

* contextualize reflection
* route tasks
* detect drift

---

### 5.6 Alignment, Coherence & Forecast

**Question answered:**

> *How stable is this person’s internal system right now — and what risks exist?*

Includes:

* alignment state
* coherence score
* forecast risk windows
* nudge readiness

**Important:**
These are **signals**, not judgments.

---

### 5.7 Identity Graph

**Question answered:**

> *How does this person see themselves — and how is that evolving?*

Includes:

* anchors
* features
* edges
* identity momentum
* timeline snapshots

This is the foundation of **Personal Brain 2.0**.

Currently:

* Partially built
* Latent but powerful

---

### 5.8 Narrative State

**Question answered:**

> *What story is emerging across time?*

Includes:

* narrative arc
* phase transitions
* inflection points
* continuity sense

This allows Sakhi to reflect:

> “This feels like a transition — not a failure.”

---

### 5.9 Action Scaffolds (Mirrored)

The personal model mirrors:

* focus_path_state
* mini_flow_state
* micro_journey_state
* routing_state

**Important:**
These are *mirrors*, not commitments.

They exist so Sakhi:

* stays consistent
* doesn’t repeat itself
* understands what support is already active

---

## 6. Write Rules (Extremely Important)

### Who can write to `personal_model`?

* ✅ Deterministic workers only
* ✅ Scheduled consolidation jobs
* ✅ Explicit refresh pipelines

### Who can NEVER write?

* ❌ LLMs
* ❌ Prompt logic
* ❌ Ad-hoc API calls
* ❌ Client input

### Write characteristics:

* Rolling overwrite
* No append history
* Must be recomputable
* Must be explainable

---

## 7. Read Rules

Read by:

* `/v2/turn`
* tone / empathy / microreg engines
* planner / routing logic
* daily & weekly workers

Read frequency:

* Very high
* Low latency required

This is why it must remain **compact and clean**.

---

## 8. Relationship to Memory (Critical Distinction)

| Memory        | Personal Model            |
| ------------- | ------------------------- |
| Past          | Present                   |
| Append-only   | Rolling                   |
| What happened | What it seems to mean now |
| Immutable     | Revisable                 |
| Many rows     | One row                   |

If this boundary blurs, Sakhi becomes unsafe.

---

## 9. Failure Modes to Avoid

If misused, the personal model can become:

* a personality classifier ❌
* a destiny engine ❌
* a moral authority ❌
* a control surface ❌

**Canon law:**
If a field starts sounding like “who you are”, it is wrong.

---

## 10. Why This Enables the Inner Human Mirror

The Inner Mirror requires:

* continuity without rigidity
* memory without fixation
* understanding without authority

The personal model makes that possible by being:

* always provisional
* always updateable
* always reflective
* never absolute

---

## 11. Honest Status Assessment

* Core structure: **Strong**
* Writes: **Safe**
* Reads: **Well-used**
* Identity graph: **Under-utilized**
* Narrative layer: **Partial**
* Explainability: **Missing (future)**

Nothing here blocks completion.
What’s missing is **orchestration, not schema**.

---

## 12. Canonical Law

> **The personal model must always be able to say:
> “This is my current understanding — and it could change.”**

That sentence protects human agency.

---

**Status:** Canonical
**Applies to:** All current and future builds
**Owner:** Founding team
**Last updated:** *(add build/date)*
