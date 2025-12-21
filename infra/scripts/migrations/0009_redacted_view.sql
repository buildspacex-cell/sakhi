CREATE OR REPLACE VIEW export_journals_redacted AS
SELECT id,
       user_id,
       created_at,
       regexp_replace(coalesce(cleaned, ''), '([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})', '***@***', 'g') AS text,
       facets_v2
FROM journal_entries;
