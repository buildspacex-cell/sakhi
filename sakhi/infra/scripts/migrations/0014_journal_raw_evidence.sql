-- journal_entries as Raw Evidence Layer
-- Add capture-time, non-interpretive fields
ALTER TABLE journal_entries
  ADD COLUMN IF NOT EXISTS input_type text,              -- text | voice
  ADD COLUMN IF NOT EXISTS client_context jsonb DEFAULT '{}'::jsonb, -- coarse screen/flow/location
  ADD COLUMN IF NOT EXISTS language text,
  ADD COLUMN IF NOT EXISTS timezone text,
  ADD COLUMN IF NOT EXISTS user_tags text[] DEFAULT '{}';

-- Remove derived mood_score from raw table
ALTER TABLE journal_entries
  DROP COLUMN IF EXISTS mood_score;
