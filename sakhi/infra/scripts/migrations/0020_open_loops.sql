-- Migration 0020: open_loops
-- Stores extracted open decisions and conversation commitments per person.
-- open_decision: things still being deliberated ("should I take this role?")
-- conversation_commitment: things committed to in conversation ("I'll reach out by Friday")

CREATE TABLE IF NOT EXISTS open_loops (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id       UUID        NOT NULL,
    loop_type       TEXT        NOT NULL CHECK (loop_type IN ('open_decision', 'conversation_commitment')),
    topic           TEXT        NOT NULL,       -- plain-language description of the decision or commitment
    topic_key       TEXT,                       -- optional: maps to a continuity topic anchor
    stance          TEXT,                       -- current optimization target at time of extraction
    status          TEXT        NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'dismissed')),
    source_preview  TEXT,                       -- first 200 chars of source turn text (debug)
    entry_id        TEXT,                       -- source journal/turn entry id
    first_raised_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ,
    resolution_note TEXT
);

CREATE INDEX IF NOT EXISTS open_loops_person_status_idx
    ON open_loops (person_id, status, last_updated_at DESC);

CREATE INDEX IF NOT EXISTS open_loops_person_type_idx
    ON open_loops (person_id, loop_type, status);
