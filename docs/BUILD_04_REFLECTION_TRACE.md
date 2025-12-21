# BUILD_04 — Reflection Trace

### Trust, Inspectability, and Completion of the Inner Human Mirror

This document defines **Phase-2 / Build-04**, the final structural layer required to complete the **Inner Human Mirror** vision.

Build-04 does **not** add intelligence.
It makes existing intelligence **visible, bounded, and trustworthy**.

---

## 1. Canonical Purpose

The Reflection Trace exists to answer one sentence — clearly and safely:

> **“I can see how Sakhi saw me.”**

Without this layer:

* understanding feels opaque
* trust is emotional, not inspectable
* debugging is guesswork
* safety review is incomplete

With this layer:

* Sakhi’s reasoning is visible **without exposing chain-of-thought**
* interpretation is accountable
* users can disagree safely
* builders can replay decisions

---

## 2. What Reflection Trace Is (And Is Not)

### It **IS**

* deterministic
* bounded
* human-readable
* replayable
* non-identity
* non-authoritative

### It **IS NOT**

* chain-of-thought
* prompt logs
* internal LLM reasoning
* psychological explanation
* memory
* identity state

> **This is an explanation of *process*, not *thought*.**

---

## 3. Position in the Architecture

```
Moment Model
   ↓
Evidence Pack
   ↓
Deliberation Scaffold
   ↓
Reflection Trace   ← (THIS BUILD)
   ↓
LLM Reflection
```

Reflection Trace is generated **before** language, and **never after**.

---

## 4. When Reflection Trace Is Generated

A Reflection Trace is created **only if at least one is true**:

* Evidence Pack was used
* Deliberation Scaffold was generated
* MomentModel.mode ∉ {trivial, chat, logistics}

No trace for:

* small talk
* pure journaling
* transactional queries

This keeps volume low and meaning high.

---

## 5. Canonical ReflectionTrace Shape

```json
ReflectionTrace = {
  "turn_id": "uuid",
  "created_at": "timestamp",

  "moment_summary": {
    "mode": "hold | ground | clarify | expand | pause",
    "dominant_need": "string",
    "stability": 0.0–1.0
  },

  "evidence_used": [
    {
      "when": "ISO timestamp or relative time",
      "source": "episodic | daily | narrative",
      "reason_selected": "salience | recurrence | contrast"
    }
  ],

  "deliberation_present": true | false,

  "tensions_named": [
    "string"
  ],

  "engines_fired": [
    "moment_model",
    "evidence_pack",
    "deliberation_scaffold"
  ],

  "intentionally_not_done": [
    "no advice",
    "no decision",
    "no task mutation",
    "no identity update"
  ],

  "confidence": 0.0–1.0
}
```

---

## 6. Storage & Lifecycle Rules (Strict)

### Persistence

* Reflection Trace **is persisted**
* Stored as:

  * either a new `reflection_traces` table
  * or a structured extension of `debug_traces`

### Absolutely Forbidden

* ❌ Writing to memory tables
* ❌ Writing to `personal_model`
* ❌ Feeding back into intelligence engines
* ❌ LLM-generated content inside the trace

### Retention

* Default: **internal only**
* Eligible for future user-facing explainability
* Retention policy is configurable (7d / 30d / indefinite)

---

## 7. Read & Access Rules

### Who may read it

* Internal replay tools
* Safety review
* Debugging
* (Later) optional user inspection

### Who may not

* Intelligence engines
* Planning logic
* Nudges
* Any system that could turn trace into authority

Reflection Trace is **observability**, not intelligence.

---

## 8. Confidence Calculation

Confidence must be deterministic and explainable.

Suggested baseline:

```
confidence =
  (moment_stability * 0.4)
+ (evidence_quality * 0.3)
+ (deliberation_clarity * 0.3)
```

Low confidence does **not** block reflection —
it **must be surfaced honestly**.

---

## 9. Failure Modes to Guard Against

This build fails if:

* Trace reads like justification ❌
* Trace sounds persuasive ❌
* Trace implies “this is the truth” ❌
* Trace leaks internal prompts ❌
* Trace becomes identity memory ❌

If users feel argued with, the build is wrong.

---

## 10. Definition of “Done”

Build-04 is complete when:

* Sakhi can say (internally):
  **“Here’s how I arrived at this reflection.”**
* Builders can replay a turn deterministically
* Safety reviewers can audit decisions
* Users could disagree without defensiveness
* Trust increases without charisma

At this point, the **Inner Human Mirror is structurally complete**.

---

## 11. Codex Instructions — DO NOT ASSUME

### Ask Codex to proceed only after answering these:

**Codex, before coding BUILD-04, confirm:**

1. **Storage choice**

   * New `reflection_traces` table or extension of `debug_traces`?

2. **Retention**

   * 7 days / 30 days / indefinite (internal)?

3. **Access scope**

   * Internal only for now? (default: yes)

4. **Redaction**

   * Any fields that must never be user-visible?

5. **Write path**

   * Sync write during `/v2/turn` or async worker?

6. **Replay scope**

   * Single-turn replay only, correct?

7. **Confidence formula**

   * Reuse deliberation confidence or recompute?

---

## 12. Codex Execution Instructions (High-Level)

**Once clarified, instruct Codex to:**

1. Define ReflectionTrace schema
2. Implement `build_reflection_trace()` (deterministic)
3. Collect:

   * moment summary
   * evidence metadata
   * deliberation presence
   * engines fired
   * intentional non-actions
4. Persist trace with `turn_id`
5. Ensure zero reads from trace in intelligence paths
6. Add unit tests for:

   * trace creation gating
   * suppression conditions
   * confidence bounds
   * non-identity guarantee

---

## 13. Canonical Law

> **If Sakhi cannot explain how it understood the moment,
> it is not allowed to act confident about it.**

This completes the Inner Human Mirror.

---

**Build:** Phase-2 / Build-04
**Status:** Canonical
**Unlocks:** 100% Inner Human Mirror Completion
**Everything after this is Phase-3 exploration, not core vision**
