-- Planner foundation: Extend existing goals table and add supporting tables
-- Note: goals table already exists, so we ALTER it to add missing columns

-- Add missing columns to existing goals table (using IF NOT EXISTS pattern)
DO $$
BEGIN
    -- Add type column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'goals' AND column_name = 'type') THEN
        ALTER TABLE goals ADD COLUMN type TEXT DEFAULT 'goal';
    END IF;

    -- Add priority column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'goals' AND column_name = 'priority') THEN
        ALTER TABLE goals ADD COLUMN priority INTEGER DEFAULT 0;
    END IF;

    -- Add due_at column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'goals' AND column_name = 'due_at') THEN
        ALTER TABLE goals ADD COLUMN due_at TIMESTAMPTZ;
    END IF;

    -- Add meta column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'goals' AND column_name = 'meta') THEN
        ALTER TABLE goals ADD COLUMN meta JSONB DEFAULT '{}';
    END IF;

    -- Add created_at column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'goals' AND column_name = 'created_at') THEN
        ALTER TABLE goals ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
    END IF;

    -- Add completed_at column if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'goals' AND column_name = 'completed_at') THEN
        ALTER TABLE goals ADD COLUMN completed_at TIMESTAMPTZ;
    END IF;
END $$;

-- Add indexes if not exist
CREATE INDEX IF NOT EXISTS idx_goals_person ON goals(person_id);
CREATE INDEX IF NOT EXISTS idx_goals_person_status ON goals(person_id, status);
CREATE INDEX IF NOT EXISTS idx_goals_parent ON goals(parent_goal_id);

-- Goal evolution history for tracking changes over time
CREATE TABLE IF NOT EXISTS goal_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    previous_title TEXT,
    revised_title TEXT,
    previous_description TEXT,
    revised_description TEXT,
    reason TEXT,
    evolution_source TEXT CHECK (evolution_source IN ('user', 'system', 'reflection', 'rhythm')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_goal_history_goal ON goal_history(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_history_person ON goal_history(person_id);

-- Intent extractions from journal entries
CREATE TABLE IF NOT EXISTS intent_extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    entry_id UUID,
    intent_text TEXT NOT NULL,
    intent_type TEXT CHECK (intent_type IN ('goal', 'task', 'concern', 'question', 'commitment', 'aspiration')),
    confidence FLOAT DEFAULT 0.5,
    linked_goal_id UUID REFERENCES goals(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'rejected', 'converted')),
    meta JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_intent_extractions_person ON intent_extractions(person_id);
CREATE INDEX IF NOT EXISTS idx_intent_extractions_status ON intent_extractions(person_id, status);

-- Goal suggestions (proposed by system, awaiting user confirmation)
CREATE TABLE IF NOT EXISTS goal_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    supporting_intent_ids UUID[] DEFAULT '{}',
    occurrence_count INTEGER DEFAULT 1,
    confidence FLOAT DEFAULT 0.5,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected', 'deferred')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    responded_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_goal_suggestions_person ON goal_suggestions(person_id);
CREATE INDEX IF NOT EXISTS idx_goal_suggestions_status ON goal_suggestions(person_id, status);
