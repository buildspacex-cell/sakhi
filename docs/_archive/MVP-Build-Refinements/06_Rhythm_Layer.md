Capacity Patterns Over Time (Deterministic, Non-Interpretive)

Status: Implemented & Locked
Scope: Rhythm ingestion, safety gating, weekly rollups
Depends on:

STEP 1 — Journals (Raw Evidence)

STEP 2 — Short-Term Memory (Bounded Window)

STEP 3 — Episodic Memory (What Happened)

STEP 4 — Reflection & Longitudinal Learning

1. Purpose of STEP 5

STEP 5 enables Sakhi to talk about rhythm as patterns of capacity, not moods, labels, or advice.

It answers:

“How does this person’s capacity fluctuate over time?”

This includes:

physical energy cycles

cognitive focus windows

emotional variability and recovery

psycho-energetic vitality

Crucially, STEP 5 does not explain why these patterns exist.
It only measures how they move.

2. Core Principles (Non-Negotiable)

Rhythm is physics, not psychology

No LLM writes to rhythm state

No narrative or advice is persisted

Patterns are stored; meaning is generated later

Reflection may speak about rhythm, but rhythm never speaks for itself

3. Rhythm Channels (Conceptual Model)

Rhythm is modeled across four independent capacity channels:

Channel	What It Represents	What It Is NOT
Body	Physical energy, fatigue, recovery	Emotion
Mind	Cognitive bandwidth, focus tolerance	Motivation
Emotion	Variability, reactivity, recovery latency	Mood labels
Energy	Felt vitality, drive, engagement	Physical stamina

Work is a context, not a rhythm channel.
It emerges from the interaction of mind + energy + body under load.

4. Tables in the Rhythm Layer
4.1 rhythm_events (Append-Only Signal Log)

Purpose:
Raw-ish, timestamped rhythm events. This is the ground truth history.

CREATE TABLE rhythm_events (
  id UUID PRIMARY KEY,
  person_id UUID NOT NULL,
  event_ts TIMESTAMPTZ DEFAULT now(),
  kind TEXT,
  payload JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);


Characteristics

Append-only

No overwrites

No prose required

Safe for recomputation

Status: ✅ Canon-safe

4.2 rhythm_daily_curve (Deterministic Daily Capacity Curve)

Purpose:
Stores a per-day capacity curve (96 × 15-minute slots).

CREATE TABLE rhythm_daily_curve (
  id UUID PRIMARY KEY,
  person_id UUID NOT NULL,
  day_scope DATE NOT NULL DEFAULT current_date,
  slots JSONB NOT NULL,
  confidence NUMERIC DEFAULT 0.0,
  source TEXT DEFAULT 'worker',
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (person_id, day_scope)
);


Characteristics

Deterministic

Overwrites per day (acceptable)

Numeric only

No interpretation

Status: ⚠️ Overwrite snapshot, but structurally sound

4.3 rhythm_state (Current Snapshot — Read-Only for Reflection)

Purpose:
Represents the latest rhythm snapshot for UI and immediate context.

CREATE TABLE rhythm_state (
  person_id UUID PRIMARY KEY,
  body_energy NUMERIC DEFAULT 0.5,
  mind_focus NUMERIC DEFAULT 0.5,
  emotion_tone TEXT DEFAULT 'neutral',
  fatigue_level NUMERIC DEFAULT 0.0,
  stress_level NUMERIC DEFAULT 0.0,
  next_peak TIMESTAMPTZ,
  next_lull TIMESTAMPTZ,
  payload JSONB DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ DEFAULT now()
);


Characteristics

Overwrite-prone

Presentation-oriented

Must not be treated as historical truth

Status: ⚠️ Snapshot only (not learning)

4.4 rhythm_weekly_rollups ⭐ (Added in STEP 5)

Purpose:
Durable, deterministic weekly rhythm patterns used by reflection.

CREATE TABLE rhythm_weekly_rollups (
  id UUID PRIMARY KEY,
  person_id UUID NOT NULL,
  week_start DATE NOT NULL,
  week_end DATE NOT NULL,
  rollup JSONB NOT NULL,
  confidence NUMERIC DEFAULT 0.0,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (person_id, week_start)
);


Characteristics

One row per person per week

Idempotent

No prose

No interpretation

Authoritative for weekly reflection

Status: ✅ Canon-safe, authoritative

5. Canonical Weekly Rollup JSON Contract

Stored in rhythm_weekly_rollups.rollup:

{
  "body": {
    "avg_level": 0.61,
    "slope": "down",
    "volatility": "medium",
    "peak_windows": ["morning"],
    "dip_windows": ["evening"],
    "recovery_latency": "long",
    "confidence": 0.72
  },
  "mind": { "...": "..." },
  "emotion": { "...": "..." },
  "energy": { "...": "..." }
}

Explicit Prohibitions

❌ prose

❌ causes

❌ advice

❌ diagnoses

❌ identity claims

6. Rhythm Workers & Authority
6.1 run_rhythm_engine (Existing)

Writes

rhythm_daily_curve

rhythm_state

rhythm_events

Properties

Deterministic

No LLM

Snapshot-oriented

Status: ⚠️ Acceptable as ingestion, not learning

6.2 weekly_rhythm_rollup_worker ⭐ (Added)

File

sakhi/apps/worker/tasks/weekly_rhythm_rollup_worker.py


Reads

rhythm_daily_curve

rhythm_events

Writes

rhythm_weekly_rollups

Guarantees

No LLM

No prose

No other table writes

Deterministic & idempotent

Status: ✅ Sole authority for weekly rhythm patterns

7. Safety Gates (Damage Containment)

To prevent interpretive contamination, STEP 5 introduces rhythm safety flags.

Config Flags
ENABLE_RHYTHM_WORKERS=true
ENABLE_RHYTHM_FORECAST_WRITES=false

Effect

❌ LLM rhythm forecasts disabled

❌ Narrative overwrites blocked

✅ Deterministic ingestion preserved

✅ Weekly rollups protected

This mirrors the safeguards from STEP 4.

8. How Weekly Reflection Uses Rhythm

Weekly reflection reads:

memory_episodic → what happened

personal_model.longitudinal_state → what’s changing

rhythm_weekly_rollups → how capacity fluctuated

It may say:

“Your energy tended to dip mid-week, and emotional variability increased.”

This language is:

grounded in structure

reversible

confidence-gated

human-sounding without being speculative

9. MVP vs Full Product
MVP (Weekly Reflection)

7-day rollups

low confidence

cautious language

Full Companion

multi-week comparisons

higher confidence

richer pattern language

Same architecture. No rewrites.

10. One-Sentence Summary

Rhythm measures how capacity moves.
Reflection decides what it means — temporarily.

STEP 5 completes Sakhi’s ability to speak about time, change, and capacity with clarity and trust.