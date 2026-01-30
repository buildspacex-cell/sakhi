-- Initialise core Sakhi schema: users, journals, embeddings, events, tasks.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text NOT NULL UNIQUE,
    full_name text,
    password_hash text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_email_trgm ON users USING gin (email gin_trgm_ops);

CREATE TABLE IF NOT EXISTS journal_entries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title text,
    content text NOT NULL,
    mood text,
    facets jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE journal_entries
    ADD COLUMN IF NOT EXISTS content text;

ALTER TABLE journal_entries
    ADD COLUMN IF NOT EXISTS facets jsonb DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_journal_entries_user ON journal_entries (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_journal_entries_content_trgm ON journal_entries USING gin (content gin_trgm_ops);

CREATE TABLE IF NOT EXISTS journal_embeddings (
    entry_id uuid PRIMARY KEY REFERENCES journal_entries(id) ON DELETE CASCADE,
    embedding vector(1536) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_journal_embeddings_vector
    ON journal_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE TABLE IF NOT EXISTS events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES users(id) ON DELETE CASCADE,
    entry_id uuid REFERENCES journal_entries(id) ON DELETE SET NULL,
    event_type text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    idempotency_key text UNIQUE,
    response jsonb,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS occurred_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS event_type text DEFAULT 'unknown';

UPDATE events
    SET event_type = COALESCE(event_type, 'unknown');

ALTER TABLE events
    ALTER COLUMN event_type SET NOT NULL;

ALTER TABLE events
    ALTER COLUMN event_type DROP DEFAULT;

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS payload jsonb DEFAULT '{}'::jsonb;

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS idempotency_key text;

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS response jsonb;

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_events_user_at ON events (user_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON events (event_type);
CREATE INDEX IF NOT EXISTS idx_events_idempotency_key ON events (idempotency_key);

CREATE TABLE IF NOT EXISTS tasks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    related_entry_id uuid REFERENCES journal_entries(id) ON DELETE SET NULL,
    title text NOT NULL,
    description text,
    due_at timestamptz,
    status text NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'in_progress', 'completed', 'cancelled')
    ),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks (user_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_at ON tasks (due_at);
CREATE INDEX IF NOT EXISTS idx_tasks_title_trgm ON tasks USING gin (title gin_trgm_ops);
