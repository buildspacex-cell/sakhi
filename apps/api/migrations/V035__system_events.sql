CREATE TABLE IF NOT EXISTS system_events (
    id BIGSERIAL PRIMARY KEY,
    ts timestamptz DEFAULT now(),
    person_id uuid,
    layer text,
    event text,
    payload jsonb
);

CREATE INDEX IF NOT EXISTS idx_system_events_person_ts
  ON system_events(person_id, ts DESC);
