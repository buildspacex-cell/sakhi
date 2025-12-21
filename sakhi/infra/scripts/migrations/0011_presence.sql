CREATE TABLE IF NOT EXISTS presence_outreach (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL,
  tier TEXT NOT NULL,
  sent_at TIMESTAMPTZ DEFAULT now(),
  accepted BOOLEAN
);
