(Ephemeral Meaning, Persistent Change)

Status: Implemented & Locked
Scope: Reflection, Longitudinal Learning, Continuity
Depends on:

Step 1 — Journal (Raw Evidence)

Step 2 — Short-Term Memory (Bounded Window)

Step 3 — Episodic Memory (Durable “What Happened”)

1. Purpose of STEP 4

STEP 4 introduces human-level reflection and long-term continuity without sacrificing trust, reversibility, or epistemic safety.

The core problem this step solves:

How can Sakhi feel like it learns over months
without freezing interpretations or identity claims into memory?

The answer is a strict separation between:

Reflection (meaning) → ephemeral

Learning (change over time) → structured, time-aware, persistent

2. Core Principle (Non-Negotiable)

Reflection outputs are ephemeral.
Trend deltas are the only long-lived learning artifacts.

No reflection prose, summaries, or narratives are ever persisted as truth.

3. Layer Responsibilities (Recap)
Layer	Role	Persistence	Interpretation
Journals	Raw evidence	Immutable	❌
STM	Recent window	TTL-bound	❌
Episodic	“What happened”	Durable	⚠️ bounded
Longitudinal (Step 4.6)	Change over time	Durable	❌
Reflection (Step 4.4)	Meaning now	Ephemeral	✅
4. Reflection Contract (STEP 4.2)

Reflection is a read-only, non-authoritative reasoning layer.

Reflection MAY:

read episodic memory

read longitudinal_state

generate human-readable understanding

ask gentle questions

Reflection MUST NOT:

write to any DB table

update memory or identity

persist summaries or insights

harden interpretations

Reflection is thinking aloud, not remembering.

5. Longitudinal Learning Contract (STEP 4.3a + 4.3b)

Learning captures how signals change over time, not what they “mean”.

Learning characteristics

deterministic (no LLM)

time-aware

confidence-weighted

incremental

reversible

Learning is the only authority that updates continuity.

6. Database Schema (Authoritative)
Table: personal_model
Column added in STEP 4.3a
ALTER TABLE personal_model
ADD COLUMN longitudinal_state JSONB NOT NULL DEFAULT '{}'::jsonb;

Canonical JSON Contract: longitudinal_state
{
  "<dimension>": {
    "<signal_key>": {
      "direction": "up | down | stable | volatile",
      "volatility": "low | medium | high",
      "confidence": 0.0,
      "observed_over_days": 0,
      "window": {
        "start": "YYYY-MM-DD",
        "end": "YYYY-MM-DD"
      },
      "last_episode_at": "ISO_TIMESTAMP",
      "last_updated_at": "ISO_TIMESTAMP"
    }
  }
}

Allowed base dimensions (extensible)

body

mind

emotion

energy

work

Explicit prohibitions

❌ prose

❌ identity labels

❌ causes / diagnoses

❌ advice

❌ reflection summaries

This column stores structure only.

7. Weekly Reflection Worker (STEP 4.4)
File
sakhi/apps/worker/tasks/weekly_reflection.py

Reads

memory_episodic (last 7 days)

personal_model.longitudinal_state (read-only)

Writes

❌ none (ephemeral output only)

Output
{
  "period": "weekly",
  "window": { "start": "...", "end": "..." },
  "reflection_text": "...",
  "confidence_note": "..."
}

Reflection structure

What happened (descriptive)

Felt sense (as expressed)

Noticing change (confidence-gated)

Gentle inquiry (optional)

Reflection language is tentative, non-diagnostic, and reversible.

8. Weekly Learning Worker (STEP 4.6)
File
sakhi/apps/worker/tasks/weekly_learning_worker.py

Role

Sole authority for updating personal_model.longitudinal_state.

Reads

memory_episodic (last 28 days, configurable)

Writes

personal_model.longitudinal_state

personal_model.updated_at

Does NOT

use LLMs

generate prose

read reflections

write identity / soul fields

Learning Window (configurable)
LEARNING_WINDOW_DAYS=28
DECAY_DAYS=21

Learning Logic (Deterministic)

For each (dimension, signal_key):

compute direction

compute volatility

update confidence

update time window

decay confidence when inactive

Signals fade; they are never deleted abruptly.

9. Safety Gates (Damage Containment)

To prevent legacy workers from corrupting continuity, STEP 4 introduces feature-flag safety gates.

Config flags
ENABLE_IDENTITY_WORKERS=false
ENABLE_REFLECTIVE_STATE_WRITES=false

Effect

Identity writers → no-op

Reflective persistence → no-op

Deterministic aggregations → unaffected

This ensures a single learning authority.

10. Why There Is No LLM in Learning

This is intentional.

Learning answers:

“How are signals changing over time?”

That requires:

ordering

counting

slope detection

decay

Not interpretation.

LLMs are used only at:

episodic summarization (bounded)

reflection generation (ephemeral)

11. MVP vs Full Companion
MVP (Weekly Reflection)

weekly learning

low confidence

short windows

tentative language

Full Companion (Months)

richer longitudinal_state

higher confidence

longer windows

deeper but still reversible reflection

Same architecture. No rewrites.

12. What STEP 4 Enables

continuity without identity lock-in

reflections that improve over time

safe model upgrades

trustworthy long-term companionship

clear technical moat

13. One-Sentence Summary

Reflection creates meaning.
Learning remembers change.
Meaning is never remembered.