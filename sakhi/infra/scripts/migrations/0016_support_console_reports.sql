-- 0016_support_console_reports.sql
-- User-consented support diagnostics bundles (metadata-only, no journal/conversation text).

CREATE TABLE IF NOT EXISTS support_debug_reports (
    id                                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id                         UUID NOT NULL,
    support_code                      TEXT NOT NULL UNIQUE,
    issue_summary                     TEXT NOT NULL,
    repro_steps                       TEXT,
    diagnostics_enabled               BOOLEAN NOT NULL DEFAULT false,
    include_conversation_metadata     BOOLEAN NOT NULL DEFAULT false,
    consent_snapshot                  JSONB NOT NULL DEFAULT '{}'::jsonb,
    client_context                    JSONB NOT NULL DEFAULT '{}'::jsonb,
    diagnostics_snapshot              JSONB NOT NULL DEFAULT '{}'::jsonb,
    status                            TEXT NOT NULL DEFAULT 'active',
    expires_at                        TIMESTAMPTZ NOT NULL,
    revoked_at                        TIMESTAMPTZ,
    resolved_at                       TIMESTAMPTZ,
    created_at                        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT support_debug_reports_status_check
        CHECK (status IN ('active', 'revoked', 'resolved', 'expired'))
);

CREATE INDEX IF NOT EXISTS idx_support_debug_reports_person_created
    ON support_debug_reports (person_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_support_debug_reports_status_expires
    ON support_debug_reports (status, expires_at DESC);
