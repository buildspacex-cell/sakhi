-- =============================================================================
-- Phase 1.2: Scheduling Preferences Schema
-- =============================================================================
-- Extends user_profile and adds scheduling-specific tables.
--
-- Purpose:
-- - Store user's scheduling preferences (when, where, how they like to meet)
-- - Enable intelligent calendar and Sakhi-to-Sakhi coordination
-- - Support energy-aware scheduling
-- =============================================================================

-- =============================================================================
-- 1. Scheduling Preferences Table
-- =============================================================================
-- Separate table for detailed scheduling preferences (complements user_profile.preferences)

CREATE TABLE IF NOT EXISTS scheduling_preferences (
    person_id UUID PRIMARY KEY REFERENCES persons(id) ON DELETE CASCADE,

    -- Time preferences
    preferred_times JSONB DEFAULT '{}'::jsonb,
    /* Expected structure:
    {
        "weekday": ["evening"],              -- Preferred times on weekdays
        "weekend": ["late_morning", "afternoon"],
        "specific": {
            "monday": ["morning"],           -- Day-specific overrides
            "friday": ["evening"]
        }
    }
    Valid time slots: early_morning (5-8), morning (8-12), lunch (12-14),
                      afternoon (14-17), evening (17-21), night (21-24)
    */

    avoid_times JSONB DEFAULT '{}'::jsonb,
    /* Expected structure:
    {
        "always": ["early_morning"],         -- Never schedule here
        "weekday": ["lunch"],                -- Protect focus time
        "weekend": [],
        "specific": {
            "sunday": ["evening"]            -- Family time
        },
        "reasons": {
            "early_morning": "Not a morning person",
            "sunday_evening": "Family dinner"
        }
    }
    */

    -- Duration and buffer preferences
    buffer_minutes INTEGER DEFAULT 30,       -- Time between events
    max_events_per_day INTEGER DEFAULT 3,    -- Max scheduled events
    preferred_durations JSONB DEFAULT '{}'::jsonb,
    /* Expected structure:
    {
        "coffee": 45,
        "lunch": 60,
        "dinner": 120,
        "call": 30,
        "meeting": 60,
        "default": 60
    }
    */

    -- Location preferences
    location_preferences JSONB DEFAULT '{}'::jsonb,
    /* Expected structure:
    {
        "default_area": "downtown",
        "max_travel_minutes": 30,
        "home_base": {"address": "...", "lat": ..., "lng": ...},
        "work_location": {"address": "...", "lat": ..., "lng": ...},
        "preferred_spots": [
            {"name": "Rosario's", "type": "restaurant", "for": ["dinner"]},
            {"name": "Blue Bottle", "type": "cafe", "for": ["coffee"]}
        ],
        "avoid_areas": ["airport area"]
    }
    */

    -- Dining preferences
    dining_preferences JSONB DEFAULT '{}'::jsonb,
    /* Expected structure:
    {
        "likes": ["italian", "thai", "mediterranean"],
        "dislikes": ["sushi", "very spicy"],
        "dietary": ["vegetarian", "gluten-free"],
        "favorites": [
            {"name": "Rosario's", "cuisine": "italian", "location": "downtown"},
            {"name": "Pad Thai House", "cuisine": "thai", "location": "midtown"}
        ],
        "price_range": "moderate",           -- budget, moderate, expensive, any
        "ambiance": ["quiet", "casual"]      -- quiet, lively, casual, formal
    }
    */

    -- Energy-aware scheduling (connects to rhythm)
    energy_preferences JSONB DEFAULT '{}'::jsonb,
    /* Expected structure:
    {
        "high_energy_for": ["important meetings", "creative work", "networking"],
        "low_energy_ok": ["casual catch-ups", "routine calls"],
        "protect_recovery": true,            -- Don't schedule during recovery windows
        "respect_rhythm": true               -- Use rhythm_daily_curve data
    }
    */

    -- Communication preferences
    communication_preferences JSONB DEFAULT '{}'::jsonb,
    /* Expected structure:
    {
        "preferred_channels": ["whatsapp", "phone"],
        "avoid_channels": ["email for scheduling"],
        "response_time": "within_day",       -- immediate, within_hour, within_day, relaxed
        "advance_notice": 2                  -- Days of notice preferred for scheduling
    }
    */

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- 2. Helper Functions
-- =============================================================================

-- Get or create scheduling preferences
CREATE OR REPLACE FUNCTION get_scheduling_preferences(p_person_id UUID)
RETURNS scheduling_preferences AS $$
DECLARE
    v_prefs scheduling_preferences;
BEGIN
    SELECT * INTO v_prefs
    FROM scheduling_preferences
    WHERE person_id = p_person_id;

    IF v_prefs IS NULL THEN
        INSERT INTO scheduling_preferences (person_id)
        VALUES (p_person_id)
        RETURNING * INTO v_prefs;
    END IF;

    RETURN v_prefs;
END;
$$ LANGUAGE plpgsql;

-- Update specific preference section
CREATE OR REPLACE FUNCTION update_scheduling_preference(
    p_person_id UUID,
    p_section TEXT,
    p_value JSONB
) RETURNS void AS $$
BEGIN
    -- Ensure record exists
    INSERT INTO scheduling_preferences (person_id)
    VALUES (p_person_id)
    ON CONFLICT (person_id) DO NOTHING;

    -- Update the specific section
    EXECUTE format(
        'UPDATE scheduling_preferences SET %I = $1, updated_at = now() WHERE person_id = $2',
        p_section
    ) USING p_value, p_person_id;
END;
$$ LANGUAGE plpgsql;

-- Check if a time slot is preferred
CREATE OR REPLACE FUNCTION is_preferred_time(
    p_person_id UUID,
    p_day_of_week TEXT,  -- 'monday', 'tuesday', etc.
    p_time_slot TEXT     -- 'morning', 'afternoon', 'evening', etc.
) RETURNS BOOLEAN AS $$
DECLARE
    v_prefs scheduling_preferences;
    v_day_type TEXT;
    v_preferred JSONB;
    v_avoided JSONB;
BEGIN
    SELECT * INTO v_prefs FROM scheduling_preferences WHERE person_id = p_person_id;

    IF v_prefs IS NULL THEN
        RETURN TRUE;  -- No preferences = all times ok
    END IF;

    -- Determine if weekday or weekend
    v_day_type := CASE
        WHEN p_day_of_week IN ('saturday', 'sunday') THEN 'weekend'
        ELSE 'weekday'
    END;

    -- Check if explicitly avoided
    v_avoided := v_prefs.avoid_times;
    IF v_avoided ? 'always' AND v_avoided->'always' ? p_time_slot THEN
        RETURN FALSE;
    END IF;
    IF v_avoided ? v_day_type AND v_avoided->v_day_type ? p_time_slot THEN
        RETURN FALSE;
    END IF;
    IF v_avoided ? 'specific' AND v_avoided->'specific' ? p_day_of_week
       AND v_avoided->'specific'->p_day_of_week ? p_time_slot THEN
        RETURN FALSE;
    END IF;

    -- Check if explicitly preferred (if preferences exist)
    v_preferred := v_prefs.preferred_times;
    IF v_preferred != '{}'::jsonb THEN
        -- Has preferences, check if this time is in them
        IF v_preferred ? 'specific' AND v_preferred->'specific' ? p_day_of_week THEN
            RETURN v_preferred->'specific'->p_day_of_week ? p_time_slot;
        END IF;
        IF v_preferred ? v_day_type THEN
            RETURN v_preferred->v_day_type ? p_time_slot;
        END IF;
        RETURN FALSE;  -- Has preferences but this time isn't in them
    END IF;

    RETURN TRUE;  -- No explicit preferences, time is ok
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 3. Triggers
-- =============================================================================

CREATE OR REPLACE FUNCTION update_scheduling_preferences_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_scheduling_preferences_updated
BEFORE UPDATE ON scheduling_preferences
FOR EACH ROW EXECUTE FUNCTION update_scheduling_preferences_timestamp();

-- =============================================================================
-- 4. Comments
-- =============================================================================

COMMENT ON TABLE scheduling_preferences IS 'User scheduling preferences for intelligent calendar and Sakhi-to-Sakhi coordination';
COMMENT ON FUNCTION is_preferred_time IS 'Check if a specific day/time slot is preferred for the user';
