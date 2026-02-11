-- Migration 0009: Allow 'pacifies' in behavior_log.effect_direction
--
-- The LLM extraction prompt uses "aggravates" or "pacifies" (Ayurvedic terms),
-- but the CHECK constraint only allowed aggravates/balances/neutral.
-- This adds 'pacifies' to the allowed values.

ALTER TABLE behavior_log
  DROP CONSTRAINT IF EXISTS behavior_log_effect_direction_check;

ALTER TABLE behavior_log
  ADD CONSTRAINT behavior_log_effect_direction_check
  CHECK (effect_direction IN ('aggravates', 'pacifies', 'balances', 'neutral') OR effect_direction IS NULL);
