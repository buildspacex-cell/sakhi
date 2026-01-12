Brain Engine & Insight Synthesis

(Unified State Cache + Reflective Insight Layer)

Purpose of this layer

The Brain Engine assembles a single, coherent snapshot of the person’s current state across all subsystems and caches it for fast, consistent reuse.

The Insight Update layer then uses this snapshot to generate higher-order reflections and recommendations without re-running heavy analysis on every interaction.

Together, they allow Sakhi to:

reason holistically

remain responsive

keep higher-level intelligence consistent across features

The Brain Engine
(Unified State Assembly & Caching)
What the Brain Engine is

The Brain Engine is a consolidator and cache, not a decision-maker.

It pulls structured state from multiple subsystems, normalizes it, and writes a unified “brain state” snapshot into a single table.

It answers: “What is the person’s current operating state right now?”

How the brain state is built (compute_brain_state)

The engine reads from the following sources:

Planner / Goals

From planner_context_cache

Active goals, effort, blockers, confidence

Rhythm

From rhythm_state

Body energy, mental focus, emotional tone

Fatigue/stress, recovery needs

Next peak/lull, cycles, trends

Emotion

From personal_model

Dominant mood, volatility

Mood curve, sentiment trend

Self-reported emotion and fragility

Identity / Soul

From soul_values, purpose_themes, persona_evolution

Top values and purpose

Latest identity arc

Persona mode

Intention alignment (1 − drift_score)

Relationship

From relationship_state

Trust, attunement, emotional safety, relationship stage

Environment

From environment_context

Weather, calendar blocks

Day cycle, weekend/holiday, travel flags

Environment tags

Habits

From growth_habits

Top habits, consistency, motivation

Focus

From focus_sessions

Last session mode, outcome, flow, distractions

Duration and timestamp

Life Chapter

From narrative_seasons (or fallback to life_arcs)

Current chapter, tone, and theme

Working Memory

From personal_model.short_term

Recent conversational context (bounded)

Friction Points

From growth_task_confidence_events

Areas of hesitation or low confidence

Derived Priorities

Computed from planned_items or active_goals

Persistence model

Function: refresh_brain(person_id)

Computes the unified state

Upserts one row per person into:

personal_os_brain


Each subsystem state is stored as a structured JSON field

Updates last_updated

Optionally:

Refreshes journey caches (today / week / month / life) if refresh_journey = true

Access pattern

Function: get_brain_state(force_refresh = false)

Returns the cached personal_os_brain row

Recomputes only if:

cache is missing, or

force_refresh is requested

This ensures:

fast reads

consistent state across features

no repeated heavy joins per turn

What the Brain Engine does not do

It does not infer new facts

It does not create plans or actions

It does not generate user-facing text

It does not mutate upstream systems

It is a state mirror, not an agent.

Turn Insight Update
(Reflective Insight Generation)
Purpose of this job

Turn Insight Update generates higher-level insights by interpreting the current brain state in context.

It answers:

“Given the person’s full state, what insights are worth surfacing now?”

When it runs

turn_insight_update is always enqueued by turn_v2

Runs asynchronously in the worker

The live reply has already been sent

What it does

Handler: _handle_insight_update
Calls:

insight_engine.generate_insights(person_id, mode, behavior_profile)


Inside generate_insights:

Loads:

Brain state (brain_engine.get_brain_state)

Recent weekly/monthly summaries

Narrative context

Determines journey scope:

today / weekly / monthly (based on mode)

Builds four insight buckets:

Vision insights

Long-term direction

Narrative and purpose signals

Pattern insights

Repeated behaviors or tensions

Drawn from brain + weekly trends

Value alignment insights

Alignment between habits, actions, and values

Action recommendations

Energy-aware

Planner-aware

Proactiveness-aware

Still advisory, not imperative

Computes:

A lightweight confidence score

A short summary text (first items across buckets)

Returns an insight bundle:

{
  vision_insights,
  pattern_insights,
  value_alignment,
  action_recommendations,
  confidence,
  summary
}

Persistence behavior

The handler itself does not write to a table

Any persistence happens inside:

brain_engine

journey_renderer

narrative or cache refreshes

The insight bundle is:

logged

made available to presence / UI / analytics layers

not blocking the turn

How these layers are used later

Brain state

Feeds planning, identity reasoning, rhythm-aware features

Acts as the shared state for higher-level intelligence

Insight bundles

Surface in presence logic

Power reflective summaries and analytics

Can be selectively shown without recomputation

Architectural stance (this matters)

Sakhi does not “think” from scratch every time.
It maintains a coherent internal state — and reflects from that.

This allows:

consistency across experiences

explainability

performance at scale

separation of state from expression

One-line summary

The Brain Engine assembles state.
The Insight Engine reflects on it.