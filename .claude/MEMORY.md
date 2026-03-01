# Sakhi Project Memory

> Persistent context for Claude sessions. Update this file as you learn important patterns.

---

## Key Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-04 | Single migration source at `/sakhi/infra/scripts/migrations/` | Avoid schema drift |
| 2026-02-04 | Pre-commit hooks with black, ruff, typecheck | Catch errors before commit |
| 2026-02-04 | `make ready-to-commit` before all commits | Catches Vercel/Railway errors |
| 2026-02-26 | Add `docs/CODEBASE_CONTEXT.md` + `scripts/context-audit.sh` as context baseline | Keep coding decisions tied to live code health, not stale assumptions |

---

## Architecture Gotchas

### Python Backend
- **Import path**: Always use `from sakhi.apps.api...` not `from apps.api...`
- **Worker entry**: `sakhi.apps.worker.main` not `apps.worker.main`
- **Test fixtures**: Use `DEMO_USER_ID` from `sakhi.tests.fixtures`
- **Quick-test target is stale**: `make quick-test` references missing `sakhi/tests/v2/test_smoke.py`
- **Ayurvedic demo worker import mismatch**: `sakhi/apps/worker/tasks/ayurvedic_pipeline.py` still imports `core.workers.*`
- **Crystallization update hazard**: `trajectory_data` may be string-encoded JSON; coerce before dict mutation

### Frontend
- **App Router**: Next.js 14 with App Router (not Pages Router)
- **API Routes**: Use `route.ts` not `api.ts`
- **Dynamic exports**: Pages with dynamic data need `export const dynamic = 'force-dynamic'`

### Database
- **pgvector**: 1536 dimensions for embeddings
- **UUIDs**: Use `gen_random_uuid()` from pgcrypto
- **Migrations**: Numbered 0001-NNNN in `/sakhi/infra/scripts/migrations/`

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: sakhi` | Run from project root, ensure `poetry install` |
| `vector dimension mismatch` | Check embedding model (should be 1536) |
| `Vercel build failed: ESLint` | Run `pnpm lint --fix` in apps/web |
| `Railway deploy failed` | Check `python -c "from sakhi.apps.api.main import app"` |

---

## Testing Patterns

```python
# Integration test with real DB
@pytest.mark.integration
@pytest.mark.asyncio
async def test_something(api_client, ensure_test_user, db):
    await ensure_test_user(DEMO_USER_ID)
    response = await api_client.get("/endpoint")
    assert response.status_code == 200

# Unit test with mocked DB
def test_something_unit(mock_db):
    mock_db.fetchrow.return_value = {"id": "test"}
    # test logic
```

---

## User Preferences

- Demo user: `6b5b2fbc-9efb-4ba4-be0a-9ec527e23f90` (Vidhya)
- Avoid emojis in code/docs unless requested
- Prefer editing existing files over creating new ones
- Run `make ready-to-commit` before all commits

---

## Current Sprint Focus

- Stabilizing investor simulation pipeline outputs
- Keeping architecture/test docs aligned with actual code counts
- Hardening quality gates (`make verify`/`make ready-to-commit`) to reflect real test paths

---

*Last updated: 2026-02-26*
