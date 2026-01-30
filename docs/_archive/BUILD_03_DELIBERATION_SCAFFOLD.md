# BUILD_03 — Deliberation Scaffold

### Expanding Thought Without Steering Action

This document defines **Phase-2 / Build-03** of Sakhi: the **Deliberation Scaffold**.

If the Evidence Pack enables **recognition**,
the Deliberation Scaffold enables **clear thinking**.

It exists to solve one problem:

> **How can Sakhi help a human think through complexity
> without choosing for them, nudging them, or collapsing ambiguity?**

---

## 1. Canonical Purpose

The Deliberation Scaffold is a **deterministic thinking surface**.

It helps the user:

* see tensions clearly
* recognize trade-offs
* separate intention from momentum
* slow down reactive decisions

It does **not**:

* give advice
* rank options
* recommend actions
* optimize outcomes

If Sakhi ever “feels opinionated,” this layer is being misused.

---

## 2. Position in the Architecture

```
Moment Model
   ↓
Evidence Pack
   ↓
Deliberation Scaffold   ← (THIS BUILD)
   ↓
Reflection & Language
```

**Key rule:**
Deliberation always happens **before** reflection, never inside it.

---

## 3. What the Deliberation Scaffold Is (And Is Not)

### It **IS**

* deterministic
* explicit
* inspectable
* reversible
* pre-interpretive

### It **IS NOT**

* decision logic
* optimization
* advice generation
* moral framing
* behavioral control

This layer expands the **decision space** — then stops.

---

## 4. Inputs (What This Build Consumes)

The Deliberation Scaffold uses **existing intelligence only**.

### Required Inputs

* `MomentModel`
* `EvidencePack`

### Supporting Signals

* alignment state
* coherence state
* conflict records
* drift detection
* forecast risk windows
* identity anchors (read-only)

No new inference sources are introduced.

---

## 5. Output: DeliberationScaffold Object (Canonical Shape)

The scaffold is **ephemeral**, injected into turn context.

```json
DeliberationScaffold = {
  "current_tension": "plain description of the tension",
  "decision_domain": "work | relationship | health | self | transition | unknown",
  "options": [
    {
      "option_label": "neutral description",
      "what_this_serves": "value/need it supports",
      "likely_effects": "short-term tendencies",
      "tradeoffs": "what becomes harder or deferred"
    }
  ],
  "signals_used": [
    "alignment",
    "energy",
    "recurrence",
    "identity_tension"
  ],
  "explicitly_not_deciding": [
    "no recommendation",
    "no ranking",
    "no urgency imposed"
  ],
  "confidence": 0.0-1.0
}
```

---

## 6. Option Construction Rules (Critical)

### Option Count

* Minimum: **2**
* Maximum: **4**

Never fewer than 2 — or the system collapses choice.

---

### Language Rules

* No “best”
* No “should”
* No future guarantees
* No optimization language

✅ Correct:

> “One option prioritizes recovery. Another preserves momentum.”

❌ Incorrect:

> “The healthier choice would be to rest.”

---

## 7. Visibility Contract (Important)

The Deliberation Scaffold:

* **may be partially surfaced** in language
* **may remain implicit** in tone and structure
* **must always exist internally** if a decision-shaped moment is detected

It is **never** hidden logic that steers behavior.

---

## 8. Storage & Lifecycle

* ❌ Not written to memory
* ❌ Not written to personal_model
* ✅ Eligible for Reflection Trace (Build-04)
* ♻️ Recomputed freely per turn

Retention window: **single turn only**.

---

## 9. Who Can Use This Layer

### Allowed

* Reflection & Language
* Reflection Trace
* Orchestration Layer

### Forbidden

* Task mutation
* Goal updates
* Planner enforcement
* Nudging engines

---

## 10. Failure Modes to Guard Against

This build fails if:

* options feel prescriptive ❌
* one option is framed as superior ❌
* urgency is implied ❌
* Sakhi “pushes clarity” instead of holding it ❌

If a user feels pressured, the scaffold is wrong.

---

## 11. Definition of “Done”

This build is complete when users say:

> “That helped me think — not decide.”

And when Sakhi can:

* name tension calmly
* surface trade-offs neutrally
* stop without resolving

---

## 12. Canonical Law

> **The Deliberation Scaffold exists to hold complexity —
> not to collapse it.**

Human agency lives in unresolved space.

---

**Build:** Phase-2 / Build-03
**Status:** Canonical
**Depends on:** Moment Model, Evidence Pack
**Unlocks:** Reflection Trace (Build-04)
