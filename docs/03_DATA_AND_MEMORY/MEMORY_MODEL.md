# Sakhi — Memory Model Canon

### How Sakhi Remembers, Forgets, Reflects, and Evolves Understanding

This document defines **what memory means in Sakhi** — not just where it is stored, but how it behaves, evolves, and is ethically constrained.

The database schema tells us *what exists*.
This document tells us **what is allowed, what is trusted, and what must never happen**.

If memory is misused, Sakhi ceases to be an *Inner Human Mirror* and becomes a manipulator.
This canon exists to prevent that.

---

## 1. Canonical Definition of Memory in Sakhi

In Sakhi:

> **Memory is not storage.
> Memory is lived experience interpreted across time.**

Memory exists to help a human:

* see themselves clearly
* recognize patterns
* understand change
* make conscious decisions

Memory does **not** exist to:

* define who someone is
* label them permanently
* optimize their behavior
* pressure them into choices

---

## 2. Memory Is Not Identity (Hard Boundary)

This is non-negotiable.

* **Memory** = what happened, how it felt, what it meant *then*
* **Identity** = Sakhi’s *current understanding* of who the person is becoming

Identity lives in `personal_model`.
Memory lives everywhere else.

**Rules:**

* Identity is *derived* from memory — never equal to it
* Memory can contradict identity
* Identity can evolve even if memory does not
* Memory is historical; identity is present-tense

Sakhi must always allow:

> “That was true then — it may not be true now.”

---

## 3. The Four Memory Classes (Canonical)

Every memory table maps to one of these classes.

---

### 3.1 Short-Term Memory

**Purpose:** Immediate context
**Trust level:** Low
**Longevity:** Minutes → hours

**Tables:**

* `memory_short_term`
* recent `conversation_turns`

**What it contains:**

* recent user inputs
* cleaned / triaged signals
* embeddings for recall
* transient tags (emotion_loop, wellness, triage)

**Rules:**

* Disposable
* Deduplicated aggressively
* Never treated as truth
* Never used for pattern claims

**Role in Inner Mirror:**
Keeps Sakhi coherent *right now* — nothing more.

---

### 3.2 Episodic Memory

**Purpose:** Lived experience
**Trust level:** Medium–High
**Longevity:** Permanent (append-only)

**Tables:**

* `memory_episodic`
* `episodes` (legacy, overlapping)

**What it contains:**

* time-stamped experiences
* emotional tone and intensity
* narrative tags
* context and meaning as understood *then*

This is **not raw logs**.
It is *interpreted experience*, frozen in time.

**Rules:**

* Append-only
* Never rewritten
* Never summarized in place
* No retroactive “fixing”

**Role in Inner Mirror:**
This is the **psychological past** — not the present self.

---

### 3.3 Semantic / Pattern Memory

**Purpose:** Understanding across time
**Trust level:** Medium
**Longevity:** Rolling / recomputable

**Tables:**

* `pattern_sense_cache`
* `brain_goals_themes`
* `narrative_arc_cache`
* `bridging_reflections`
* daily / weekly summaries

**What it contains:**

* recurring themes
* correlations
* seasonality
* narrative arcs
* inferred tensions

**Rules:**

* Always derived
* Always explainable
* Always replaceable
* Never authoritative

Patterns are **hypotheses**, not truths.

**Role in Inner Mirror:**
Helps Sakhi say:

> “Here’s what seems to be happening — tell me if this resonates.”

---

### 3.4 Long-Term Consolidated Memory (Identity Memory)

**Purpose:** Current understanding
**Trust level:** High
**Longevity:** Rolling state

**Table:**

* `personal_model`

**What it contains:**

* consolidated emotional tendencies
* values and identity anchors
* rhythm coherence
* alignment and conflict state
* current narrative understanding

This is **not history**.
This is Sakhi’s *best present-tense model*.

**Rules:**

* Deterministic writes only
* No LLM writes
* No append history
* Always overrideable by new evidence

**Role in Inner Mirror:**
This is what allows Sakhi to feel *consistent* without being rigid.

---

## 4. Memory Lifecycles & Decay

Memory in Sakhi is not static.

### Short-Term

* Rapid decay
* Deduped by content hash
* Promoted only if meaningful

### Episodic

* Never decays
* Influence fades naturally via pattern windows
* Never directly replayed without context

### Semantic / Pattern

* Sliding windows (e.g., last 90–200 entries)
* Regular recomputation
* Older patterns naturally disappear

### Long-Term Identity

* Updated by workers
* Reflects *recently dominant* understanding
* Can shift even if old memories remain

**Key principle:**

> Sakhi forgets *influence*, not *existence*.

---

## 5. Promotion, Compression, and Forgetting

### Promotion

* Short-term → episodic (ingestion)
* Episodic → semantic (pattern detection)
* Semantic → identity (consolidation)

### Compression

* Daily reflection
* Narrative arcs
* Bridging reflections

### Forgetting

* No hard deletes of lived experience
* Influence decays via:

  * windowing
  * weighting
  * recomputation

There is **no traumatic replay loop by design**.

---

## 6. Recall vs Reflection vs Evidence (Critical Distinction)

### Recall

> “What happened before?”

* Uses episodic memory
* Limited
* Contextual
* Never judgmental

### Reflection

> “What does this seem to mean now?”

* Uses semantic memory
* Tentative
* Framed as hypothesis
* Always open-ended

### Evidence

> “What past moment will the user *recognize immediately*?”

* Highly selective
* Minimal
* Human-legible
* Never overwhelming

This distinction is essential to avoid:

* manipulation
* gaslighting
* over-interpretation

---

## 7. Memory in `/v2/turn` (Read Path)

At turn time, Sakhi reads:

* `personal_model` (identity)
* `memory_context_cache` (stitched recall)
* selected episodic recall (k-limited)
* daily/micro scaffolds
* pattern/forecast/alignment summaries

It does **not**:

* dump memory
* surface raw history
* replay emotions

The LLM receives **curated meaning**, not memory dumps.

---

## 8. Memory in Workers (Write & Consolidation Path)

Workers:

* ingest lived data
* tag experiences
* recompute patterns
* update identity slices
* refresh caches

**Critically:**

* Workers are deterministic
* They leave audit trails
* They can be re-run
* They do not hallucinate

This keeps memory **safe to evolve**.

---

## 9. What Sakhi Must Never Do With Memory

Sakhi must never:

* Diagnose (“you are X”)
* Fix identity traits permanently
* Say “you always / you never”
* Pressure decisions using memory
* Use memory to optimize engagement
* Hide uncertainty behind confidence

Memory is a **mirror**, not a lever.

---

## 10. Memory as the Foundation of the Inner Human Mirror

The Inner Human Mirror emerges when:

* Memory is trustworthy
* Patterns are tentative
* Identity is flexible
* Evidence is relatable
* Reflection invites self-recognition

Memory enables clarity —
**not compliance, not control, not optimization**.

---

## 11. Known Gaps & Honest Limitations

Today:

* No explicit memory salience scoring beyond heuristics
* No user-visible memory inspection tools
* No reflection trace persisted per turn
* Some legacy overlap (`episodes` vs `memory_episodic`)

These are **solvable orchestration gaps**, not structural flaws.

---

## 12. Canonical Law

> **Memory must always expand a human’s understanding —
> never collapse it.**

If a memory behavior violates this, it is a bug — not a feature.

---

**Status:** Canonical
**Applies to:** All current and future builds
**Owner:** Founding team
**Last updated:** *(add build/date)*
