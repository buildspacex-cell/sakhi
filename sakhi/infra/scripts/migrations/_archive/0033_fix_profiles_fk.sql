-- Migration: 0033_fix_profiles_fk
-- Purpose: Change profiles.user_id FK from auth.users to auth_users
-- This allows using our internal auth_users.id as person_id consistently
-- Date: 2026-01-26

-- Drop the existing FK constraint to auth.users
ALTER TABLE profiles
DROP CONSTRAINT IF EXISTS profiles_user_id_fkey;

-- Add new FK constraint to auth_users
ALTER TABLE profiles
ADD CONSTRAINT profiles_user_id_fkey
FOREIGN KEY (user_id) REFERENCES auth_users(id)
ON DELETE CASCADE;

-- Comment explaining the change
COMMENT ON CONSTRAINT profiles_user_id_fkey ON profiles IS
'FK to auth_users.id (our internal user table), not auth.users (Supabase auth table)';
