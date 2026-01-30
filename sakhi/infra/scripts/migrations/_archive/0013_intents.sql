CREATE TABLE IF NOT EXISTS intents (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL,
  source_entry_id BIGINT REFERENCES journal_entries(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  raw_input TEXT,
  intent_type TEXT NOT NULL,
  domain TEXT,
  timeline TEXT NOT NULL DEFAULT 'none',
  target_date DATE,
  priority SMALLINT,
  status TEXT NOT NULL DEFAULT 'draft',
  clarity_score NUMERIC DEFAULT 0.0,
  user_permission BOOLEAN DEFAULT FALSE,
  proposed_plan JSONB,
  context_snapshot JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS intents_user_idx ON intents(user_id);
CREATE INDEX IF NOT EXISTS intents_status_idx ON intents(status);
