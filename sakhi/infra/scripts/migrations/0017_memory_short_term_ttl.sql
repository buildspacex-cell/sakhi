-- STM hardening: explicit TTL for short-term memory
-- STM is a windowed cache; rows should expire automatically.

DO $$
DECLARE
    ttl_days integer := COALESCE(NULLIF(current_setting('sakhi.stm_ttl_days', true), '')::integer, 14);
BEGIN
    -- Add expires_at column
    ALTER TABLE memory_short_term
        ADD COLUMN IF NOT EXISTS expires_at timestamptz;

    -- Backfill existing rows with created_at + ttl_days (fall back to now()).
    UPDATE memory_short_term
    SET expires_at = COALESCE(expires_at, COALESCE(created_at, NOW()) + ttl_days * INTERVAL '1 day')
    WHERE expires_at IS NULL;

    -- Enforce not null
    ALTER TABLE memory_short_term
        ALTER COLUMN expires_at SET NOT NULL;
END $$;

-- Set default using current_setting so it respects sakhi.stm_ttl_days at runtime.
ALTER TABLE memory_short_term
    ALTER COLUMN expires_at SET DEFAULT (
        NOW() + COALESCE(NULLIF(current_setting('sakhi.stm_ttl_days', true), '')::integer, 14) * INTERVAL '1 day'
    );

CREATE INDEX IF NOT EXISTS idx_memory_short_term_expires_at
    ON memory_short_term (expires_at);
