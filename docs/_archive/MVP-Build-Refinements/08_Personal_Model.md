STEP 7 — Personal Model (Longitudinal Trends Only)
Purpose

STEP 7 establishes the only authoritative learning layer in the system.

It answers:

How is the person changing over time — and how sure are we?

It explicitly does not answer:

Who the person is.

Authoritative Field
personal_model.longitudinal_state

All other personal_model fields are:

legacy

gated

non-authoritative

Canonical Dimensions

Only the following dimensions are allowed:

body

mind

emotion

energy

work

Canonical Schema (Per Dimension)
{
  "direction": "up | down | flat",
  "magnitude": 0.0,
  "volatility": 0.0,
  "confidence": 0.0,
  "window": {
    "start": "ISO-8601",
    "end": "ISO-8601"
  },
  "lifecycle": "emerging | stabilizing | decaying",
  "last_updated_at": "ISO-8601"
}

Inputs (Read-Only)

memory_episodic.context_tags (no text)

rhythm_weekly_rollups

planner_weekly_pressure

prior longitudinal_state

Worker
turn_personal_model_update

Properties

Weekly cadence

Deterministic math only

No LLM

No prose

Idempotent

Confidence can increase and decrease

Confidence Discipline

Confidence is:

bounded [0,1]

derived from evidence volume + consistency

decays without reinforcement

required for lifecycle promotion

Lifecycle States
State	Meaning
emerging	Weak / early signal
stabilizing	Repeated, consistent
decaying	Weakening or reversing

No state is permanent.

Safety Guarantees

No identity labels

No narrative text

No reflection persistence

Trends are reversible