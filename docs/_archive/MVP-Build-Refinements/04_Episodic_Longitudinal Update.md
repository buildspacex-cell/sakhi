Build ID: EPISODE→DELTA-01
Status: Locked
Scope: Learning (Deterministic)
Depends on: Steps 1–4.3a completed

1. Purpose

Define when and how episodic memory updates the continuity model (personal_model.longitudinal_state)—
without prose, without identity claims, and without reflection authority.

This contract ensures:

updates are eligible, bounded, and time-aware

confidence grows slowly and decays naturally

learning is incremental, not re-computed wholesale

2. Authority & Separation (Non-Negotiable)

Episodic memory → source of signals

Learning logic (this contract) → only writer of longitudinal_state

Reflection → read-only consumer

Reflection must never trigger writes here.

3. Eligibility: Which Episodes Can Update Continuity?

An episodic row is eligible only if it meets all of the following:

3.1 Source & Stability

Source table: memory_episodic

Episode is persisted (not STM)

Episode has stable fields (post-ingest mutations complete)

3.2 Signal Presence

At least one eligible signal present (see §4):

body / mind / emotion / energy / work

3.3 Time Window

Episode timestamp within the active learning window:

MVP default: last 14–28 days

Full companion: last 30–120 days

3.4 Dedup & Rate Limit

Same entry_id must not update the same signal twice

Max updates per signal per run: 1

4. Eligible Signals (Base Containers)

Only these base containers may update continuity:

Dimension	Examples (non-exhaustive)
body	fatigue, sleep_quality, physical_discomfort
mind	focus, clarity, rumination
emotion	anxiety, sadness, calm
energy	vitality, burnout_pressure
work	workload_pressure, alignment, recovery

Rules

No identity labels

No diagnoses

Neutral descriptors only

Extensible via new keys (no schema migration required)

5. Signal Extraction (Deterministic)

From each eligible episode, extract signals only (no prose):

{
  "dimension": "emotion",
  "signal_key": "anxiety",
  "polarity": "up | down | neutral",
  "intensity": "low | medium | high",
  "episode_ts": "ISO_TIMESTAMP"
}


Notes:

Polarity expresses direction vs baseline, not emotion valence

Intensity influences volatility, not confidence directly

6. Update Cadence
6.1 MVP

Weekly batch update

Operates on episodes since last run

6.2 Full Companion

Weekly (primary)

Optional monthly consolidation (same rules)

No per-turn updates. No real-time learning.

7. Update Rules (Deterministic Math)

For each (dimension, signal_key):

7.1 Direction

Compute slope across recent eligible episodes

Outcomes: up | down | stable | volatile

7.2 Volatility

Based on sign changes and intensity variance

Buckets: low | medium | high

7.3 Confidence

Starts low (e.g., 0.15)

Increases with:

repeated consistent direction

longer observation window

Decreases with:

high volatility

inactivity (see decay)

Clamped to [0.0, 1.0]

7.4 Time Fields (Mandatory)

observed_over_days or {window.start, window.end}

last_episode_at

last_updated_at

8. Decay & Freshness
8.1 Natural Decay

If no supporting episodes for a signal within:

MVP: 21 days

Full: 45–60 days

Then:

reduce confidence gradually

keep direction but mark as stale implicitly (via time)

8.2 No Hard Deletes

Signals are not deleted automatically; they fade.

9. Write Scope & Idempotency

Writes occur only to:

personal_model.longitudinal_state

Update is idempotent per run

Partial updates allowed (only touched signals change)

10. Prohibitions (Enforced)

Learning logic must never:

write prose

store causes or “why”

label identity (“you are”)

override windows without time math

read or write reflection tables

11. MVP vs Full Companion (Same Contract)
Aspect	MVP	Full Companion
Window	14–28 days	30–120 days
Cadence	Weekly	Weekly + monthly
Confidence ceiling	Lower	Higher
Signal depth	Fewer keys	More keys

Same rules. More evidence.

12. Outcome (What This Enables)

With this contract:

Continuity accumulates safely

Reflections can speak about change

Old interpretations never fossilize

The system remains upgradeable

This is the deterministic spine that powers a wow experience later.