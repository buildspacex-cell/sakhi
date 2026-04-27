-- Migration 0019: continuity_stance_history
-- Tracks per-person, per-topic optimization stance over time.
-- Used to detect when a person shifts what they're optimizing for
-- (e.g. quality → speed, stability → impact) — the "What Changed" signal.

CREATE TABLE IF NOT EXISTS continuity_stance_history (
    id          BIGSERIAL PRIMARY KEY,
    person_id   UUID        NOT NULL,
    topic_key   TEXT        NOT NULL,
    stance      TEXT        NOT NULL,   -- one of 8 targets: quality, speed, stability, relationships, autonomy, learning, impact, simplicity
    confidence  FLOAT       NOT NULL DEFAULT 0.5,
    entry_id    TEXT,                   -- source journal/turn entry
    source_preview TEXT,               -- first 200 chars of source text (debug only)
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS continuity_stance_history_person_topic_time_idx
    ON continuity_stance_history (person_id, topic_key, detected_at DESC);
