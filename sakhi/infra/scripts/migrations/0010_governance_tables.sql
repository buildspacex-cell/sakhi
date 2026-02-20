-- 0010_governance_tables.sql
-- Governance event ledger, per-person constraints, and objective versioning.
-- Supports kala GovernanceGate integration with Sakhi conversation pipeline.

-- 1. Governance event ledger (append-only, maps to kala.ledger.Event)
CREATE TABLE IF NOT EXISTS governance_events (
    id          TEXT PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    person_id   UUID NOT NULL,
    event_type  TEXT NOT NULL,        -- proposed, validated, committed, rejected, reconciled, observed
    action      TEXT NOT NULL,        -- semantic label: suggest_meditation, suggest_exercise, conversation_turn
    actor       TEXT NOT NULL DEFAULT 'system',  -- llm, user, system, governance
    data        JSONB NOT NULL DEFAULT '{}',
    reason      TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_gov_events_person
    ON governance_events (person_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_gov_events_action
    ON governance_events (person_id, action, event_type, ts DESC);

-- 2. Per-person governance constraints (maps to kala.constraints.Constraint)
CREATE TABLE IF NOT EXISTS governance_constraints (
    id              TEXT NOT NULL,
    person_id       UUID NOT NULL,
    constraint_type TEXT NOT NULL,     -- time_boundary, value_alignment, drift_threshold, commitment, capacity, custom
    field           TEXT NOT NULL,     -- dotted path into action_context
    operator        TEXT NOT NULL,     -- lt, gt, lte, gte, eq, neq, in, not_in, between, contains, not_contains
    value           JSONB NOT NULL,    -- expected value (JSON-encoded)
    description     TEXT NOT NULL DEFAULT '',
    source          TEXT NOT NULL DEFAULT '',   -- "objective:sleep-health:v1", "system", "user_preference"
    priority        INT NOT NULL DEFAULT 2,     -- 1=SOFT, 2=MEDIUM, 3=HARD
    active          BOOLEAN NOT NULL DEFAULT true,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, person_id)
);

CREATE INDEX IF NOT EXISTS idx_gov_constraints_person
    ON governance_constraints (person_id) WHERE active = true;

-- 3. Governance objectives with version lineage (maps to kala.objectives.ObjectiveVersion)
CREATE TABLE IF NOT EXISTS governance_objectives (
    objective_id    TEXT NOT NULL,
    version         INT NOT NULL,
    person_id       UUID NOT NULL,
    ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    data            JSONB NOT NULL DEFAULT '{}',
    source          TEXT NOT NULL DEFAULT '',   -- user_input, feedback, crystallization, onboarding
    reason          TEXT NOT NULL DEFAULT '',   -- why this version was created
    parent_version  INT,
    PRIMARY KEY (objective_id, version, person_id)
);

CREATE INDEX IF NOT EXISTS idx_gov_objectives_person
    ON governance_objectives (person_id, objective_id, version DESC);
