# Database Migrations

## Current State

The database schema is **baselined** as of 2026-02-03.

- **Active tables:** 179
- **Baseline migration:** `0001_baseline.sql`
- **Schema doc:** [docs/DATABASE_SCHEMA.md](../../../../docs/DATABASE_SCHEMA.md)

## For New Databases

To set up a fresh database:

```bash
psql $DATABASE_URL -f sakhi/infra/scripts/migrations/0001_baseline.sql
```

Or use the Supabase dashboard to restore from a backup.

## For Existing Databases

New migrations go in this folder with the next number:

```
0002_your_migration.sql
0003_another_migration.sql
```

## Archive

Historical migrations (0001-0053 pre-baseline) are preserved in:
`_archive/2026-02-03_reorganization/migrations_consolidated/`

## Regenerating Schema Doc

After any migration, regenerate the schema doc by querying the live database.
