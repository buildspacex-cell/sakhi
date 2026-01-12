-- Reflection Inquiry storage (turns + embeddings)
-- Deterministic, user-initiated inquiry over reflections.

CREATE TABLE IF NOT EXISTS reflection_inquiry_turns (
    id uuid PRIMARY KEY,
    person_id uuid NOT NULL,
    reflection_id text,
    reflection_kind text NOT NULL,
    window_days int NOT NULL DEFAULT 7,
    question_text text NOT NULL,
    answer_text text NOT NULL,
    answer_mode text NOT NULL, -- explain | meaning | advice
    sources_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reflection_inquiry_turns_person_created
    ON reflection_inquiry_turns (person_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reflection_inquiry_turns_reflection
    ON reflection_inquiry_turns (reflection_id);

CREATE TABLE IF NOT EXISTS reflection_inquiry_embeddings (
    id uuid PRIMARY KEY,
    turn_id uuid NOT NULL REFERENCES reflection_inquiry_turns(id) ON DELETE CASCADE,
    person_id uuid NOT NULL,
    content_kind text NOT NULL, -- question | answer | combined
    content_text text NOT NULL,
    embedding_vec vector(1536) NOT NULL,
    content_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reflection_inquiry_embeddings_person
    ON reflection_inquiry_embeddings (person_id);

CREATE INDEX IF NOT EXISTS idx_reflection_inquiry_embeddings_vector
    ON reflection_inquiry_embeddings USING ivfflat (embedding_vec vector_cosine_ops)
    WITH (lists = 100);
