-- =============================================================================
-- Phase 2.1: Sakhi Calendar Schema
-- =============================================================================
-- A calendar that understands you - not just when you're free,
-- but when you're at your best for different types of activities.
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- Calendar Events
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS calendar_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id TEXT NOT NULL,  -- Links to personal_model

  -- Basic event info
  title TEXT NOT NULL,
  description TEXT,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ NOT NULL,
  location TEXT,
  location_data JSONB,  -- {address, lat, lng, place_id, type}

  -- Event classification
  event_type TEXT NOT NULL DEFAULT 'personal',
    -- 'meeting', 'social', 'personal', 'work', 'blocked', 'focus_time', 'recovery'
  category TEXT,
    -- 'dinner', 'coffee', 'call', 'deep_work', 'exercise', 'appointment'
  energy_required TEXT DEFAULT 'medium',
    -- 'low', 'medium', 'high' - helps with scheduling
  is_flexible BOOLEAN DEFAULT FALSE,
    -- Can this be moved if needed?

  -- Sakhi-native context
  created_by TEXT NOT NULL DEFAULT 'user',
    -- 'user', 'sakhi_suggestion', 'sakhi_coordination', 'external_sync'
  related_person_ids TEXT[],
    -- Who is this with? References relationship model
  conversation_context TEXT,
    -- What led to this event (journal/conversation reference)
  source_entry_id UUID,
    -- If created from a journal entry

  -- Coordination (for Sakhi-to-Sakhi mesh - Phase 3)
  coordination_id UUID,
  coordination_status TEXT,
    -- 'proposed', 'pending_response', 'confirmed', 'declined', 'cancelled'
  coordination_data JSONB,
    -- {other_sakhi_id, proposal_history, negotiation_notes}

  -- Reflective context (what Sakhi noticed)
  energy_note TEXT,
    -- "You were running high that week"
  relationship_note TEXT,
    -- "First time seeing them in a month"
  pre_event_ritual TEXT,
    -- "You might want 30 min buffer before this"
  post_event_note TEXT,
    -- Added after event: how it went

  -- Recurrence (optional)
  recurrence_rule TEXT,
    -- RRULE format: "FREQ=WEEKLY;BYDAY=MO,WE,FR"
  recurrence_parent_id UUID REFERENCES calendar_events(id),
  recurrence_exception BOOLEAN DEFAULT FALSE,

  -- Status and metadata
  status TEXT DEFAULT 'confirmed',
    -- 'tentative', 'confirmed', 'cancelled'
  reminder_settings JSONB,
    -- {minutes_before: [30, 10], notify_via: ['push', 'email']}
  external_id TEXT,
    -- ID from external calendar if synced
  external_source TEXT,
    -- 'google_calendar', 'apple_calendar', 'outlook'

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_calendar_events_person_time
  ON calendar_events(person_id, start_time);
CREATE INDEX IF NOT EXISTS idx_calendar_events_person_range
  ON calendar_events(person_id, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_calendar_events_type
  ON calendar_events(person_id, event_type);
CREATE INDEX IF NOT EXISTS idx_calendar_events_coordination
  ON calendar_events(coordination_id) WHERE coordination_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_calendar_events_external
  ON calendar_events(person_id, external_id) WHERE external_id IS NOT NULL;


-- ─────────────────────────────────────────────────────────────────────────────
-- Availability Cache
-- ─────────────────────────────────────────────────────────────────────────────
-- Pre-computed availability windows for fast scheduling queries

CREATE TABLE IF NOT EXISTS availability_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id TEXT NOT NULL UNIQUE,

  -- Computed availability windows
  windows JSONB NOT NULL DEFAULT '[]',
    -- [{start, end, quality, reason, energy_level}]
    -- quality: 'preferred', 'available', 'suboptimal', 'emergency_only'

  -- Energy-based windows
  high_energy_windows JSONB,
    -- Best for meetings, important calls, creative work
  low_energy_windows JSONB,
    -- Better for routine tasks, solo work
  recovery_windows JSONB,
    -- Blocked for rest, don't schedule here

  -- By event type
  social_windows JSONB,
    -- Good times for social activities (considers introvert/extrovert)
  focus_windows JSONB,
    -- Good times for deep work
  meeting_windows JSONB,
    -- Acceptable meeting times

  -- Computation metadata
  computed_at TIMESTAMPTZ DEFAULT NOW(),
  valid_until TIMESTAMPTZ,
    -- When this cache expires
  computation_inputs JSONB,
    -- {calendar_event_count, preferences_version, rhythm_state_at}

  -- Cache invalidation
  invalidated_at TIMESTAMPTZ,
  invalidation_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_availability_cache_person
  ON availability_cache(person_id);
CREATE INDEX IF NOT EXISTS idx_availability_cache_valid
  ON availability_cache(person_id, valid_until) WHERE invalidated_at IS NULL;


-- ─────────────────────────────────────────────────────────────────────────────
-- Event Attendees
-- ─────────────────────────────────────────────────────────────────────────────
-- Track who's attending events and their response status

CREATE TABLE IF NOT EXISTS calendar_attendees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID NOT NULL REFERENCES calendar_events(id) ON DELETE CASCADE,

  -- Attendee identification
  person_id TEXT,
    -- If they're a Sakhi user
  relationship_id UUID,
    -- Reference to relationship model
  external_email TEXT,
    -- For non-Sakhi attendees
  display_name TEXT,

  -- Response status
  status TEXT DEFAULT 'pending',
    -- 'pending', 'accepted', 'declined', 'tentative', 'delegated'
  response_at TIMESTAMPTZ,
  response_note TEXT,

  -- Role
  is_organizer BOOLEAN DEFAULT FALSE,
  is_optional BOOLEAN DEFAULT FALSE,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_calendar_attendees_event
  ON calendar_attendees(event_id);
CREATE INDEX IF NOT EXISTS idx_calendar_attendees_person
  ON calendar_attendees(person_id) WHERE person_id IS NOT NULL;


-- ─────────────────────────────────────────────────────────────────────────────
-- Scheduling Requests
-- ─────────────────────────────────────────────────────────────────────────────
-- Track scheduling conversations and their outcomes

CREATE TABLE IF NOT EXISTS scheduling_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id TEXT NOT NULL,

  -- What they asked for
  original_request TEXT NOT NULL,
    -- "Dinner with Alex this week"
  parsed_intent JSONB,
    -- {event_type, participants, timeframe, preferences}

  -- Related entities
  related_person_ids TEXT[],
    -- Who this is about

  -- Proposed options
  proposed_times JSONB,
    -- [{start, end, score, reasoning}]
  selected_option INT,
    -- Which proposal was selected

  -- Outcome
  status TEXT DEFAULT 'pending',
    -- 'pending', 'options_presented', 'confirmed', 'cancelled', 'failed'
  resulting_event_id UUID REFERENCES calendar_events(id),

  -- Conversation tracking
  conversation_turns JSONB,
    -- History of back-and-forth

  created_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_scheduling_requests_person
  ON scheduling_requests(person_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scheduling_requests_status
  ON scheduling_requests(person_id, status);


-- ─────────────────────────────────────────────────────────────────────────────
-- Helper Functions
-- ─────────────────────────────────────────────────────────────────────────────

-- Get events in a time range
CREATE OR REPLACE FUNCTION get_events_in_range(
  p_person_id TEXT,
  p_start TIMESTAMPTZ,
  p_end TIMESTAMPTZ
) RETURNS SETOF calendar_events AS $$
BEGIN
  RETURN QUERY
  SELECT *
  FROM calendar_events
  WHERE person_id = p_person_id
    AND status != 'cancelled'
    AND start_time < p_end
    AND end_time > p_start
  ORDER BY start_time;
END;
$$ LANGUAGE plpgsql;


-- Check if a time slot is free
CREATE OR REPLACE FUNCTION is_time_slot_free(
  p_person_id TEXT,
  p_start TIMESTAMPTZ,
  p_end TIMESTAMPTZ
) RETURNS BOOLEAN AS $$
DECLARE
  conflict_count INT;
BEGIN
  SELECT COUNT(*)
  INTO conflict_count
  FROM calendar_events
  WHERE person_id = p_person_id
    AND status != 'cancelled'
    AND start_time < p_end
    AND end_time > p_start;

  RETURN conflict_count = 0;
END;
$$ LANGUAGE plpgsql;


-- Get upcoming events
CREATE OR REPLACE FUNCTION get_upcoming_events(
  p_person_id TEXT,
  p_limit INT DEFAULT 10
) RETURNS SETOF calendar_events AS $$
BEGIN
  RETURN QUERY
  SELECT *
  FROM calendar_events
  WHERE person_id = p_person_id
    AND status != 'cancelled'
    AND start_time > NOW()
  ORDER BY start_time
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;


-- Invalidate availability cache
CREATE OR REPLACE FUNCTION invalidate_availability_cache(
  p_person_id TEXT,
  p_reason TEXT DEFAULT 'calendar_changed'
) RETURNS VOID AS $$
BEGIN
  UPDATE availability_cache
  SET invalidated_at = NOW(),
      invalidation_reason = p_reason
  WHERE person_id = p_person_id
    AND invalidated_at IS NULL;
END;
$$ LANGUAGE plpgsql;


-- Auto-invalidate cache on calendar changes
CREATE OR REPLACE FUNCTION trigger_invalidate_availability()
RETURNS TRIGGER AS $$
BEGIN
  -- Invalidate cache when events change
  IF TG_OP = 'DELETE' THEN
    PERFORM invalidate_availability_cache(OLD.person_id, 'event_deleted');
    RETURN OLD;
  ELSE
    PERFORM invalidate_availability_cache(NEW.person_id, 'event_' || LOWER(TG_OP));
    RETURN NEW;
  END IF;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for cache invalidation
DROP TRIGGER IF EXISTS calendar_events_invalidate_cache ON calendar_events;
CREATE TRIGGER calendar_events_invalidate_cache
  AFTER INSERT OR UPDATE OR DELETE ON calendar_events
  FOR EACH ROW
  EXECUTE FUNCTION trigger_invalidate_availability();


-- ─────────────────────────────────────────────────────────────────────────────
-- Update timestamp trigger
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_calendar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS calendar_events_update_timestamp ON calendar_events;
CREATE TRIGGER calendar_events_update_timestamp
  BEFORE UPDATE ON calendar_events
  FOR EACH ROW
  EXECUTE FUNCTION update_calendar_timestamp();
