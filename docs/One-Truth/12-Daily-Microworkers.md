Daily & Micro Experience Workers

(Time-Based Guidance & Lightweight Presence)

Purpose of this layer

The Daily & Micro Experience layer translates Sakhi’s internal state (planner, rhythm, insights, brain state) into small, time-appropriate prompts and previews across the day.

This layer exists to:

support daily rhythm and momentum

provide gentle structure, not control

surface guidance without blocking live turns

This layer does not think — it surfaces.

When these workers run

Scheduled periodically by the scheduler

Run independently of user turns

Populate cache tables ahead of time

Mirror state into personal_model where needed

turn_v2 only reads cached artifacts + guard flags
No heavy computation runs inline.

Morning flows (start-of-day grounding)
morning_preview_worker

Why
Create a calm, structured start-of-day overview.

What / How

Generates:

focus areas

key tasks

reminders

rhythm hint

short summary

Writes to:

morning_preview_cache (per person + date)

mirrors into personal_model.morning_preview_state

Use

Read by /v1/morning_preview

Seed for:

turn_v2 morning preview & guards

downstream morning/micro workers

This is the daily “opening context.”

morning_ask_worker

Why
Invite intention rather than prescribe action.

What / How

Reads morning_preview_cache

Generates a reflective “ask” prompt

Writes to morning_ask_cache

Use

Consumed by turn_v2 (morning ask / guard)

Used in morning experience flows

morning_momentum_worker

Why
Nudge early-day momentum without pressure.

What / How

Uses morning preview + context

Generates a momentum cue

Writes to morning_momentum_cache

Use

Exposed via turn_v2

Used in daily UI

Intra-day micro flows (lightweight support)
micro_momentum_worker

Why
Provide a small forward nudge during the day.

What / How

Generates a brief prompt or cue

Writes to micro_momentum_cache

Use

Read by turn_v2 (micro momentum)

Used in micro flows

micro_recovery_worker

Why
Offer recovery when energy or stress dips.

What / How

Generates a short recovery suggestion

Writes to micro_recovery_cache

Use

Read by turn_v2

Used in recovery UI

Focus & flow shaping
focus_path_worker

Why
Lay out a short, realistic focus path for the day.

What / How

Generates a focus sequence

Writes to focus_path_cache

Use

Included in turn_v2 responses

Used by focus-oriented UI

mini_flow_worker

Why
Create a compact, actionable flow when attention is limited.

What / How

Generates a small flow sequence

Writes to mini_flow_cache

Use

Returned via turn_v2

Used in mini-flow UI

micro_journey_worker

Why
Provide a concise sense of progression within the day.

What / How

Generates a micro-journey summary or plan

Writes to micro_journey_cache

Use

Returned via turn_v2

Used in journey UI

Evening flow (closure)
evening_closure_worker

Why
Help the day land gently and close the loop.

What / How

Generates an end-of-day reflection / closure prompt

Writes to daily_closure_cache (or evening_closure_cache)

Use

Read by turn_v2

Used in evening experiences

Architectural guarantees (important)

All workers:

run off the turn path

write to dedicated caches

are safe to recompute

turn_v2:

only reads cached artifacts

checks guard flags

never waits on these jobs

Experience is prepared in advance — never improvised under latency.

How this fits the overall storyline
Brain state / Planner / Rhythm / Insights
                ↓
      Daily & micro workers (scheduled)
                ↓
         Cached experiences
                ↓
        turn_v2 surfaces gently


This preserves:

responsiveness

predictability

emotional safety

What this layer does not do

Does not infer new identity

Does not create plans or goals

Does not override planner decisions

Does not push urgency

Does not run heavy reasoning inline

It is experience orchestration, not intelligence creation.

One-line anchor (keep this)

Sakhi prepares the day quietly — and meets the user where they are.

This section now completes the experiential side of the system, cleanly layered on top of everything you’ve built before.