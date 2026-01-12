Sakhi — Episodic Memory Contract (v2.3)
1. Purpose of Episodic Memory

Episodic Memory is Sakhi’s durable, human-scale memory layer.

It represents what happened, compressed into meaningful slices, without turning those slices into identity, advice, or decisions.

It exists to:

preserve experience beyond short-term memory

enable understanding across time

feed downstream intelligence layers with evidence, not opinion

Episodic memory does not decide.
Episodic memory does not advise.
Episodic memory observes and preserves.

2. When Episodes Are Created

Episodes are created only via asynchronous consolidation

Never synchronously in the turn path

Triggered after journals are written

Windowed by calendar day (UTC)

Creation rule (v2.3)

≥ 2 journals in the same day → eligible

Deduped by window + source_entry_ids

Idempotent

This ensures:

low latency

no journal-level noise

stable, replayable memory

3. What an Episode Contains (Authoritative Fields)

Episodic memory uses the existing memory_episodic table.
All fields are optional, confidence-gated, and additive.

Core observational fields (always safe)
Field	Meaning
text	Neutral, factual daily summary (2–4 sentences)
vector_vec	Embedding of the summary (semantic recall only)
ts	Time scope of the episode (window start)
content_hash	Deduplication
record	Metadata (episode type, window bounds, source ids)
Meaning & identity signals (derived, gated)
Field	Meaning	Notes
soul	Core meaning signals surfaced from experience	Observational
soul_shadow	Repeated inner difficulty	Non-diagnostic
soul_light	Sources of strength/clarity	Non-aspirational
Emotional & rhythm signals
Field	Meaning
emotional_state	Coarse affective state
rhythm_state	Energy / tempo / sustainability
Tension & dynamics (multi-episode only)
Field	Meaning	Gating
soul_conflict	Internal tension across time	Multi-episode
soul_friction	Repeated resistance	Multi-episode
emotion_loop	Recurring emotional regulation pattern	Confidence ≥ 0.65

These are never inferred from a single day.

4. What Episodic Memory Is NOT

❌ Not identity

❌ Not diagnosis

❌ Not advice

❌ Not goals

❌ Not plans

❌ Not turn context text

It is read-only evidence for intelligence layers.

5. Downstream Consumers — Complete Map

This is the key section you asked for.

A. Deep Identity & Meaning Layers
narrative_deep.py

Reads: soul, soul_shadow, soul_light

Ignores: vectors, summaries, emotion loops

Produces: personal_model.soul_narrative

Role: Meaning synthesis (non-turn, narrative arc)

identity_momentum_deep.py

Reads: soul, emotional_state, rhythm_state, ts

Uses: latest ~50 episodes

Produces: personal_model.identity_momentum_state

Role: Directional continuity over time

B. Rhythm & Regulation
rhythm_soul_deep.py

Reads: soul, rhythm_state, emotional_state, ts

Produces: personal_model.rhythm_soul_state

Role: Energy–meaning alignment

esr_deep.py

Reads: emotional_state, rhythm_state, emotion_loop, ts

Produces: personal_model.esr_state

Role: Emotional regulation & stability

Notes: Deterministic; no LLM; benefits passively from v2.3

C. Decision & Action Readiness
decision_graph_deep.py

Reads: soul_conflict, soul_friction, emotional_state, rhythm_state

Produces: personal_model.internal_decision_graph

Role: Internal tension, trade-offs, readiness

Notes: Only meaningful after episodic v2.3

D. Goals & Direction
brain_goals_themes_refresh.py (v2.3 refactor)

Reads: signal-first episodes using:

soul_conflict

soul_friction

emotion_loop

Fallback: recency if signals sparse

Produces: personal_model.goals_state

Role: Directional intent formation

Notes: Prompt unchanged; selection improved

E. Pattern Mining (Intentionally Raw)

These should not be over-normalized.

weekly_learning_worker.py
pattern_sense_refresh.py
identity_timeline_deep.py

Reads: raw episodic rows

Purpose: discovery, trend mining

Produces: internal pattern states

Notes: Noise-tolerant by design

F. Context & Recall Infrastructure
context_refresh_worker.py

Reads: vector_vec from episodic + STM

Produces: memory_context_cache.merged_context_vector

Role: Long-horizon semantic grounding

Notes: No text recall; vectors only

episodic_retrieval.py (canonical helper)

Reads: vector_vec, text, context_tags, ts

Purpose: semantic recall for labs / future synthesis

Notes: Not used in turn pipeline

6. What No Worker Does (By Design)

No worker:

modifies episodic memory

writes new episodic truth

uses episodic memory in real-time turn replies

treats episodic memory as identity

This preserves:

trust

debuggability

extensibility

7. Why This Architecture Scales to Sakhi’s Vision

This contract supports future capabilities like:

action suggestions

planning

scheduling

contextual help (“what might help right now?”)

Because:

episodic memory is stable

intelligence layers are separate

synthesis/presentation can evolve independently

no single worker “owns” the person

Sakhi doesn’t decide from memory.
Sakhi understands from memory.

8. Status

Episodic Memory v2.3 is COMPLETE and LOCKED.

