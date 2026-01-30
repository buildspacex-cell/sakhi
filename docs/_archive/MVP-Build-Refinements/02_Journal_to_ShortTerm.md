1. Purpose of This Build

This build reforms Short-Term Memory (STM) into a true working set:

Explicitly short-lived

Evidence-only

Safe to drop and rebuild

Free of interpretation, identity, or long-term meaning

The goal is to ensure STM supports clear, human-level reflection without becoming an interpretation sink or shadow long-term memory.

2. Functional Outcomes
✅ STM Is Now Actually “Short-Term”

Introduces an explicit time-based decay

Default retention: 14 days

Fully configurable via environment

✅ STM Is Evidence-Only

Stores only references to recent evidence

No sentiment, entities, facets, soul, summaries, or vectors

No derived meaning of any kind

✅ STM Is Disposable & Rebuildable

Safe to truncate without losing meaning

Can be rebuilt deterministically from:

journal_entries

conversation_turns

✅ STM Has a Single Responsibility

Assemble recent context

Not reflection

Not inference

Not identity modeling

3. Conceptual Model
Memory Layering (Authoritative)
Raw Evidence (Immutable)
        ↓
Short-Term Memory (Windowed, Disposable)
        ↓
Episodic Memory (Meaningful Events)
        ↓
Long-Term / Personal Model
        ↓
Reflection & Guidance


This build locks the STM boundary.

4. STM Contract (Authoritative)
Definition

Short-Term Memory is a disposable, windowed cache of recent evidence references used to assemble current context.

STM MUST:

Be bounded in time

Contain no derived meaning

Be safe to delete and rebuild

Reference evidence, not reinterpret it

STM MUST NOT:

Store sentiment, emotion, intent, or entities

Store summaries or narratives

Store embeddings or vectors

Store soul, identity, or values

Act as a long-term store

5. Tables Involved
5.1 memory_short_term

Role:
Holds a recent working window of evidence references and minimal capture metadata.

Schema (Post-Reform)
Column	Type	Description
id	uuid	Primary key
user_id	text	Owner
entry_id	uuid	Pointer to journal_entries / turn
source_type	text	journal | turn | experience
text	text	Optional raw text cache (byte-identical)
mood	text	Explicit user-provided mood (optional)
user_tags	text[]	Explicit user-provided tags (optional)
created_at	timestamptz	Insert time
expires_at	timestamptz	Window boundary (TTL)
5.2 TTL / Decay Enforcement

TTL column: expires_at (NOT NULL)

Default retention: 14 days

Configurable via: STM_TTL_DAYS (env)

Eviction rule:

DELETE FROM memory_short_term
WHERE expires_at < now();


Cleanup runs:

Best-effort during STM inserts/merges

Supported by index on expires_at

Optional periodic DB job

6. What Changed in This Build
Removed from STM Writes

The following are no longer written to STM:

sentiment / emotion classification

entities

facets / facets_v2

system-generated tags

embeddings / vectors

summaries

soul / soul_shadow / soul_light

identity or pattern data

These belong in downstream inference or episodic layers.

Write-Side Discipline

STM writes occur only at ingest / merge boundaries

Workers no longer mutate STM

Focus summaries no longer write to STM

Soul workers update episodic / personal layers only

7. Configuration
Environment Variable
STM_TTL_DAYS=14


Centralized in stm_config.py

Used to compute expires_at

Can be tuned without migrations

8. Migration Strategy

Existing STM rows are not migrated

Backfilled with expires_at

Old rows naturally age out

No breaking changes to callers

This avoids risky historical rewrites.

9. Why This Matters (Design Rationale)

Without this reform, STM:

Accumulates stale meaning

Blurs evidence with interpretation

Degrades reflection quality

Causes repetition and emotional drift

With this reform:

Reflection reasons over fresh evidence, not fossilized interpretations.

This aligns with Sakhi’s core principle:

Evidence is sacred.
Meaning is provisional.
Reflection must stay human.

10. Non-Goals of This Build

This build does not:

Redesign inference models

Migrate soul data

Implement reflection logic

Optimize retrieval or embeddings

Backfill historical meaning

Those belong to subsequent builds.

11. Follow-On Builds Enabled

This reform enables:

STEP 3: STM → Episodic Memory Consolidation

STEP 4: Weekly Reflection Engine

STEP 5: Long-Term Narrative & Rhythm Modeling

Each can now proceed on a clean foundation.

2. Summary (One Paragraph)

This build transforms Short-Term Memory into a true working set by enforcing explicit time-based decay, removing all derived meaning, and narrowing its responsibility to recent evidence references only. STM is now disposable, rebuildable, and structurally aligned with Sakhi’s reflection-first architecture. This correction prevents interpretation leakage, improves reflection clarity, and establishes a stable foundation for episodic and long-term memory layers.