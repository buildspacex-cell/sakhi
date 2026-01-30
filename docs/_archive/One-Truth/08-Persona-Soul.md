Persona & Soul Update System

(Background Identity & Relationship Maintenance)

Purpose of this layer

Keep Sakhi’s sense of who the user is and how the relationship feels up to date — without blocking live interaction or turning single turns into fixed identity claims.

This layer maintains continuity, tone alignment, and long-horizon identity signals, not moment-to-moment interpretation.

When this runs

turn_persona_update is always enqueued by turn_v2

It runs asynchronously in the turn_updates worker

The live user reply has already been returned

This ensures:

zero latency impact

no interruption to reflection

identity work happens off the critical path

What this worker does (by responsibility)
1. Session-level persona tuning (lightweight, incremental)

Function: update_session_persona(person_id, text)

Extracts persona signals from the turn text

Updates persona_traits, blending dimensions such as:

warmth

reflectiveness

humor

expressiveness

tone bias

Updates last_updated

Design intent

This is tone calibration, not identity definition

It affects how Sakhi responds, not who the user is

2. Soul / identity refresh (deep, asynchronous rebuild)

Function: run_soul_engine(person_id)

This step rebuilds the long-horizon identity layer by scanning recent journals and memory artifacts.

It clears and re-inserts:

soul_values

value_name, description, confidence

anchors and evidence

identity_signatures

labels, narratives

coherence and supporting memories

purpose_themes

recurring themes

momentum and directionality

life_arcs

arc names and scopes

summaries, sentiment, narrative continuity

conflict_records

tension types

impacts and resolution hints

persona_evolution

current mode

drift score

evolution path

Design intent

Identity is rebuilt from evidence, not appended per turn

Single turns cannot permanently redefine the user

Drift is detected, not assumed

3. Narrative layer (best-effort)

Function: run_narrative_engine (optional)

Attempts to construct higher-order narrative coherence

Logs a warning if unavailable or failing

No hard dependency

This keeps narrative non-blocking and non-authoritative.

4. Relationship state adjustment (trust & attunement)

Function: update_from_turn(person_id, sentiment, pushback)

Reads:

sentiment (from emotion facets)

pushback signals (phrases like “stop”, “back off”, “no more”)

Updates relationship_state:

trust

attunement

emotional safety

Mirrors into personal_model.relationship_state when possible

Design intent

The relationship itself is treated as stateful

Respect, boundaries, and tone safety are tracked explicitly

Pushback reduces assertiveness automatically

What this system explicitly does not do

It does not create goals or tasks

It does not surface identity claims directly to the user

It does not react instantly to single turns

It does not block or modify the live reply

It does not treat emotion as truth

Identity emerges from patterned evidence, not inference.

How these outputs are used later

persona_traits

Influence conversational tone and response style

Soul tables

Feed downstream reasoning, alignment checks, and snapshot views

Support long-term reflection and meaning synthesis

relationship_state

Acts as the trust / safety backbone

Used in relationship-aware response logic and boundary handling

Why this layer belongs outside the live turn

Identity and relationship cannot be updated safely in real time.

By moving this work to background workers:

reflection stays human

identity stays stable

over-personalization is avoided

system behavior remains explainable

Architectural stance (important)

Sakhi does not decide who the user is in the moment.
It slowly learns who the user is over time.

This layer exists to remember continuity, not to assert identity.

One-line summary

Live turns express.
Persona and soul layers evolve.