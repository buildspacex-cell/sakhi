-- Migration: 0031_supabase_auth_grants
-- Purpose: Ensure Supabase roles can access auth_users schema/table under RLS
-- Date: 2026-01-22

-- Allow Supabase roles to use public schema
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;

-- Table privileges are still constrained by RLS policies
GRANT SELECT, INSERT, UPDATE ON auth_users TO anon, authenticated, service_role;

