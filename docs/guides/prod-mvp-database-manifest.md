# MVP Production Database Manifest

> **Status:** Ready to execute
> **Scope:** Slim production database for the current Sakhi MVP
> **Goal:** Ship auth-bound chat, conversation history, continuity topics/arcs, and deep reflection without importing the full 179-table legacy schema

---

## What This Covers

This manifest is for the current MVP only:

- `POST /v2/turn`
- `GET /v2/conversation/history`
- `GET /continuity/policy`
- `PUT /continuity/policy`
- `POST /continuity/policy/enable`
- `GET /continuity/topics`
- `GET /continuity/arc`
- `POST /continuity/reflection/run`
- `GET /continuity/reflection/status`
- `GET /continuity/reflection/result`

This manifest does not include support console, agent flows, email/calendar, governance setup, demo/simulation, or the broader legacy analytics/memory graph stack.

---

## Migration Strategy

Do not run the full [0001_baseline.sql](../../sakhi/infra/scripts/migrations/0001_baseline.sql) if the goal is a slim MVP production database.

Instead:

1. Run the curated MVP bootstrap SQL at [mvp_prod_bootstrap.sql](/Users/fanantics/Documents/Sakhi/sakhi/infra/scripts/migrations/mvp_prod_bootstrap.sql).
2. Run that curated SQL on the new Supabase project.
3. Import only the data marked `copy`.
4. Leave the `create-empty` tables empty initially.
5. Backfill derived caches after cutover if needed.

---

## Required Extensions

Enable these first:

- `pgcrypto`
- `pg_trgm`
- `vector`

---

## Table Manifest

### A. Create And Copy

These are the tables that should exist and should have data migrated from the current environment.

| Table | Action | Why it matters now | Current runtime path |
|---|---|---|---|
| `persons` | `create + copy` | canonical person identity row | `apps/api/core/persons.py`, `journal_entries.user_id`, `personal_model.person_id` |
| `auth_users` | `create + copy` | prod auth-bound person resolution uses it | `apps/api/utils/person_resolver.py` |
| `journal_entries` | `create + copy` | every `/v2/turn` persists here; continuity compiles directly from it | `apps/api/services/journaling/observe.py`, `apps/api/services/continuity/service.py` |
| `conversation_sessions` | `create + copy` | chat session lookup/history | `apps/api/services/memory/sessions.py` |
| `conversation_turns` | `create + copy` | stored transcript and conversation history | `apps/api/services/memory/sessions.py` |
| `personal_model` | `create + copy` | current reply path still writes short-term state here | `apps/api/services/conversation_v2/conversation_engine.py` |
| `session_continuity` | `create + copy` | current reply path updates last interaction here | `apps/api/services/conversation_v2/conversation_engine.py` |
| `continuity_surface_policy` | `create + copy` | continuity endpoints hard-gate on this policy | `apps/api/services/continuity/adapters.py` |
| `continuity_labels` | `create + copy` | enables `POST /continuity/label` and label-backed support/admin continuity snapshots | `apps/api/services/continuity/adapters.py`, `apps/api/routes/support.py` |

### B. Create Empty On Day 1

These should exist in schema on day 1, but their rows can start empty.

| Table | Action | Why schema should exist | Notes |
|---|---|---|---|
| `session_summaries` | `create-empty` | chat context loader queries it | empty is fine; summaries can be rebuilt later |
| `deep_reflections` | `create-empty` | reflection job state/result persistence | no need to migrate old reflection history |
| `conversation_state` | `create-empty` | conversation context builder queries it | empty rows are fine; missing table causes top-level fallback |
| `persona_modes` | `create-empty` | conversation context builder queries it | empty rows default to `Reflective` mode |
| `theme_states` | `create-empty` | conversation context builder queries it | safe to backfill later |
| `planner_context_cache` | `create-empty` | conversation context builder queries it | empty rows are fine |
| `context_recalls` | `create-empty` | deep recall context is best-effort | guarded, but useful to keep schema present |
| `thread_continuity_markers` | `create-empty` | deep recall thread context is best-effort | guarded, but useful to keep schema present |
| `journal_embeddings` | `create-empty` | semantic correlation scoring uses it when available | cross-topic logic falls back if empty |
| `continuity_topic_correlations` | `create-empty` | cross-topic cache table | safe to compute lazily later |
| `continuity_life_dimensions` | `create-empty` | life-dimensions cache table | safe to compute lazily later |

### C. Exclude For This MVP

Do not include these in the first production cut unless you are explicitly enabling those surfaces.

| Table or Area | Why excluded |
|---|---|
| `governance_events` | governance/reflection logging is best-effort and non-fatal for the current MVP |
| support console tables | not part of the minimal chat + continuity launch |
| email/calendar tables | not needed for the continuity-first MVP |
| agent/desktop task tables | not needed for the continuity-first MVP |
| demo/simulation tables | internal only |
| broader analytics/rhythm/state cache tables | not required to boot the current MVP endpoints |

---

## Data Copy Order

Use this import order so foreign keys and runtime assumptions line up cleanly:

1. `persons`
2. `auth_users`
3. `journal_entries`
4. `conversation_sessions`
5. `conversation_turns`
6. `personal_model`
7. `session_continuity`
8. `continuity_surface_policy`
9. `continuity_labels`
10. `session_summaries` if you decide to carry them over

Do not copy on day 1:

- `deep_reflections`
- `journal_embeddings`
- `continuity_topic_correlations`
- `continuity_life_dimensions`
- `context_recalls`
- `thread_continuity_markers`
- `planner_context_cache`
- `theme_states`
- `conversation_state`
- `persona_modes`

Those can start empty.

---

## Supabase Execution Order

### Option 1: Recommended

Use a direct DB connection and run:

1. extensions
2. curated MVP bootstrap SQL
3. optional cache/context compatibility SQL
4. data import for the `create + copy` set

Example:

```bash
export PROD_DIRECT_URL="postgresql://postgres:[PASSWORD]@db.[NEW-REF].supabase.co:5432/postgres"
/opt/homebrew/Cellar/libpq/18.1/bin/psql "$PROD_DIRECT_URL" -f sakhi/infra/scripts/migrations/mvp_prod_bootstrap.sql
```

### Option 2: Dashboard SQL Editor

If using the Supabase SQL editor:

1. run the curated schema file first
2. verify tables exist
3. import data in batches
4. only then point Railway/Vercel/mobile at the new DB

Use the direct connection or SQL editor for DDL. Do not run schema creation through the pooler URL.

## Example Data Copy Commands

Use direct database URLs for both source and target.

```bash
export SOURCE_DIRECT_URL="postgresql://postgres:[PASSWORD]@db.[SOURCE-REF].supabase.co:5432/postgres"
export PROD_DIRECT_URL="postgresql://postgres:[PASSWORD]@db.[NEW-REF].supabase.co:5432/postgres"

mkdir -p tmp/mvp-prod-export

for table in \
  persons \
  auth_users \
  journal_entries \
  conversation_sessions \
  conversation_turns \
  personal_model \
  session_continuity \
  continuity_surface_policy \
  continuity_labels
do
  /opt/homebrew/Cellar/libpq/18.1/bin/pg_dump \
    "$SOURCE_DIRECT_URL" \
    --data-only \
    --column-inserts \
    --table="public.${table}" \
    > "tmp/mvp-prod-export/${table}.sql"
done
```

Then import in the same order:

```bash
for table in \
  persons \
  auth_users \
  journal_entries \
  conversation_sessions \
  conversation_turns \
  personal_model \
  session_continuity \
  continuity_surface_policy \
  continuity_labels
do
  /opt/homebrew/Cellar/libpq/18.1/bin/psql \
    "$PROD_DIRECT_URL" \
    -f "tmp/mvp-prod-export/${table}.sql"
done
```

If you decide to carry over session summaries too:

```bash
/opt/homebrew/Cellar/libpq/18.1/bin/pg_dump \
  "$SOURCE_DIRECT_URL" \
  --data-only \
  --column-inserts \
  --table="public.session_summaries" \
  > "tmp/mvp-prod-export/session_summaries.sql"

/opt/homebrew/Cellar/libpq/18.1/bin/psql \
  "$PROD_DIRECT_URL" \
  -f "tmp/mvp-prod-export/session_summaries.sql"
```

For the first cut, do not export/import:

- `deep_reflections`
- `journal_embeddings`
- `continuity_topic_correlations`
- `continuity_life_dimensions`
- `context_recalls`
- `thread_continuity_markers`
- `planner_context_cache`
- `theme_states`
- `conversation_state`
- `persona_modes`

---

## Suggested Backfill Order After Cutover

Once the slim prod DB is live, backfill these in this order:

1. `session_summaries`
2. `journal_embeddings`
3. `continuity_topic_correlations`
4. `continuity_life_dimensions`
5. `conversation_state`
6. `theme_states`
7. `planner_context_cache`
8. `context_recalls`
9. `thread_continuity_markers`

This order gives you the biggest product win first: chat history quality, then faster/better cross-topic reflection, then richer reply context.

---

## Smoke Tests

After schema creation and data import, verify:

- `/health`
- `/v2/turn`
- `/v2/conversation/history`
- `/continuity/policy/enable`
- `/continuity/topics`
- `/continuity/arc`
- `/continuity/reflection/run`
- `/continuity/reflection/status`
- `/continuity/reflection/result`

If `/v2/turn` works but feels under-personalized, the usual cause is an empty context bundle:

- `conversation_state`
- `persona_modes`
- `theme_states`
- `planner_context_cache`

If continuity works but cross-topic reflection feels slow, the usual cause is empty:

- `journal_embeddings`
- `continuity_topic_correlations`
- `continuity_life_dimensions`

---

## Runtime Notes

- Current continuity compilation is still journal-derived for topics/arcs and turn-time reflection, but `continuity_labels` is now included in the slim prod schema so manual label writes and support/admin continuity snapshots do not fail.
- Current cross-topic cache tables are optional because reads and writes degrade cleanly if the tables are empty or missing.
- Current normal chat still benefits from `personal_model` and `session_continuity`, so those should be migrated even in the slim schema.
- If the goal changes from “continuity MVP” to “full Sakhi prod,” stop using this manifest and go back to the full production launch path.
