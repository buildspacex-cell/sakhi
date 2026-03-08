# Production Readiness Audit

> **Date:** 2026-03-05
> **Scope:** Full workspace — backend, frontend, infrastructure, data pipeline
> **Overall Score:** ~45/100 — strong foundations, critical security gaps to close

---

## Executive Summary

Sakhi has a **solid engineering foundation**: structured logging, health checks, Prometheus metrics, proper DB pooling, comprehensive Makefile automation, and a 14-migration schema with idempotent guards. The critical gaps are in **authentication enforcement**, **security headers**, **test coverage**, and **operational readiness** (backup, scaling, monitoring dashboards).

### Priority Matrix

| Priority | Count | Category |
|----------|-------|----------|
| P0 — Must fix before production | 8 | Auth, SQL injection, CSRF, API key exposure |
| P1 — Fix before scaling | 10 | Rate limiting, worker retries, error boundaries, CORS |
| P2 — Fix before GA | 8 | Test coverage, SEO, backup procedures, feature flags |
| P3 — Nice to have | 6 | Image optimization, code splitting, distributed tracing |

---

## P0 — CRITICAL (Must Fix Before Production)

### 1. Route Authentication Missing

**Impact:** Any user can access any other user's data.

| Route | Issue | File |
|-------|-------|------|
| `/v2/turn` | Accepts `?user=UUID` with no auth verification | `sakhi/apps/api/routes/turn_v2.py` |
| `/api/turn-v2` | Frontend proxy — no Supabase auth check | `apps/web/app/api/turn-v2/route.ts` |
| `/api/chat` | Uses `NEXT_PUBLIC_API_KEY` (exposed to client JS) | `apps/web/app/api/chat/route.ts` |
| `/demo/*` | No auth — demo-only but reachable in production | `sakhi/apps/api/routes/demo.py` |
| `/api/lab/*` | No auth — dev-only but no production guard | `apps/web/app/api/lab/` |
| `/api/agent/approvals/*` | No Supabase auth check | `apps/web/app/api/agent/` |

**Root Cause:** `resolve_person()` utility accepts `?user=<uuid>` query param without verifying the UUID belongs to the authenticated Supabase user.

**Fix:**
- Add Supabase JWT verification middleware to all user-facing routes
- Verify `person_id` from JWT matches `?user=` query param
- Gate `/demo/*` and `/api/lab/*` behind `SAKHI_ENVIRONMENT != production`

### 2. SQL Injection via Schema Identifiers

**Impact:** Table/column names interpolated via f-strings.

| File | Line | Code |
|------|------|------|
| `sakhi/apps/api/routes/memory.py` | 376 | `f"DELETE FROM {table} WHERE person_id = $1"` |
| `sakhi/apps/api/routes/dev.py` | 149 | `f"DELETE FROM {table_name} WHERE {id_column} = $1"` |

**Mitigation:** Values come from internal whitelist (not user input), but pattern is unsafe.

**Fix:** Use `asyncpg`'s `connection.execute()` with SQL identifier quoting, or use an allowlist guard with assertion.

### 3. OAuth CSRF Vulnerability

**Impact:** Attacker can craft Gmail OAuth callback URL with arbitrary `person_id`.

**File:** `sakhi/apps/api/routes/email.py:199-203`

The state parameter is decoded but the CSRF token inside it is never verified against a server-side store. An attacker can construct a state with any `person_id`.

**Fix:** Store CSRF token in Redis/DB on OAuth start, verify on callback.

### 4. API Key Exposed in Client Bundle

**Impact:** `NEXT_PUBLIC_API_KEY` is embedded in client-side JavaScript. Anyone can extract it.

**Files:** 10+ routes using `process.env.NEXT_PUBLIC_API_KEY`:
- `/api/chat`, `/api/breath/session`, `/api/missions`, `/api/rhythm/*`, `/api/analytics/*`

**Fix:** Rename to `API_KEY` (server-only, not `NEXT_PUBLIC_*`).

### 5. Missing Security Headers

**Impact:** Clickjacking, MIME sniffing, no HTTPS enforcement.

**File:** `apps/web/next.config.js` — no `headers()` export.

**Missing:**
- `Content-Security-Policy`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Strict-Transport-Security`
- `Permissions-Policy`

**Fix:** Add `headers()` async function to `next.config.js`.

### 6. Deep Reflection Access Control Missing

**Impact:** Any user can fetch another user's deep reflection by UUID.

**File:** `sakhi/apps/api/services/continuity/reflection.py:149-157`

```python
SELECT ... FROM deep_reflections WHERE id = $1::uuid
# No person_id check!
```

**Fix:** Add `AND person_id = $2` to the query and pass authenticated person_id.

### 7. Dev Auth Bypass Risk

**Impact:** If `NODE_ENV` leaks to production, dev bypass grants access without login.

**File:** `apps/web/lib/devAuthBypass.ts:6-8`

Currently guarded by `NODE_ENV === "development"` only.

**Fix:** Require explicit `DEV_AUTH_BYPASS_ENABLED=true` env var, not just NODE_ENV.

### 8. ESLint Disabled During Builds

**Impact:** Build-time errors masked in production deploys.

**File:** `apps/web/next.config.js:7-8` — `eslint: { ignoreDuringBuilds: true }`

**Fix:** Remove this flag. Fix lint errors instead of suppressing them.

---

## P1 — HIGH (Fix Before Scaling)

### 9. No Error Boundaries in Frontend

Only 1 `error.tsx` exists (`/demo/error.tsx`). Missing: root-level, `/experience/*`.

**Fix:** Add `app/error.tsx` and `app/experience/error.tsx`.

### 10. CORS Too Permissive

**File:** `sakhi/apps/api/main.py:41-51`

```python
allow_methods=["*"],
allow_headers=["*"],
```

**Fix:** Whitelist specific methods (`GET, POST, PUT, DELETE, PATCH`) and headers (`Authorization, Content-Type`). Move origins to env var.

### 11. Worker Retry & Dead Letter Queues Missing

No retry policy configured on any RQ queue. Failed jobs are lost.

**Fix:** Add `retry=Retry(max=3, interval=[10, 30, 60])` to queue enqueue calls. Configure failed job handler.

### 12. Rate Limiting Incomplete

- Only per-API-key global RPM (60/min default)
- No per-endpoint limits
- No rate limit headers in responses
- Pacing middleware is advisory only

**Fix:** Add per-endpoint rate limits for expensive operations (LLM calls, email sync). Add `X-RateLimit-*` headers.

### 13. LLM Token Limit Checks Missing

**File:** `sakhi/apps/api/core/llm.py`

`call_llm()` has no `max_tokens` enforcement. Large continuity reflections with 1000+ entries can exceed context window.

**Fix:** Add token counting before LLM calls. Truncate context if needed. Handle `context_length_exceeded` errors with retry.

### 14. Conversation Engine Missing Timeouts

**File:** `sakhi/apps/api/services/conversation_v2/conversation_engine.py`

LLM calls have no `asyncio.wait_for()` timeout wrapper. Hung LLM = hung request.

**Fix:** Wrap all LLM calls in `asyncio.wait_for(..., timeout=30.0)`.

### 15. Deep Reflection Fire-and-Forget

**File:** `sakhi/apps/api/services/continuity/reflection.py:71-80`

`asyncio.create_task()` with no error boundary. If the background task crashes, user gets no feedback — reflection hangs at "queued" forever.

**Fix:** Add error boundary in the task. Set status to "failed" with error message. Add timeout guard.

### 16. Simulation Pipeline Can Corrupt Production Data

**File:** `scripts/run_demo_personas.py`

- Runs against live `DATABASE_URL`
- `--no-cleanup` leaves demo data in production DB
- Hardcoded UUIDs can collide with real users
- `db_mod.POOL.terminate()` kills all connections including production

**Fix:** Add `SAKHI_ENVIRONMENT` guard — refuse to run if `production`. Use `pool.close()` instead of `terminate()`.

### 17. Demo Code Imported in Production Paths

**File:** `sakhi/apps/api/services/continuity/inference.py:5-28`

Production inference module imports from `services/demo/simulation_continuity`. If demo schemas diverge, production continuity breaks.

**Fix:** Decouple demo continuity from production inference. Use feature flag guard.

### 18. Input Validation Missing

Most API routes don't validate request bodies with Zod schemas (frontend) or comprehensive Pydantic validators (backend).

**Fix:** Add Zod validation in frontend API routes. Strengthen Pydantic models with field validators.

---

## P2 — MEDIUM (Fix Before GA)

### 19. Test Coverage at ~24%

- 84 test files for 343 route/service files
- Critical gaps: `/v2/turn` (only 2 test files), email OAuth flow, demo routes, agent routes
- Frontend: 14 test files exist but **no test runner configured** in `package.json`

**Fix:** Target 80% coverage on critical paths. Add Vitest to frontend `package.json`.

### 20. CI Pipeline Minimal

**File:** `.github/workflows/ci.yml`

Only runs `pytest -q`. Missing:
- Linting (`make lint`)
- Type checking (`make typecheck`)
- Integration tests
- Frontend build verification
- Security scanning (`pip-audit`, `npm audit`)

**Fix:** Mirror `make ready-to-commit` in CI.

### 21. No Database Migration Tracking

No `schema_migrations` table to track which migrations have been applied. Relies entirely on SQL idempotency (`IF NOT EXISTS`).

**Fix:** Add a `schema_migrations` table and update `db_migrate.py` to record applied migrations.

### 22. Backup & Recovery Undocumented

No backup automation, no retention policy, no recovery runbook, no backup testing.

**Fix:** Document Supabase backup procedures. Create recovery runbook. Test restore process.

### 23. Feature Flags Not Implemented

`CLAUDE.md` references `sakhi.libs.feature_flags` but the module doesn't exist in the codebase.

**Fix:** Create the module with env-var-based flags and DB persistence for runtime toggles.

### 24. SEO & Metadata Missing

No `robots.txt`, no Open Graph tags, no Twitter Cards, no `generateMetadata` on pages.

**Fix:** Add metadata for public-facing pages. Add `robots.txt` (block all if closed beta).

### 25. Missing Foreign Key Constraints

Tables `continuity_surface_policy`, `continuity_labels`, `governance_constraints`, `governance_events` have `person_id` without FK to `auth_users(id)`.

**Fix:** Add FK constraints with `ON DELETE CASCADE` in a new migration.

### 26. Worker Idempotency Missing

Pattern crystallization and other workers can create duplicate records if retried mid-execution.

**Fix:** Add deduplication checks on `(person_id, pattern_id, run_date)`.

---

## P3 — NICE TO HAVE

### 27. No `next/image` Usage

All images use raw `<img>` tags. Missing lazy loading, responsive sizing, format optimization.

### 28. No Code Splitting for Lab Routes

`/lab/*` routes load full bundle. Consider `next/dynamic` for heavy components.

### 29. 19 `as any` Casts in Frontend

TypeScript strictness is good (`strict: true`) but 19 `any` casts hide real type issues.

### 30. No Distributed Tracing

Only correlation IDs via `request.state.request_id`. No OpenTelemetry or Jaeger integration.

### 31. No Horizontal Worker Scaling

Single RQ worker instance. No documentation for multi-worker Railway setup.

### 32. Hardcoded CORS Origins

Should be configurable via env var for multi-environment deployments.

---

## Scorecard by Area

| Area | Score | Key Issues |
|------|-------|------------|
| **Authentication** | 25/100 | No auth on main routes, OAuth CSRF, API key exposure |
| **Authorization** | 30/100 | No person_id verification, reflection access control missing |
| **Input Validation** | 40/100 | Pydantic models used but inconsistent; no frontend validation |
| **Error Handling** | 65/100 | Good patterns, missing error boundaries, fire-and-forget tasks |
| **Database** | 80/100 | Good migrations, pooling, parameterized queries; missing FKs |
| **Testing** | 30/100 | 24% coverage, frontend tests unconfigured, critical paths untested |
| **Logging & Monitoring** | 75/100 | Sentry + Prometheus + structured logs; no dashboards or APM |
| **Infrastructure** | 70/100 | Railway + Vercel + Docker; no backup docs, no scaling config |
| **Security Headers** | 15/100 | No CSP, no HSTS, no X-Frame-Options |
| **CI/CD** | 40/100 | GitHub Actions exists but only runs pytest |
| **Performance** | 55/100 | Good DB pooling, no image optimization, no code splitting |
| **Documentation** | 80/100 | Excellent CLAUDE.md, migration docs, architecture docs |

---

## Recommended Fix Order

### Sprint 1 (This Week) — Security Essentials
1. Add Supabase JWT verification to `/v2/turn` and main routes
2. Fix API key exposure (`NEXT_PUBLIC_API_KEY` → server-only)
3. Add security headers to `next.config.js`
4. Add `person_id` check to deep reflection result endpoint
5. Fix OAuth CSRF (server-side token storage)

### Sprint 2 (Next Week) — Stability
6. Add error boundaries (root + experience)
7. Wrap LLM calls in timeouts
8. Add worker retry policies
9. Fix CORS (whitelist specific methods/headers)
10. Gate demo routes behind environment check

### Sprint 3 — Quality & Coverage
11. Expand CI pipeline (lint + typecheck + integration tests)
12. Add migration tracking table
13. Increase test coverage to 60% on critical paths
14. Document backup/recovery procedures
15. Implement feature flags

### Sprint 4 — Polish
16. Add SEO metadata
17. Optimize images with next/image
18. Add per-endpoint rate limits
19. Add distributed tracing
20. Document horizontal scaling

---

## Files Referenced

| Category | Key Files |
|----------|-----------|
| **Auth** | `sakhi/apps/api/utils/person_resolver.py`, `sakhi/libs/security/auth.py`, `sakhi/apps/api/middleware/auth_pilot.py` |
| **Security** | `apps/web/next.config.js`, `apps/web/lib/devAuthBypass.ts`, `sakhi/apps/api/routes/email.py` |
| **SQL** | `sakhi/apps/api/routes/memory.py:376`, `sakhi/apps/api/routes/dev.py:149` |
| **LLM** | `sakhi/apps/api/core/llm.py`, `sakhi/apps/api/services/conversation_v2/conversation_engine.py` |
| **Workers** | `sakhi/apps/worker/main.py`, `sakhi/apps/worker/scheduler.py` |
| **Continuity** | `sakhi/apps/api/services/continuity/reflection.py`, `sakhi/apps/api/services/continuity/inference.py` |
| **CI/CD** | `.github/workflows/ci.yml`, `Makefile`, `.pre-commit-config.yaml` |
| **Infra** | `railway.toml`, `Dockerfile`, `docker-compose.yml` |
| **Monitoring** | `sakhi/apps/api/core/monitoring.py`, `sakhi/apps/api/main.py` |
| **CORS** | `sakhi/apps/api/main.py:41-51` |
| **DB** | `sakhi/libs/schemas/db.py`, `sakhi/infra/scripts/migrations/` |
