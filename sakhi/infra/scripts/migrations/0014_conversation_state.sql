CREATE TABLE IF NOT EXISTS dialog_states (
  conversation_id TEXT PRIMARY KEY,
  user_id UUID,
  state JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  kind TEXT NOT NULL,
  summary TEXT NOT NULL,
  importance NUMERIC DEFAULT 0.0,
  source_conversation TEXT,
  source_message_id TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS user_memories_user_idx ON user_memories(user_id);
CREATE INDEX IF NOT EXISTS user_memories_kind_idx ON user_memories(kind);
