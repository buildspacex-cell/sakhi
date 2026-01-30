(Language-Free Weekly Curation)

Purpose

STEP 8 replaces legacy weekly synthesis with a signals-only aggregation layer.

It prepares facts for reflection —
but never stores language.

Deprecated / Gated

memory_weekly_summaries

memory_semantic_rollups

weekly writes to personal_model.long_term

All gated via feature flags.

Target Table
memory_weekly_signals
CREATE TABLE memory_weekly_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID NOT NULL REFERENCES profiles(user_id),
  week_start DATE NOT NULL,
  week_end DATE NOT NULL,

  episodic_stats JSONB NOT NULL,
  theme_stats JSONB NOT NULL,
  contrast_stats JSONB NOT NULL,
  delta_stats JSONB NOT NULL,

  confidence NUMERIC NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (person_id, week_start)
);

Inputs (Strictly Enforced)

memory_episodic.context_tags

rhythm_weekly_rollups

planner_weekly_pressure

personal_model.longitudinal_state

❌ No STM
❌ No raw text
❌ No planner cache
❌ No identity fields

Stored Signals
Episodic Stats

episode count

salient count

distinct active days

Theme Stats

frequency-weighted themes (keys only)

Contrast Stats

high vs low dimensions

overload / fragmentation markers

Delta Stats

direction only (up | down | flat)

Confidence

derived from upstream confidence + sparsity penalties

Worker
weekly_signals_worker

Weekly cadence

Deterministic

Idempotent

No prose

No LLM

Reflection Contract

Weekly reflection:

reads memory_weekly_signals

renders language at read-time

never persists output

Cross-Step Guarantees (6–8)
Guarantee	Enforced
No identity persistence	✅
No prose persistence	✅
Confidence-aware learning	✅
Time-bounded windows	✅
Deterministic rebuild	✅
Safe over months/years	✅
One-Line Summary

Steps 6–8 establish a learning spine that compounds understanding
without freezing meaning or identity.