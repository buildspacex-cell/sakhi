# Sakhi — System Architecture Overview

### How the Inner Human Mirror Is Structurally Possible

This document explains **how Sakhi is architected**, not at the level of files or frameworks, but at the level of **system responsibility and flow**.

Its purpose is to answer one question clearly:

> *How does Sakhi turn lived human experience into reflection — without becoming controlling, unsafe, or shallow?*

If this architecture holds, features can evolve safely.
If this architecture breaks, no feature can save the product.

---

## 1. First Principle: Sakhi Is Not a Chat System

Most AI systems follow this pattern:

```
User Input → Prompt → LLM → Response
```

Sakhi does **not**.

Sakhi follows this pattern:

```
User Experience
   ↓
Observation
   ↓
Memory
   ↓
Deterministic Interpretation
   ↓
Scaffolding (optional)
   ↓
Reflection (language)
```

Language is the **last mile**, not the brain.

This single decision defines the entire architecture.

---

## 2. The Five Structural Layers of Sakhi

At the highest level, Sakhi is composed of **five non-negotiable layers**, each with a strict responsibility.

---

## Layer 1 — Observation (What Enters the System)

**Purpose:**
Capture *what the human expresses or does* — without interpretation.

Sources include:

* conversation turns
* journal entries
* timing signals (pauses, gaps, revisits)
* explicit actions (tasks, breath sessions, reflections)

**Key rule:**
Nothing in this layer decides meaning.

This layer answers only:

> *What happened? When? In what form?*

---

## Layer 2 — Memory (What Is Preserved)

**Purpose:**
Store lived experience across time in a way that respects human change.

Memory is **multi-timescale**:

* short-term (recent context)
* episodic (lived moments)
* semantic (patterns and themes)
* long-term consolidation (identity-relevant history)

**Key rule:**
Memory is **append-only** or carefully versioned.

This layer answers:

> *What has this person lived through?*

Memory is sacred.
It is never rewritten to “fit a story.”

---

## Layer 3 — Deterministic Intelligence (What It Seems to Mean)

This is the **core differentiator** of Sakhi.

**Purpose:**
Interpret memory *safely* using explainable, rule-based engines.

Includes:

* emotion & energy trend analysis
* rhythm & temporal intelligence
* alignment and coherence detection
* conflict and drift sensing
* narrative phase detection
* forecasting risk windows

All of this is:

* deterministic
* inspectable
* recomputable
* non-LLM

**Key rule:**
No language model is allowed to infer meaning here.

This layer answers:

> *Given what has happened, what patterns are emerging right now?*

---

## Layer 4 — Scaffolding & Support (How Sakhi Helps Without Controlling)

**Purpose:**
Offer *temporary support structures* that make life easier — not directed.

This includes:

* daily rhythm scaffolds (morning, closure, recovery)
* focus paths and mini-flows
* micro-journeys and pacing
* task routing into gentle windows
* nudges (used sparingly)

**Key rule:**
All scaffolds are **optional and disposable**.

This layer answers:

> *What might help this person right now — if they choose it?*

Nothing here becomes obligation.

---

## Layer 5 — Reflection & Language (How Sakhi Speaks)

**Purpose:**
Translate structured understanding into humane language.

The LLM:

* receives structured context
* reflects, mirrors, questions
* never decides
* never diagnoses
* never enforces

**Key rule:**
Language expresses understanding — it does not create it.

This layer answers:

> *How do we reflect this back so the human sees themselves more clearly?*

---

## 3. The Personal Model — The Spine Across Layers

Running **through** all layers is the **Personal Model**.

It is:

* a rolling synthesis of understanding
* always revisable
* never a fixed identity
* the anchor for continuity

Memory feeds it.
Deterministic engines update it.
Scaffolds mirror it.
Language reads from it.

It answers one quiet but critical question:

> *Who does Sakhi understand this person to be right now?*

---

## 4. What Sakhi Explicitly Avoids (Architecturally)

Because of this structure, Sakhi **cannot**:

* optimize for engagement
* manipulate emotions
* silently enforce behavior
* overwrite identity
* act as a moral authority
* “decide for” the user

These are not policy choices.
They are **structural impossibilities**.

---

## 5. Time Is a First-Class Dimension

Sakhi is architected around **time**, not just content.

* moments
* days
* weeks
* phases
* transitions

Daily and weekly jobs exist not for automation, but for **temporal coherence**.

This is how Sakhi feels like:

> “It knows me over time.”

---

## 6. Where the Architecture Is Complete — and Where It Isn’t

### Structurally Complete

* separation of memory, intelligence, and language
* deterministic safety core
* temporal scaffolding
* non-authoritative reflection

### Structurally Incomplete (By Design)

* explicit *Moment Model* (currently implicit)
* reflection trace & replay
* surfaced explainability
* orchestration layer that chooses *how to be* in a moment

These are **next-layer orchestration problems**, not architectural flaws.

---

## 7. Why This Architecture Scales Safely

Because:

* intelligence is explainable
* memory is respected
* agency is preserved
* scaffolding is optional
* language is downstream

This system can grow:

* more intelligent
* more personal
* more helpful

without becoming:

* invasive
* coercive
* addictive
* unsafe

---

## 8. Canonical Law

> **If a feature cannot be placed cleanly into one of these layers, it does not belong in Sakhi.**

This document is the map.
All future building must respect it.

---

**Status:** Canonical
**Applies to:** All builds, current and future
**Owner:** Founding team
**Last updated:** *(add build/date)*
