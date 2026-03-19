# Database Migration Instructions

> **For LLMs:** Follow these instructions exactly when making database schema changes.

## Quick Reference

| Action | Command |
|--------|---------|
| View current schema | Read `docs/DATABASE_SCHEMA.md` |
| Create new migration | Write to `sakhi/infra/scripts/migrations/0002_your_change.sql` |
| Apply migration | `psql $DATABASE_URL -f sakhi/infra/scripts/migrations/0002_your_change.sql` |
| Provision fresh DB | `psql $DATABASE_URL -f sakhi/infra/scripts/migrations/0001_baseline.sql` |

---

## 1. Before Making Schema Changes

### Check the current schema
```bash
# Read the schema documentation
cat docs/DATABASE_SCHEMA.md

# Or query live database directly
psql $DATABASE_URL -c "\d table_name"
```

### Verify the table exists
Before modifying a table, confirm it exists in `0001_baseline.sql` or the live database.

---

## 2. Creating a New Migration

### File naming
```
sakhi/infra/scripts/migrations/NNNN_description.sql
```

Where `NNNN` is the next sequential number after the highest existing migration.

### Migration template
```sql
-- Migration: NNNN_description
-- Date: YYYY-MM-DD
-- Description: Brief explanation of what this migration does

-- =============================================================================
-- UP Migration
-- =============================================================================

-- Add new table
CREATE TABLE IF NOT EXISTS new_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Add new column to existing table
ALTER TABLE existing_table
ADD COLUMN IF NOT EXISTS new_column TEXT;

-- Add index
CREATE INDEX IF NOT EXISTS idx_table_column ON table_name(column_name);

-- =============================================================================
-- Notes
-- =============================================================================
-- This migration adds X to support Y feature.
```

### Rules for migrations

1. **Always use IF NOT EXISTS / IF EXISTS**
   ```sql
   CREATE TABLE IF NOT EXISTS ...
   ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...
   DROP TABLE IF EXISTS ...
   ```

2. **Never drop columns in production** - mark as deprecated instead
   ```sql
   -- BAD: Loses data
   ALTER TABLE users DROP COLUMN old_field;

   -- GOOD: Safe deprecation
   COMMENT ON COLUMN users.old_field IS 'DEPRECATED: Use new_field instead';
   ```

3. **Use gen_random_uuid() for UUIDs** (pgcrypto extension)
   ```sql
   id UUID PRIMARY KEY DEFAULT gen_random_uuid()
   ```

4. **Always add created_at/updated_at**
   ```sql
   created_at TIMESTAMPTZ DEFAULT now(),
   updated_at TIMESTAMPTZ DEFAULT now()
   ```

5. **Use TEXT over VARCHAR** unless you need length enforcement
   ```sql
   -- Preferred
   name TEXT NOT NULL

   -- Only when length matters
   country_code VARCHAR(2) NOT NULL
   ```

6. **Reference persons table** for user-scoped data
   ```sql
   person_id UUID NOT NULL REFERENCES persons(id)
   -- or for TEXT-based person_id
   person_id TEXT NOT NULL
   ```

---

## 3. Common Patterns

### New feature table
```sql
CREATE TABLE IF NOT EXISTS feature_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,

    -- Feature-specific columns
    feature_type TEXT NOT NULL,
    feature_data JSONB DEFAULT '{}',

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feature_records_person
ON feature_records(person_id);

CREATE INDEX IF NOT EXISTS idx_feature_records_type
ON feature_records(feature_type);
```

### Adding vector embeddings
```sql
ALTER TABLE table_name
ADD COLUMN IF NOT EXISTS embedding vector(1536);

CREATE INDEX IF NOT EXISTS idx_table_embedding
ON table_name USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### Adding JSONB with GIN index
```sql
ALTER TABLE table_name
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_table_metadata
ON table_name USING GIN (metadata);
```

### Unique constraints
```sql
ALTER TABLE table_name
ADD CONSTRAINT uq_table_columns UNIQUE (person_id, scope, key);
```

---

## 4. Applying Migrations

### Development
```bash
# Apply single migration
psql $DATABASE_URL -f sakhi/infra/scripts/migrations/0002_new_feature.sql

# Verify it worked
psql $DATABASE_URL -c "\d new_table"
```

### Production (Supabase)
1. Open Supabase Dashboard → SQL Editor
2. Paste migration SQL
3. Execute
4. Verify in Table Editor

---

## 5. After Making Changes

### Update the schema documentation
After applying a migration, regenerate `docs/DATABASE_SCHEMA.md` by querying the live database:

```python
# Run this to extract updated schema
poetry run python -c "
import asyncio
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()

async def get_tables():
    conn = await asyncpg.connect(os.environ['DATABASE_URL'], statement_cache_size=0)
    tables = await conn.fetch('''
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    ''')
    for t in tables:
        print(t['table_name'])
    await conn.close()

asyncio.run(get_tables())
"
```

---

## 6. Rollback Strategy

### For additive changes (new tables/columns)
No rollback needed - additive changes are safe.

### For destructive changes
1. Take a backup first via Supabase Dashboard
2. Write explicit DOWN migration:
```sql
-- DOWN Migration (keep in comments, don't auto-run)
-- DROP TABLE IF EXISTS new_table;
-- ALTER TABLE existing_table DROP COLUMN IF EXISTS new_column;
```

---

## 7. File Locations

| File | Purpose |
|------|---------|
| `sakhi/infra/scripts/migrations/0001_baseline.sql` | Full schema for fresh DBs (179 tables) |
| `sakhi/infra/scripts/migrations/mvp_prod_bootstrap.sql` | Curated slim bootstrap for the continuity/chat MVP prod database |
| `sakhi/infra/scripts/migrations/0002_*.sql` | New migrations |
| `docs/DATABASE_SCHEMA.md` | Human-readable schema reference |
| `_archive/migrations_consolidated/` | Historical migrations |

---

## 8. Required PostgreSQL Extensions

These are already enabled in Supabase:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- UUID generation
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- Trigram text search
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector embeddings
```

---

## 9. Checklist for Schema Changes

- [ ] Read current schema from `docs/DATABASE_SCHEMA.md`
- [ ] Determine next migration number (check `sakhi/infra/scripts/migrations/`)
- [ ] Write migration with `IF NOT EXISTS` guards
- [ ] Test migration locally or in Supabase SQL Editor
- [ ] Update `docs/DATABASE_SCHEMA.md` if significant changes
- [ ] Commit migration file

---

## 10. Example: Adding a New Feature

**Task:** Add a `user_goals` table for tracking personal goals.

**Step 1:** Check next migration number
```bash
ls sakhi/infra/scripts/migrations/
# Shows: 0001_baseline.sql
# Next: 0002
```

**Step 2:** Create migration file
```sql
-- sakhi/infra/scripts/migrations/0002_user_goals.sql
-- Migration: 0002_user_goals
-- Date: 2026-02-03
-- Description: Add user_goals table for personal goal tracking

CREATE TABLE IF NOT EXISTS user_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL DEFAULT 'general',
    target_date DATE,
    status TEXT NOT NULL DEFAULT 'active',
    progress_pct INTEGER DEFAULT 0 CHECK (progress_pct >= 0 AND progress_pct <= 100),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_goals_person ON user_goals(person_id);
CREATE INDEX IF NOT EXISTS idx_user_goals_status ON user_goals(status);
```

**Step 3:** Apply migration
```bash
psql $DATABASE_URL -f sakhi/infra/scripts/migrations/0002_user_goals.sql
```

**Step 4:** Verify
```bash
psql $DATABASE_URL -c "\d user_goals"
```
