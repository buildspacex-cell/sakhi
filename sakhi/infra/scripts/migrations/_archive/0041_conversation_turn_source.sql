-- Migration: Add source column to conversation_turns
-- Tracks whether input came from voice or text

ALTER TABLE conversation_turns
ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'text';

-- Add check constraint for valid source values
ALTER TABLE conversation_turns
ADD CONSTRAINT conversation_turns_source_check
CHECK (source IN ('text', 'voice'));

-- Add index for analytics queries
CREATE INDEX IF NOT EXISTS idx_conversation_turns_source
ON conversation_turns (source);

COMMENT ON COLUMN conversation_turns.source IS 'Input source: text or voice';
