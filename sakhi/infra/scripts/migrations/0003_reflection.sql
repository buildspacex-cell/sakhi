CREATE TABLE IF NOT EXISTS reflections (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('daily', 'weekly')),
  theme TEXT DEFAULT 'general',
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS reflections_user_created_idx
ON reflections(user_id, created_at DESC);
