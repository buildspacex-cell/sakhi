# Database Migrations

## Current State

The database schema is **baselined** as of 2026-01-28.

- **Active tables:** 117
- **Schema doc:** [docs/architecture/database-schema.md](../../../../docs/architecture/database-schema.md)

## For New Databases

To set up a fresh database, apply migrations in order from `_archive/`:

```bash
for f in _archive/00*.sql; do
  psql $DATABASE_URL -f "$f"
done
```

Or use the Supabase dashboard to restore from a backup.

## For Existing Databases

New migrations go in this folder with the next number:

```
0043_your_migration.sql
0044_another_migration.sql
```

## Archive

Old migrations (0001-0042) are preserved in `_archive/` for:
- Historical reference
- Fresh database setup
- Understanding schema evolution

## Regenerating Schema Doc

After any migration, regenerate the schema doc:

```bash
python sakhi/scripts/extract_schema.py > docs/architecture/database-schema.md
```
