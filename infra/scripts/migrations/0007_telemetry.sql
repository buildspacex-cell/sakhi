-- Request/response telemetry (PII-scrubbed payload snapshots)
CREATE TABLE IF NOT EXISTS request_logs (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID,
  method TEXT,
  path TEXT,
  status INT,
  duration_ms INT,
  ip INET,
  headers JSONB,
  body JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- LLM token usage + cost
CREATE TABLE IF NOT EXISTS token_usage (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID,
  model TEXT,
  tokens_in INT,
  tokens_out INT,
  cost_usd NUMERIC,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Safety incidents (prompt injection, policy violations, rate limits, etc.)
CREATE TABLE IF NOT EXISTS incidents (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID,
  kind TEXT,
  severity TEXT,
  path TEXT,
  detail TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Feature flags + pilot users
CREATE TABLE IF NOT EXISTS feature_flags (
  key TEXT PRIMARY KEY,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  meta JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS pilot_users (
  user_id UUID PRIMARY KEY,
  api_key TEXT UNIQUE NOT NULL,
  flags JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Quick defaults
INSERT INTO feature_flags(key, enabled) VALUES
  ('pilot_mode', TRUE)
ON CONFLICT (key) DO NOTHING;
