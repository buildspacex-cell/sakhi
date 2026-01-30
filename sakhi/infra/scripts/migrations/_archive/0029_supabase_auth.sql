-- Migration: 0029_supabase_auth
-- Purpose: Link Supabase Auth users with Sakhi person records
-- Date: 2026-01-22

-- =============================================================================
-- AUTH USERS TABLE
-- =============================================================================
-- This table links Supabase Auth users (auth.users) to our person_id system.
-- When a user signs in with Google, we create/update this record and use
-- the id as person_id throughout the app.

CREATE TABLE IF NOT EXISTS auth_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Supabase auth.users.id (from Google OAuth)
    supabase_user_id UUID UNIQUE,
    -- User's email from Google
    email TEXT NOT NULL UNIQUE,
    -- Display name from Google profile
    full_name TEXT,
    -- Avatar URL from Google
    avatar_url TEXT,
    -- When the user first signed up
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Last sign-in timestamp
    last_sign_in_at TIMESTAMPTZ,
    -- Onboarding completion status
    onboarding_completed_at TIMESTAMPTZ,
    -- Soft delete
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_auth_users_email ON auth_users (email);
CREATE INDEX IF NOT EXISTS idx_auth_users_supabase_id ON auth_users (supabase_user_id);

COMMENT ON TABLE auth_users IS
'Links Supabase Auth users to Sakhi person records. The id column IS the person_id used throughout the app.';

-- =============================================================================
-- ENSURE PERSONAL_MODEL CAN REFERENCE AUTH_USERS
-- =============================================================================
-- The personal_model table uses person_id which should match auth_users.id

-- Add a soft reference comment (not a hard FK to avoid migration issues)
COMMENT ON COLUMN personal_model.person_id IS
'References auth_users.id for authenticated users, or a UUID for legacy/demo users.';
