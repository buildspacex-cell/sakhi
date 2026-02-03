-- Extensible Preference Framework Tables
-- Domain-agnostic preference storage with flexible schema

-- Main preference profile storage (JSONB for flexibility)
CREATE TABLE IF NOT EXISTS preference_profiles (
    person_id TEXT PRIMARY KEY,
    profile_data JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for querying specific domains within JSONB
CREATE INDEX IF NOT EXISTS idx_pref_profiles_domains
    ON preference_profiles USING GIN ((profile_data -> 'domains'));

-- Preference learning event log (audit trail)
CREATE TABLE IF NOT EXISTS preference_events (
    id SERIAL PRIMARY KEY,
    person_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    dimension TEXT NOT NULL,
    value FLOAT NOT NULL,
    evidence_type TEXT NOT NULL,
    source_text TEXT,
    context JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pref_events_person ON preference_events(person_id);
CREATE INDEX IF NOT EXISTS idx_pref_events_domain ON preference_events(person_id, domain);
CREATE INDEX IF NOT EXISTS idx_pref_events_time ON preference_events(created_at DESC);

-- Domain definitions (allows dynamic domain registration)
CREATE TABLE IF NOT EXISTS preference_domains (
    domain_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    description TEXT,
    standard_dimensions JSONB DEFAULT '[]',
    icon TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed standard domains
INSERT INTO preference_domains (domain_id, display_name, description, standard_dimensions) VALUES
    ('food', 'Food & Dining', 'Food taste, texture, cuisine preferences',
     '["spiciness", "sweetness", "saltiness", "sourness", "temperature", "texture_crunchiness", "portion_size", "presentation", "authenticity", "health_focus"]'),
    ('fragrance', 'Fragrance', 'Scent and perfume preferences',
     '["woodiness", "florals", "citrus", "musk", "spice", "freshness", "sweetness", "smokiness", "longevity_preference"]'),
    ('travel', 'Travel', 'Travel style and destination preferences',
     '["adventure_level", "comfort_level", "cultural_immersion", "nature_focus", "urban_preference", "luxury_level", "spontaneity"]'),
    ('fashion', 'Fashion', 'Clothing and style preferences',
     '["formality", "color_boldness", "pattern_complexity", "fit_preference", "comfort_vs_style", "sustainability_focus"]'),
    ('wellness', 'Wellness', 'Health and wellness preferences',
     '["exercise_intensity", "meditation_interest", "sleep_priority", "nutrition_focus", "alternative_medicine_openness"]'),
    ('environment', 'Environment', 'Room and atmosphere preferences',
     '["temperature_warm", "lighting_bright", "noise_tolerance", "clutter_tolerance", "nature_elements", "minimalism"]'),
    ('social', 'Social', 'Social interaction preferences',
     '["group_size_preference", "introversion_extroversion", "conversation_depth", "new_people_openness"]'),
    ('media', 'Media & Entertainment', 'Content and entertainment preferences',
     '["complexity", "emotional_intensity", "humor_preference", "length_tolerance", "foreign_content_openness"]')
ON CONFLICT (domain_id) DO NOTHING;

-- Cross-domain trait definitions
CREATE TABLE IF NOT EXISTS preference_traits (
    trait_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    description TEXT,
    related_domains JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed common cross-domain traits
INSERT INTO preference_traits (trait_id, display_name, description, related_domains) VALUES
    ('minimalist', 'Minimalist', 'Preference for simplicity and clean aesthetics',
     '["environment", "fashion", "food", "media"]'),
    ('adventurous', 'Adventurous', 'Openness to new and unusual experiences',
     '["food", "travel", "social", "media"]'),
    ('traditional', 'Traditional', 'Preference for classic, time-tested options',
     '["food", "fashion", "wellness", "social"]'),
    ('health_conscious', 'Health Conscious', 'Priority on health and wellness',
     '["food", "wellness", "environment", "travel"]'),
    ('luxury_oriented', 'Luxury Oriented', 'Preference for premium experiences',
     '["travel", "fashion", "food", "environment"]'),
    ('eco_conscious', 'Eco Conscious', 'Priority on sustainability and environment',
     '["fashion", "travel", "food", "environment"]')
ON CONFLICT (trait_id) DO NOTHING;

-- Item-preference match history (for learning what works)
CREATE TABLE IF NOT EXISTS preference_match_history (
    id SERIAL PRIMARY KEY,
    person_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    item_id TEXT,
    item_description TEXT,
    predicted_score FLOAT,
    actual_feedback FLOAT,  -- User's actual rating/feedback
    feedback_type TEXT,     -- "explicit", "implicit", "rejection"
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_match_history_person ON preference_match_history(person_id);
CREATE INDEX IF NOT EXISTS idx_match_history_domain ON preference_match_history(person_id, domain);
