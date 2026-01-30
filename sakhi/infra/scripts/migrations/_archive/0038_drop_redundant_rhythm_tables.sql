-- Migration 0038: Drop redundant rhythm tables
-- These tables were used by turn_rhythm_update worker which has been removed.
-- Rhythm data is now stored in personal_model.rhythm_state via rhythm_forecast worker.

-- Drop tables that are no longer used
DROP TABLE IF EXISTS rhythm_events CASCADE;
DROP TABLE IF EXISTS rhythm_daily_curve CASCADE;
DROP TABLE IF EXISTS rhythm_chronotype CASCADE;
DROP TABLE IF EXISTS rhythm_state CASCADE;

-- Note: persona_traits is kept for now as it may contain useful historical data
