-- Migration: 0030_supabase_auth_policies
-- Purpose: Harden auth_users with RLS and user-scoped policies
-- Date: 2026-01-22

-- Enable row level security on auth_users
ALTER TABLE auth_users ENABLE ROW LEVEL SECURITY;

-- Allow an authenticated user to see their own auth_users row
CREATE POLICY auth_users_select_own
  ON auth_users
  FOR SELECT
  USING (auth.uid() = supabase_user_id);

-- Allow an authenticated user to insert their own auth_users row
CREATE POLICY auth_users_insert_own
  ON auth_users
  FOR INSERT
  WITH CHECK (auth.uid() = supabase_user_id);

-- Allow an authenticated user to update their own auth_users row
CREATE POLICY auth_users_update_own
  ON auth_users
  FOR UPDATE
  USING (auth.uid() = supabase_user_id)
  WITH CHECK (auth.uid() = supabase_user_id);

