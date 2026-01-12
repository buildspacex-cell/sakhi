“How does the system notice repetition and momentum over time without reacting turn-by-turn?”

Below is a documentation-ready section, written in the same architectural style as the Brain Engine and Memory Spine sections, explicitly answering when, why, and what.

Section 10 — Consolidation & Aggregation

(Periodic Pattern Promotion & Short-Horizon Summaries)

Purpose of this layer

The Consolidation & Aggregation layer performs slow, periodic sense-making across recent history.

Its role is to:

detect recurring signals that deserve promotion

activate goals that show real momentum

maintain lightweight, recent summaries for fast access

This layer exists to ensure that patterns emerge from repetition, not from single turns.

When it runs

Executed by a periodic worker loop in jobs/runner.py

Runs consolidate_person for each person_id with journal activity

Scheduled on a timer:

CONSOLIDATOR_INTERVAL_MINUTES

Defaults to daily

This job is:

independent of live turns

non-interruptive

non-user-facing

What consolidate_person does

consolidate_person performs two promotion tasks based on recent evidence.

1. Tag → Theme promotion

Input window

Journal entries from the last 30 days

Logic

Counts tag occurrences across entries

Any tag appearing ≥ 3 times is promoted

Write

Inserts into themes:

person_id

name (tag name)

scope

signals (supporting evidence)

Design intent

Themes represent persistent areas of attention, not momentary interests

Promotion requires repetition across time

A theme is not declared — it is earned.

2. Goal activation (momentum detection)

Input window

Journal entries from the last 14 days

Logic

Finds goals with:

status = "proposed"

whose title appears ≥ 3 times in journal text

Write

Updates those goals to:

status = "active"

Design intent

Goals become active when the user repeatedly references them

This avoids premature activation while respecting expressed momentum

The system notices when a goal stops being hypothetical.

What update_short_horizon does

update_short_horizon builds a 7-day snapshot optimized for fast reads and analytics.

Input window

Journal entries from the past 7 days

Aggregations computed

recent_layers

Count of entries by layer (journal, conversation, etc.)

recent_tags

Top tags with occurrence counts

avg_mood_7d

Average mood_score over 7 days

recent_intents

Currently left empty (placeholder)

open_questions

Currently left empty (placeholder)

Write behavior

Upserts one row per person into:

short_horizon


Includes:

aggregated fields

asof timestamp (current)

Why this layer exists (design rationale)
1. Pattern recognition without latency

Heavy aggregation is moved off the turn path

Live interaction remains fast

Patterns are detected asynchronously

2. Promotion requires repetition

No single entry can:

create a theme

activate a goal

Repetition across days is required

This protects against:

overfitting

emotional spikes

noise

3. Fast access to “recent state”

The short_horizon table allows:

dashboards

summaries

analytics

insight generation

…without re-scanning raw journals every time.

What this layer explicitly does not do

It does not generate user-facing language

It does not infer identity or intent

It does not act in real time

It does not override planner decisions

It does not create new goals

It promotes and summarizes, nothing more.

How its outputs are used later

Themes

Feed identity, narrative, and reflection layers

Represent stable areas of life focus

Activated goals

Appear in planner summaries and brain state

Influence priority and alignment logic

Short-horizon aggregates

Used for analytics and snapshot views

Read by insight and presence layers for recent context

Architectural stance

The system listens fast — but decides slowly.

Consolidation ensures that:

meaning emerges from time

momentum is respected

intelligence stays grounded in evidence

One-line summary

Consolidation turns repetition into structure — without interrupting the present.

Short-Horizon Aggregation Helper
short_horizon_aggregator.py

What it is

A helper used by the Consolidation & Aggregation job to maintain a fast, recent snapshot of a person’s activity.

When it runs

Invoked from the periodic consolidation loop in jobs/runner.py

Runs off the turn flow (never inline with user interaction)

Executes on the same schedule as consolidation (default: daily)

What it aggregates

Looks at the last 7 days of journal_entries for a person and computes:

recent_layers

Count of entries grouped by layer (journal, conversation, etc.)

recent_tags

Top tags with occurrence counts

avg_mood_7d

Average mood_score across the 7-day window

recent_intents

Currently left empty (placeholder)

open_questions

Currently left empty (placeholder)

Persistence behavior

Upserts a single row per person into:

short_horizon


Stores:

the aggregated fields

an asof timestamp representing when the snapshot was computed

Each run overwrites the prior snapshot rather than appending history.

Why this exists (in the consolidation story)

Keeps a quick, recent summary ready for:

analytics

dashboards

insight generation

presence logic

Avoids rescanning raw journals on every read

Ensures recent state is available cheaply, without touching live turns

This is a snapshot, not memory.
It summarizes recent reality without becoming long-term truth.

How it fits the overall storyline

This helper supports the slow intelligence loop:

Journals create evidence →
Consolidation notices repetition →
Short-horizon aggregation keeps a rolling snapshot.

It complements:

themes (longer-term structure)

goal activation (momentum)

without adding inference or behavior.

Theme–Rhythm Correlation Analytics

What this is

A background analytics step that strengthens the relationship between themes and rhythm outcomes using observed data.

When it runs

Executed via the analytics queue

Runs asynchronously and periodically

Never part of the turn flow

How it works

Looks at approximately the last 21 days of data

Joins:

theme_states (clarity, engagement around themes)

rhythm_forecasts (predicted energy levels)

Groups by:

person

theme

What it computes

Correlation between:

theme clarity

predicted energy

Simple directional trends:

clarity_trend

energy_trend

Sample count

What gets written

Upserts into:

theme_rhythm_links


with:

correlation

clarity_trend

energy_trend

samples

updated_at

What it does not do

Does not generate recommendations

Does not reschedule tasks

Does not change planner state

Does not affect live responses

Why this exists

Moves rhythm–theme understanding from keyword hits to observed correlation

Allows rhythm intelligence to become:

data-backed

trend-aware

longitudinal

Rhythm understanding matures from signals → correlations.

How it’s used later

Read by rhythm forecast workers

Used in analytics and system audits

Can inform future alignment insights without enforcing behavior

Early rhythm signals are heuristic; long-term rhythm understanding is analytical.