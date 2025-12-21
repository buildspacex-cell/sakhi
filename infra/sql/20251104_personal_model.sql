-- Personal model schema enhancements

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'journal_themes' AND column_name = 'window'
    ) THEN
        EXECUTE 'ALTER TABLE journal_themes RENAME COLUMN window TO time_window';
    END IF;
END $$;

ALTER TABLE journal_themes
    ALTER COLUMN metrics SET DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS surfaced_aspects (
    user_id uuid NOT NULL,
    aspect_key text NOT NULL,
    last_surfaced_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, aspect_key)
);

CREATE VIEW IF NOT EXISTS personal_model_themes AS
SELECT
    user_id,
    theme,
    time_window,
    COALESCE((metrics->>'salience')::numeric, 0) AS salience,
    COALESCE((metrics->>'significance')::numeric, 0) AS significance,
    COALESCE((metrics->>'mentions')::int, 0) AS mentions,
    (metrics->>'last_seen')::timestamptz AS last_seen
FROM journal_themes;

CREATE VIEW IF NOT EXISTS personal_model_fatigue AS
SELECT
    user_id,
    aspect_key,
    last_surfaced_at
FROM surfaced_aspects;
