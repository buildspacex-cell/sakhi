Phase-2 Build 1 — Explicit Moment Awareness
Status

📍 Phase-2 / Build 1
🎯 Required for 100% Inner Human Mirror
🧠 Deterministic, non-LLM intelligence

1. Purpose (Why This Build Exists)

Today, Sakhi implicitly understands the user’s moment.

After this build, Sakhi must be able to explicitly know and declare internally:

“What kind of moment is this — and how should I show up right now?”

This is not tone tuning.
This is situational self-awareness.

Without this layer:

intelligence is emergent

reflection depth varies

tone can feel correct but not inevitable

This build makes Sakhi intentionally present.

2. Canonical Definition — Moment Model

The Moment Model is a deterministic snapshot of the user’s current situational state, synthesized at turn-time.

It does not:

persist identity

override memory

control behavior

generate language

It exists only to answer:

“What kind of companion should Sakhi be right now?”

3. Hard Constraints (Non-Negotiable)

Codex must not:

introduce LLM reasoning

invent new memory tables

persist MomentModel initially

add probabilistic classifiers

modify personal_model directly

Codex must:

reuse existing signals

remain explainable

produce a bounded schema

integrate cleanly into /v2/turn

4. Inputs That Already Exist (DO NOT REBUILD)

Codex must assume these signals already exist and are available:

Emotional & Mental

emotion_state / emotion_loop

tone / clarity / energy signals

conflict_records

coherence_state

alignment_state

Temporal & Rhythm

rhythm_state

determine_rhythm_slot()

continuity gaps (conversation_turns timestamps)

forecast_state (risk windows)

Cognitive Load

mind layer (load, fragmentation)

recent interaction density

task pressure (via routing signals)

Meta

time of day (UTC for now)

session continuity

recent reflection/closure presence

If Codex cannot find a signal, it must ask — not assume.

5. Moment Model — Canonical Shape

Codex must implement a deterministic function that returns:

MomentModel = {
  "emotional_intensity": "low | medium | high",
  "stability": "stable | volatile | fragile",
  "cognitive_load": "low | medium | overloaded",
  "energy_state": "low | medium | high",
  "rhythm_window": "morning | midday | afternoon | evening | night",
  "risk_context": ["fatigue", "overwhelm", "irritability"],
  "continuity_state": "flowing | fragmented | restarting",
  "dominant_need": "grounding | clarity | expansion | rest | reflection",
  "recommended_companion_mode": "hold | reflect | ground | clarify | expand | pause"
}


Important

These are states, not judgments

All values must be explainable from inputs

No ML classification allowed

6. Companion Modes (Fixed Set)

Codex must hard-code exactly these modes:

Mode	Meaning
hold	Stay present, minimal language
reflect	Mirror without adding
ground	Reduce intensity, stabilize
clarify	Help untangle thinking
expand	Invite perspective
pause	Encourage rest / silence

No new modes without canon update.

7. Mapping Rules (Deterministic)

Codex must create explicit mapping logic, for example:

High emotional intensity + low stability → ground

High cognitive load + medium energy → clarify

Low intensity + high coherence → expand

Restart after long gap → hold

Fatigue risk + evening → pause

Exact rules should be documented inline.

8. Integration Point

MomentModel must be:

computed inside /v2/turn

injected into turn context

read-only for downstream layers

visible to orchestration + LLM

not persisted (Phase-2 Build-1 scope)

9. Questions Codex MUST Ask Before Writing Code

Codex must pause and ask you:

Where exactly are:

emotion_state

mind_state

coherence_state

forecast_state
currently loaded in /v2/turn?

Is there a preferred precedence:

emotion vs cognition?

rhythm vs forecast risk?

Should dominant_need be derived directly or mapped from mode?

Do you want MomentModel:

included in debug payload?

returned to client (hidden vs visible)?

Should we gate any modes by Safety & Ethics (e.g. avoid expand in fragile states)?

Codex must not continue without answers.

10. Codex Execution Steps (High Level)

Codex should execute in this order:

Audit /v2/turn context assembly

List all available signals

Implement compute_moment_model(signals)

Write mapping rules (pure function)

Inject into turn context

Add minimal logging (no persistence)

Validate against 5 real scenarios

11. Definition of Done

This build is complete when:

Sakhi internally knows what kind of moment this is

Tone feels consistent across identical situations

Builders can explain why a mode was chosen

Nothing breaks if MomentModel is disabled

If disabling it breaks Sakhi, the build is wrong.

12. What This Unlocks Next

Only after this build can you safely do:

Evidence Pack

Deliberation Scaffold

Reflection Trace

Orchestration Layer

This is the keystone build.

13. Canonical Law

If Sakhi does not know what kind of moment it is in,
it is not allowed to reflect deeply.