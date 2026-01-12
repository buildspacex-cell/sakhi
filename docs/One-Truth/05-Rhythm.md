Rhythm Triggers & Rhythm Forecasting
Purpose of this layer

Detect repeated energy- and rhythm-related strain signals in user expression and use them to bias rhythm understanding over time.

This layer does not schedule actions or recommend specific times in the moment.
It quietly shapes the system’s longer-range rhythm intelligence.

Step 1: Rhythm trigger detection (lightweight signal pass)

After intents are extracted, a small rhythm trigger hook runs.

Each intent is scanned for energy / rhythm-related language

Examples include terms like:

tired, fatigue, exhausted

sleep, rest

drained, overwhelmed

fog, scattered, low energy, low focus

If no such signals are found:

The system does nothing

No writes occur

This ensures rhythm is influenced only when relevant evidence appears.

Step 2: Applying rhythm triggers (backend-only)

If rhythm-related intents are detected, apply_rhythm_triggers runs.

It performs two backend updates:

1. Correlation tracking (persistent, aggregate)

For each relevant intent domain/theme:

A row is upserted in theme_rhythm_links for that person

Correlation counters and sample counts are incremented

These rows represent longitudinal associations between:

themes in the user’s life

and reported low-energy or overload states

This data is persistent, aggregate, and non-verbatim.

2. Rhythm refresh signal (non-user-facing)

The system sets:

personal_model.rhythm_state.refresh_hint = "weekly"


This is a flag, not a recommendation

It signals that rhythm data should be recalculated

No text, advice, or UI output is generated at this stage.

Step 3: Rhythm forecast execution (asynchronous)

A scheduler monitors rhythm refresh hints.

When it sees refresh_hint = "weekly":

It runs run_rhythm_forecast for that person

The forecast worker:

reads recent rhythm correlations

considers accumulated evidence

generates a weekly rhythm outlook

energy / focus / emotional trends

forecast vectors or summary text

Updates the user’s rhythm state

Clears the refresh hint

This process is asynchronous and decoupled from journaling or conversation.

What this system does not do

It does not generate “best time to act” suggestions at trigger time

It does not schedule tasks or plans

It does not interrupt the user

It does not turn a single tired day into a prescription

Rhythm influence emerges gradually, from pattern density, not single moments.

How this gets used later

The outputs of rhythm triggers and forecasts feed into:

Future reflections (weekly rhythm-aware summaries)

Tone and pacing decisions in guidance

Energy-aware suggestions (when explicitly asked)

System analytics and auditability

They provide context, not commands.

Design stance (core idea of the section)

Sakhi does not optimize a calendar.
It learns a person’s rhythm over time and lets that understanding quietly shape guidance.

Rhythm intelligence is:

inferential

probabilistic

slow-moving

respectful of variability

Why this matters

Prevents overfitting to bad days

Avoids “AI scheduling your life”

Creates a defensible bridge between biology and planning

Allows rhythm science to evolve without destabilizing core memory or planner systems

Rhythm’s contract (what it does and does not do)

Add a short subsection like this:

Rhythm system contract

What the rhythm system does

Maintains the user’s energy, focus, and emotional cadence

Produces:

current state

short-term daily curves

weekly outlooks

Feeds alignment and insight layers

What the rhythm system does not do

Does not schedule tasks

Does not assign priorities

Does not decide what the user should do

Does not override planner intent

Rhythm informs timing, not action.

This single block prevents massive confusion later, especially for investors or new engineers.

Addition 2 — Relationship to Consolidation & Analytics

Add a short cross-reference (this answers your earlier question implicitly):

Rhythm vs. Consolidation (explicit boundary)

Rhythm workers

Compute state and forecasts

Operate on the present or near future

Are reactive to refresh hints

Consolidation / analytics jobs

Analyze rhythm history

Compute correlations and trends

Promote repeated patterns into structure

Example:

Rhythm forecast produces energy scores

Consolidation later correlates those scores with themes (theme_rhythm_links)

Rhythm feels in the moment.
Consolidation learns over time.

This keeps ownership clean.

How rhythm outputs are used later

brain_state

body_energy, focus, emotion tone

planner alignment

checks task fit vs. energy windows

snapshots / UI

“how today / this week looks”

identity & soul layers

long-horizon rhythm–identity coherence