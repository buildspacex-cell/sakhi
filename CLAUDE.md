# Claude Code Instructions for Sakhi

> **This file provides instructions for Claude and other LLMs working on this codebase.**
>
> Last Updated: 2026-03-05

---

## Project Structure

```
sakhi-monorepo/
├── apps/
│   ├── web/                   # Next.js 14 frontend (App Router)
│   └── mobile/                # React Native (Expo)
├── sakhi/                     # Python backend (CANONICAL)
│   ├── apps/api/              # FastAPI API
│   │   ├── routes/            # 80+ API route modules
│   │   └── services/          # Business logic (230+ modules)
│   ├── apps/engine/           # 34 computational engines
│   ├── apps/worker/           # RQ background workers
│   ├── libs/                  # Shared Python libraries
│   ├── tests/                 # All Python tests
│   └── infra/scripts/
│       └── migrations/        # SINGLE migration location
├── kala/                      # Governance kernel (pure computation, 552 tests)
├── docs/                      # All documentation
│   ├── ARCHITECTURE.md        # System architecture
│   ├── DATABASE_SCHEMA.md     # 179 tables reference
│   ├── DATABASE_MIGRATIONS.md # Migration instructions
│   ├── BUILD_PLAN.md          # Feature roadmap
│   ├── kala/                  # Governance kernel documentation
│   └── features/, guides/, vision/
├── scripts/                   # Dev/utility scripts
├── config/                    # App configuration
└── _archive/                  # Historical code (excluded from IDE)
```

---

## Quick Commands

| Task | Command |
|------|---------|
| Start API | `make dev` |
| Start web | `pnpm dev:web` |
| Start workers | `make worker` |
| Run tests | `make test` |
| Quick tests only | `make quick-test` (currently stale target; use explicit pytest targets) |
| Format code | `make format` |
| Lint code | `make lint` |
| Type check | `make typecheck` |
| Env contract check | `make check-env` |
| Run migrations | `make db-migrate` |
| Build web | `cd apps/web && pnpm build` |
| Dev status dashboard | `make status` |
| **Quick verification** | `make verify` |
| **Ready to commit** | `make ready-to-commit` |
| **Pre-deploy check** | `make pre-deploy` |
| Full build check | `make build-check` |
| Generate changelog | `make changelog` |

---

## Development Tools

### Code Generators
Scaffold new routes and services with boilerplate and tests:

```bash
# Create a new API route with tests
make new-route name=wellness
# Creates: sakhi/apps/api/routes/wellness.py
#          sakhi/tests/api/test_wellness.py

# Create a new service module with tests
make new-service name=wellness_tracker
# Creates: sakhi/apps/api/services/wellness_tracker/
#          sakhi/tests/services/test_wellness_tracker.py
#          sakhi/tests/services/test_wellness_tracker_integration.py
```

### Pre-commit Hooks
Automatic checks before each commit:

```bash
# Install hooks (done automatically by make bootstrap)
make pre-commit-install

# Run all hooks manually
make pre-commit-run
```

Hooks include:
- Python formatting (black, ruff)
- TypeScript type checking (on push)
- Quick smoke tests (on push)
- Secret detection
- Large file prevention

### Test Fixtures
Use the test fixtures for consistent test data:

```python
from sakhi.tests.fixtures import (
    DEMO_USER_ID,           # "6b5b2fbc-9efb-4ba4-be0a-9ec527e23f90" (Vidhya)
    create_test_user,       # Factory for user data
    create_test_journal_entry,  # Factory for journal entries
    ensure_test_user,       # Ensure user exists in DB
)

# In tests
@pytest.fixture
def test_person_id():
    return DEMO_USER_ID

async def test_something(test_person_id):
    await ensure_test_user(test_person_id)
    # ... test with real DB
```

### Feature Flags
Control feature rollouts:

```python
from sakhi.libs.feature_flags import is_enabled, flag_override

# Check if feature is enabled
if is_enabled("new_conversation_engine_v3"):
    # Use new engine
    pass

# In tests - temporarily enable a flag
with flag_override("experimental_feature", True):
    # Flag is enabled in this block
    assert is_enabled("experimental_feature")
```

Environment overrides:
```bash
# Enable a flag via environment
export SAKHI_FLAG_NEW_CONVERSATION_ENGINE_V3=1
```

### API Test Client (TypeScript)
For testing frontend integrations:

```typescript
import { apiClient, DEMO_USER_ID } from '@/lib/test-utils/api-client';

// Send a conversation turn
const response = await apiClient.turn.send({
  personId: DEMO_USER_ID,
  message: "Hello!",
});

// Get friction state
const state = await apiClient.friction.getCurrentState(DEMO_USER_ID);

// Wait for API to be ready
await waitForApi(10000);  // 10 second timeout
```

### Dev Status Dashboard
See current state of all services:

```bash
make status
# Shows: Git status, running services, test counts, env vars
```

### Localhost Auth Bypass (Web Dev)
For localhost-only web testing without Supabase login:

```bash
# In .env.local (development only)
DEV_AUTH_BYPASS_PERSON_ID=a1b2c3d4-1111-4000-8000-000000000001
```

Notes:
- Active only when `NODE_ENV=development` and host is `localhost`/`127.0.0.1`
- Used by middleware and `GET /api/auth/me` to bypass login for protected web routes
- Set `DEV_AUTH_BYPASS_PERSON_ID=` (empty) to disable

### Documentation Generation
Auto-generate docs from code:

```bash
# Generate API routes documentation
make docs-api

# Generate database tables list
make docs-schema
```

---

## Database Changes

**CRITICAL:** Follow [docs/DATABASE_MIGRATIONS.md](docs/DATABASE_MIGRATIONS.md) exactly.

### Quick checklist:
1. Read `docs/DATABASE_SCHEMA.md` to understand current schema (179 tables)
2. Create migration at `sakhi/infra/scripts/migrations/NNNN_description.sql`
3. Always use `IF NOT EXISTS` / `IF EXISTS` guards
4. Apply with `make db-migrate` or `psql $DATABASE_URL -f <migration_file>`
5. Update `docs/DATABASE_SCHEMA.md` if significant changes

### Never do:
- Drop columns without explicit user approval
- Run destructive migrations without backup
- Modify `0001_baseline.sql` (it's a snapshot of 179 tables)
- Create migrations in other locations (only `sakhi/infra/scripts/migrations/`)

---

## Python Backend (sakhi/apps/api/)

### Adding a new route
1. Create route file in `sakhi/apps/api/routes/`
2. Register in `sakhi/apps/api/main.py`
3. Add service logic in `sakhi/apps/api/services/`

### Key services
| Service | Purpose |
|---------|---------|
| `services/ayurveda/` | Ayurvedic intelligence (prakruti, vikriti, causal reasoning) |
| `services/memory/` | Memory system (STM, episodic, recall, preferences) |
| `services/conversation_v2/` | Conversation engine, reasoner, synthesis |
| `services/continuity/` | Continuity policy, arc surfacing, deep reflection jobs |
| `services/turn/` | Per-turn orchestration, context loading |
| `services/governance/` | Kala governance bridge (constraints, drift gating, event ledger) |
| `services/demo/` | Demo seeding, simulation harness, governance seeder |
| `services/soul/` | Soul values, identity state computation |
| `services/patterns/` | Pattern detection and crystallization |
| `services/agent/` | Desktop agent, browser automation, vision loop |
| `services/mesh/` | Inter-Sakhi coordination |
| `services/calendar/` | Calendar and scheduling |
| `services/learning/` | Intervention plans, feedback, preference updates |
| `services/email/` | Email intelligence (Gmail integration, signals, patterns) |

### Database access pattern
```python
from sakhi.libs.db import get_db_pool

async def my_function():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.fetch("SELECT * FROM table WHERE person_id = $1", person_id)
```

### Environment variables
- Local runtime source of truth is `.env.local` (dev) with fallback to `.env`
- Production source of truth is platform env settings (Railway/Vercel), not local files
- `.env.example` and `.env.local.example` are templates only (not loaded at runtime)
- Access via `os.environ['VAR_NAME']` or `from dotenv import load_dotenv`
- Production alerting supports optional external sinks via `SAKHI_MONITORING_ENABLED`, `SAKHI_SENTRY_DSN`, and `SAKHI_ALERT_WEBHOOK_URL`

---

## Frontend (apps/web/)

### Next.js App Router structure
```
apps/web/app/
├── api/              # API routes (thin proxy to FastAPI backend)
│   ├── voice/        # Voice endpoints (STT, TTS)
│   ├── friction/     # Friction framework endpoints
│   └── agent/        # Agent/browser automation
├── experience/       # Main app pages
│   ├── converse/     # Chat interface
│   ├── calendar/     # Calendar UI
│   └── me/           # User profile/wellness
├── demo/             # Demo pages for investors
└── lab/              # Experimental features
```

### API calls to backend
```typescript
import { getApiBase } from "@/lib/api-base";

const response = await fetch(`${getApiBase()}/endpoint`);
```

### Styling
- Tailwind CSS with custom brand colors (indigo palette)
- Dark mode supported via `dark:` classes

### Mobile / Web Parity
- **The flow (screens, questions, logic) must be identical** between `apps/mobile/` and `apps/web/`. The mobile app is the source of truth for flow design.
- **The visual design must be appropriate to each form factor.** Do NOT just copy mobile styles to web. Web pages should be responsive and work on all browsers and screen sizes (desktop, tablet, mobile-width browsers).
- **Web layout pattern**: Center content in a max-width column (`maxWidth: 560px`, `margin: 0 auto`). Buttons, inputs, and footers live inside this column — never in a separate full-width bar.
- **Responsive by default**: Use `width: 100%` with `maxWidth` constraints so layouts naturally adapt to narrow viewports without media queries.
- When building or modifying any experience flow, always reference the mobile app for the canonical flow and question data, then adapt the presentation for web.

---

## Voice Integration

Voice pipeline is implemented:
- `apps/web/app/api/voice/turn/route.ts` - Audio → Whisper STT → Sakhi → OpenAI TTS → Audio
- `apps/web/app/api/voice/tts/route.ts` - Standalone TTS
- `apps/web/lib/hooks/useVoice.ts` - React hook for voice capture

---

## Testing

### Test Commands
| Command | When to Use |
|---------|-------------|
| `make verify` | **Before every commit** - quick lint + typecheck + smoke |
| `make test` | Run all unit tests |
| `make integration-test` | Run integration tests (requires DB) |
| `make test-workers` | Test workers only |
| `make test-routes` | Test API routes only |
| `make test-coverage` | Generate coverage report |
| `make pre-deploy` | **Before major deploys** - full verification |

### Test Structure
```
sakhi/tests/
├── conftest.py              # Shared fixtures
├── fixtures/                # Test data factories
├── unit/                    # Unit tests (mocked DB)
│   ├── workers/
│   └── services/
├── integration/             # Integration tests (real DB)
│   ├── routes/              # API endpoint tests
│   └── workers/             # Worker + DB tests
└── e2e/                     # End-to-end flows
```

### Test Coverage Tracking
See [docs/TEST_STATUS.md](docs/TEST_STATUS.md) for:
- Which workers/routes have tests
- Priority gaps to fill
- Coverage targets (90% for production)

---

## Build → Test → Commit → Deploy Workflow

Since Vercel/Railway auto-deploy on commit to main:

### Daily Development
```bash
# 1. Write code + tests + docs
# 2. Quick verification before commit
make verify              # ~30 seconds

# 3. Commit (pre-commit hooks run automatically)
git add -A && git commit -m "feat: Add X"

# → Auto-deploys to staging
```

### Before Production Deploy
```bash
# Full verification suite
make pre-deploy          # ~2-5 minutes

# This runs:
# ✓ Linting
# ✓ Type checking
# ✓ Local env contract (`.env.local` -> `.env`)
# ✓ All unit tests
# ✓ All integration tests
```

### Commit Checklist
Before committing, ensure:
- [ ] `make verify` passes
- [ ] Tests added for new code
- [ ] Docs updated (BUILD_PLAN.md, features/, etc.)
- [ ] No secrets in code

---

## Git Workflow

1. Work on feature branch
2. Commit with descriptive messages
3. PR to `main` branch

### Commit message format
```
feat: Add user goals tracking
fix: Resolve memory leak in embeddings
refactor: Consolidate migration files
docs: Update schema documentation
```

---

## File Locations Reference

| What | Where |
|------|-------|
| FastAPI routes | `sakhi/apps/api/routes/` |
| Services/business logic | `sakhi/apps/api/services/` |
| Database migrations | `sakhi/infra/scripts/migrations/` |
| Schema documentation | `docs/DATABASE_SCHEMA.md` |
| Migration instructions | `docs/DATABASE_MIGRATIONS.md` |
| Architecture overview | `docs/ARCHITECTURE.md` |
| Feature roadmap | `docs/BUILD_PLAN.md` |
| Environment variables | `.env` (not committed) |

---

## Common Patterns

### Person-scoped data
Most tables use `person_id` to scope data to a user:
```sql
person_id UUID NOT NULL  -- or TEXT depending on table
```

### JSONB for flexible data
```sql
metadata JSONB DEFAULT '{}'
```

### Vector embeddings
```sql
embedding vector(1536)  -- OpenAI text-embedding-3-small
```

### Timestamps
```sql
created_at TIMESTAMPTZ DEFAULT now(),
updated_at TIMESTAMPTZ DEFAULT now()
```

---

## Key Tables

| Table | Purpose |
|-------|---------|
| `personal_model` | User's Ayurvedic profile, operating system, states |
| `memory_short_term` | Recent conversation memory |
| `memory_episodic` | Daily episode summaries with state vectors |
| `journal_entries` | User journal entries |
| `intervention_plans` | Wellness intervention tracking |
| `registered_agents` | Desktop/browser agents |
| `calendar_events` | Sakhi calendar events |
| `governance_constraints` | Kala constraint definitions |
| `governance_objectives` | Versioned governance objectives |
| `governance_events` | Governance event ledger |

---

## Required for ALL Code Changes

### 1. Tests Required
Every feature or fix MUST include tests:

**Unit Tests** (always required):
```bash
# Python: Add tests in sakhi/tests/
pytest sakhi/tests/test_your_feature.py -v

# Run all tests before committing
make test
```

**Integration Tests** (required for large modules):
When building a new service/module, include integration tests that:
- Test the full API endpoint flow (request → service → database → response)
- Test interactions between multiple services
- Test with realistic data scenarios

```bash
# Integration tests location
sakhi/tests/integration/test_your_module_integration.py

# Example: Test full conversation turn flow
async def test_turn_with_memory_and_workers():
    # 1. Create test user
    # 2. Call /v2/turn endpoint
    # 3. Verify memory was stored
    # 4. Verify workers were triggered
    # 5. Verify response quality
```

### 2. Database Changes Require Read → Update → Test
If code touches the database:
1. **READ** `docs/DATABASE_SCHEMA.md` first to understand existing schema
2. **UPDATE** the schema doc if you add/modify tables
3. **TEST** migrations work:
   ```bash
   # Apply migration
   psql $DATABASE_URL -f sakhi/infra/scripts/migrations/NNNN_your_migration.sql

   # Verify
   psql $DATABASE_URL -c "\d your_table"
   ```

### 3. Documentation Updates Required
Every development MUST include corresponding doc updates:

| What You Built | Update These Docs |
|----------------|-------------------|
| New feature | `docs/BUILD_PLAN.md` (mark complete), `docs/features/` (add/update feature doc) |
| New API endpoint | `docs/ARCHITECTURE.md` (API routes section) |
| Database changes | `docs/DATABASE_SCHEMA.md`, `docs/DATABASE_MIGRATIONS.md` if new patterns |
| New service/module | `docs/ARCHITECTURE.md` (services section), `CLAUDE.md` (key services table) |
| Setup/config changes | `docs/guides/getting-started.md`, `docs/guides/TODO_DEPLOY.md` |
| Test patterns | `docs/guides/testing.md` |

**Checklist before PR:**
- [ ] Feature doc created/updated in `docs/features/`
- [ ] BUILD_PLAN.md status updated (⬜ → ✅)
- [ ] ARCHITECTURE.md updated if system design changed
- [ ] guides/ updated if setup/deploy changed

### 4. Build Verification
Before committing significant changes:
```bash
# Python API imports
python -c "from sakhi.apps.api.main import app; print('API OK')"

# Web build
cd apps/web && pnpm build
```

---

## Do NOT

- Modify files in `_archive/` (historical reference only)
- Commit `.env` or `.env.local` files
- Push directly to `main` without review
- Delete database tables without explicit approval
- Create new root-level directories (use existing structure)
- Create migrations outside `sakhi/infra/scripts/migrations/`
- Write code without corresponding tests
- Build large modules without integration tests
- Modify database schema without reading DATABASE_SCHEMA.md first
- Ship features without updating relevant documentation
- Leave BUILD_PLAN.md out of sync with actual implementation status

---

## Claude Workflow: When User Says "Commit"

When the user says **"commit"**, **"ready to commit"**, **"let's commit"**, or similar:

### Step 1: Run Verification + Build
```bash
make ready-to-commit        # lint → typecheck → quick-test → API check → web build
```
This catches: Python lint issues, type errors, test failures, Railway errors (API), Vercel errors (web).

### Step 2: Check Results
- If **passes**: Proceed to Step 3
- If **fails**: Fix the issues first, then re-run

### Step 3: Review Changes
```bash
git status
git diff --stat
```
Show the user what will be committed.

### Step 4: Create Commit
```bash
git add <specific files>   # Prefer specific files over -A
git commit -m "<type>: <description>"
```

Commit message format:
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code restructure
- `docs:` Documentation only
- `test:` Adding tests
- `chore:` Maintenance

### Step 5: Confirm
Tell the user: "Committed. Vercel/Railway will auto-deploy."

---

## Claude Workflow: When Building Features

When user asks to **build something**:

1. **Read first** - Check existing code patterns in relevant files
2. **Write code** - Follow patterns in this codebase
3. **Write tests** - Add to `sakhi/tests/` (unit) or `sakhi/tests/integration/` (integration)
4. **Update docs** - BUILD_PLAN.md, ARCHITECTURE.md, feature docs as needed
5. **Verify** - Run `make verify` before telling user it's ready

### For Large Features
If building a new service/route/module:
1. Use code generators: `make new-route name=X` or `make new-service name=X`
2. Include integration tests
3. Update TEST_STATUS.md with new test coverage

---

## Quick Task Shortcuts

When the user says these phrases, immediately perform the corresponding action:

| User Says | What to Do |
|-----------|------------|
| **"fix lint"** | Run `make format` then `make lint`, fix any remaining issues |
| **"check db"** | List recent migrations (`ls -la sakhi/infra/scripts/migrations/`), show table count |
| **"what broke"** | Run `make verify`, analyze failures, propose fixes |
| **"resume"** | Read `.claude/CURRENT_TASK.md`, continue where we left off |
| **"status"** | Run `make status` to show dev environment state |
| **"test this"** | Run relevant tests for the files we just modified |
| **"deploy check"** | Run `make ready-to-commit` to catch all deploy issues |
| **"update memory"** | Update `.claude/MEMORY.md` with new learnings from this session |
| **"reset onboarding \<user_id\>"** | Reset onboarding for a user (see instructions below) |

### Reset Onboarding

When the user says **"reset onboarding"** with a user ID, run these SQL commands:

```bash
export $(grep -v '^#' /Users/fanantics/Documents/Sakhi/.env | grep DATABASE_URL | xargs) && \
/opt/homebrew/Cellar/libpq/18.1/bin/psql "$(echo $DATABASE_URL | sed 's/\?.*//')" -c "
  UPDATE auth_users SET onboarding_completed_at = NULL, onboarding_phase = NULL WHERE id = '<USER_ID>';
  DELETE FROM personal_model WHERE person_id = '<USER_ID>';
  DELETE FROM auth.sessions WHERE user_id = (SELECT supabase_user_id FROM auth_users WHERE id = '<USER_ID>');
"
```

This clears:
1. `auth_users.onboarding_completed_at` and `onboarding_phase` → app treats them as new user
2. `personal_model` row → onboarding computes a fresh Operating System
3. `auth.sessions` → signs the user out so they must log in again (full fresh flow)

There is also a full data reset endpoint at `POST /dev/reset-user-data` (body: `{"person_id": "<USER_ID>"}`) that clears ALL user data across 30+ tables. Only use this for a complete wipe.

### Session Memory Files

Claude has persistent memory across sessions:

| File | Purpose |
|------|---------|
| `.claude/MEMORY.md` | Key decisions, patterns, gotchas, user preferences |
| `.claude/CURRENT_TASK.md` | What we're working on now |

**At session start**: Read `.claude/MEMORY.md` and `.claude/CURRENT_TASK.md` for context.

**At session end**: Update these files with new learnings and task status.

---

## Changelog

When committing, optionally update `CHANGELOG.md`:

```bash
make changelog   # Generate changelog entry from recent commits
```

Or manually add to the appropriate section:
- `## [Unreleased]` - Changes not yet released
- Group by: Added, Changed, Fixed, Removed
