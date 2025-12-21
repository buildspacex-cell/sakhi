-- Build 41 – Deep Context Recall
-- Goal: perfect long-term conversational memory via stitched recaps and life-event linking.
-- Tables:
--   context_recalls           : stitched context per turn/thread with multi-vector payloads
--   life_event_links          : links recall items to inferred life events/themes
--   thread_continuity_markers : mark long-running conversation threads for stable persona recall
--   context_compact_summaries : compact summaries for fast context injection

CREATE TABLE IF NOT EXISTS context_recalls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    turn_id UUID,
    thread_id UUID,
    stitched_summary TEXT NOT NULL,
    compact JSONB NOT NULL DEFAULT '{}'::jsonb,
    vectors JSONB NOT NULL DEFAULT '{}'::jsonb, -- e.g., {short_term: [], episodic: [], semantic: []}
    signals JSONB NOT NULL DEFAULT '{}'::jsonb, -- e.g., {mood: "", intent: "", slots: []}
    confidence NUMERIC NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (person_id, turn_id)
);

CREATE INDEX IF NOT EXISTS context_recalls_person_idx
    ON context_recalls (person_id, created_at DESC);

CREATE INDEX IF NOT EXISTS context_recalls_thread_idx
    ON context_recalls (person_id, thread_id, created_at DESC);

CREATE TABLE IF NOT EXISTS life_event_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    recall_id UUID NOT NULL REFERENCES context_recalls (id) ON DELETE CASCADE,
    event_label TEXT NOT NULL,
    weight NUMERIC NOT NULL DEFAULT 0.0,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS life_event_links_person_idx
    ON life_event_links (person_id, created_at DESC);

CREATE TABLE IF NOT EXISTS thread_continuity_markers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    thread_id UUID NOT NULL,
    continuity_hint TEXT,
    persona_stability JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_turn_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (person_id, thread_id)
);

CREATE INDEX IF NOT EXISTS thread_continuity_person_idx
    ON thread_continuity_markers (person_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS context_compact_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    recall_id UUID REFERENCES context_recalls (id) ON DELETE CASCADE,
    thread_id UUID,
    compact JSONB NOT NULL DEFAULT '{}'::jsonb,
    tokens_est INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS context_compact_person_idx
    ON context_compact_summaries (person_id, created_at DESC);

