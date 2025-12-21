CREATE TABLE IF NOT EXISTS body_signals (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('sleep','energy','meal','movement')),
  value JSONB NOT NULL,
  at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS body_signals_user_kind_at
ON body_signals(user_id, kind, at DESC);
