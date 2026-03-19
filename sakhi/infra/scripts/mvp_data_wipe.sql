-- ============================================================================
-- Sakhi MVP Data Wipe (v3 — full wipe, no users preserved)
-- Purpose : Truncate ALL data in every public-schema table.
--           Schema (tables, indexes, constraints) is kept intact.
--           auth.* is NOT touched here — delete auth users in Supabase Dashboard.
--
-- HOW TO RUN
--   1. Open Supabase SQL Editor for project yiitskcbrcbgbsumxxrx
--   2. Paste and run this entire file.
--   3. Go to Supabase Dashboard → Authentication → Users → delete all users.
--
-- IRREVERSIBLE. Make a backup first if needed.
-- ============================================================================

DO $$
DECLARE
    r           RECORD;
    table_count INT := 0;
BEGIN
    FOR r IN (
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    ) LOOP
        BEGIN
            EXECUTE format('TRUNCATE TABLE public.%I CASCADE', r.tablename);
            table_count := table_count + 1;
            RAISE NOTICE 'Truncated: %', r.tablename;
        EXCEPTION WHEN others THEN
            RAISE WARNING 'Skipped %: %', r.tablename, SQLERRM;
        END;
    END LOOP;
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Done. % tables wiped.', table_count;
    RAISE NOTICE '========================================';
END $$;

-- Verify everything is empty
SELECT
    (SELECT COUNT(*) FROM public.persons)                    AS persons,
    (SELECT COUNT(*) FROM public.journal_entries)            AS journals,
    (SELECT COUNT(*) FROM public.conversation_turns)         AS turns,
    (SELECT COUNT(*) FROM public.continuity_surface_policy)  AS continuity_policies;

-- Expected: all zeros
