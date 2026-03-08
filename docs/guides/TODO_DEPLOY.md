# Deployment Checklist

> Last Updated: 2026-03-08

## Environment Variables

Source-of-truth:
- Local dev uses `.env.local` (fallback `.env`) for API/worker and `apps/web/.env.local` for web.
- Production uses Railway/Vercel env dashboards.

| Variable | Dev | Prod | Status |
|----------|-----|------|--------|
| `LAB_DISABLE_STM_EVICT` | `1` (disabled) | `0` or unset | Ensure STM cleanup runs in prod |
| `SAKHI_DISABLE_QUEUE` | `1` (inline) | `0` or unset | Workers run async via Redis in prod |
| `REDIS_URL` | `redis://localhost:6379/0` | Production Redis URL | Required for async workers |
| `DATABASE_URL` | Local PostgreSQL | Production PostgreSQL | Required |
| `OPENAI_API_KEY` | Set | Set | Required for LLM calls |
| `SAKHI_MONITORING_ENABLED` | `0` or `1` | `1` recommended | Enables external incident sink |
| `SAKHI_ALERT_WEBHOOK_URL` | Optional | Set | On-call webhook relay (PagerDuty/Opsgenie/custom) |
| `SAKHI_ALERT_WEBHOOK_BEARER_TOKEN` | Optional | Optional | Bearer token for secured alert webhook sinks |
| `SAKHI_ALERT_WEBHOOK_TIMEOUT_SEC` | Optional (`4`) | Optional (`4`) | Alert webhook timeout in seconds |
| `SAKHI_ALERT_DEDUPE_WINDOW_SEC` | Optional (`180`) | Optional (`180`) | Alert dedupe window in seconds |
| `SAKHI_ALERT_AUTH_FAILURE_THRESHOLD` | Optional (`5`) | Optional (`5`) | Repeated auth-failure burst threshold |
| `SAKHI_ALERT_AUTH_FAILURE_WINDOW_SEC` | Optional (`300`) | Optional (`300`) | Auth-failure burst window (sec) |
| `SAKHI_ALERT_CRASH_LOOP_THRESHOLD` | Optional (`5`) | Optional (`5`) | Crash-loop burst threshold |
| `SAKHI_ALERT_CRASH_LOOP_WINDOW_SEC` | Optional (`300`) | Optional (`300`) | Crash-loop burst window (sec) |
| `SAKHI_ALERT_DATA_ACCESS_SPIKE_THRESHOLD` | Optional (`8`) | Optional (`8`) | Export/delete spike threshold |
| `SAKHI_ALERT_DATA_ACCESS_WINDOW_SEC` | Optional (`600`) | Optional (`600`) | Export/delete spike window (sec) |
| `SAKHI_SENTRY_DSN` | Optional | Optional | Sentry sink for crash/error events |
| `SAKHI_SENTRY_TRACES_SAMPLE_RATE` | Optional (`0`) | Optional (`0`-`0.1`) | Sentry performance traces sample rate |
| `SAKHI_OPERATOR_ACCESS_TOKEN` | Optional | Required if `SAKHI_ENABLE_INTERNAL_ROUTES_IN_PROD=1` | Break-glass token for operator-only internal route access |
| `SAKHI_JOURNAL_MASTER_KEY` | Set (32+ chars) | Set (32+ chars) | Required master secret for per-user journal encryption key derivation |
| `SAKHI_JOURNAL_WRITE_MODE` | `encrypted_only` | `encrypted_only` (default) | Strict journal encryption mode (`dual_write` only for temporary migration windows) |
| `SAKHI_RELEASE` | Optional | Set | Release tag for incident correlation |

## Pre-Deploy Checklist

- [ ] Validate local env contract: `make check-env`
- [ ] Validate Railway env contract in deployment shell: `make check-env-prod-api`
- [ ] Validate Vercel env contract in deployment shell: `make check-env-prod-web`
- [ ] Run `make test` - all tests pass
- [ ] Run `pnpm build` in apps/web - build succeeds
- [ ] Database migrations applied: `make db-migrate`
- [ ] Check `SAKHI_DISABLE_QUEUE=0` for async workers
- [ ] Check `LAB_DISABLE_STM_EVICT=0` for STM cleanup
- [ ] Redis is running and accessible
- [ ] Verify worker process is started: `make worker`

## Production Rollout (Ordered)

- [ ] Set `SAKHI_RELEASE=<git-sha-or-tag>` in Railway API/worker and Vercel web before deploy
- [ ] Run full gate locally: `make pre-deploy`
- [ ] In deployment shells, run env contract gates:
  - API/worker: `make check-env-prod-api`
  - Web: `make check-env-prod-web`
- [ ] Apply DB migrations once for the release: `make db-migrate`
- [ ] Deploy in this order: API -> worker -> web
- [ ] Confirm `/health/live` and `/health/ready` both return `200` after API deploy
- [ ] Run one canary `/v2/turn` for a test user and confirm worker completion

## Encryption + Privacy Gate (Required)

- [ ] `SAKHI_JOURNAL_WRITE_MODE=encrypted_only` in both API and worker runtime
- [ ] `SAKHI_JOURNAL_MASTER_KEY` configured and at least 32 characters
- [ ] Run encryption safety tests: `poetry run pytest sakhi/tests/unit/services/test_journal_crypto.py sakhi/tests/unit/services/test_memory_encrypted_only_paths.py`
- [ ] `SAKHI_DEBUG_RESPONSE=0` in production
- [ ] `SAKHI_ENABLE_INTERNAL_ROUTES_IN_PROD=0` (or unset)
- [ ] If internal routes are explicitly enabled in prod, set `SAKHI_OPERATOR_ACCESS_TOKEN` and require headers (`x-sakhi-operator-token`, `x-sakhi-operator-id`, `x-sakhi-approval-ref`, `x-sakhi-breakglass-reason`)
- [ ] Negative auth check: authenticated user cannot fetch another person's data via mismatched `?user=<uuid>` or cross-user deep-reflection `id`
- [ ] Redaction gate: prompt/journal free-text does not appear in request telemetry rows, API/worker logs, or monitoring sink payloads

## Post-Deploy Smoke + Alerting

- [ ] `/health/live` remains healthy for 15+ minutes
- [ ] `/health/ready` remains healthy for 15+ minutes with DB connectivity
- [ ] Run one normal continuity chat and one deep reflection canary, verify both complete without timeout
- [ ] Verify monitoring sink wiring in logs (`monitoring_setup` event) and confirm no alert-delivery errors
- [ ] Simulate alert policy canaries: repeated auth failures, break-glass allow/deny, crash-loop, and export/delete spike

## Known-User Beta Trust Gate (Required)

Before onboarding users who personally know the team, complete:

- [ ] `SAKHI_DEBUG_RESPONSE=0` in production
- [ ] `SAKHI_ENABLE_INTERNAL_ROUTES_IN_PROD=0` (or unset) in production
- [ ] `SAKHI_JOURNAL_MASTER_KEY` configured in Railway
- [ ] `SAKHI_JOURNAL_WRITE_MODE=encrypted_only` in production (use `dual_write` only as a time-boxed migration override)
- [ ] Monitoring sink configured (`SAKHI_ALERT_WEBHOOK_URL` and/or `SAKHI_SENTRY_DSN`)
- [ ] Production credentials are role-scoped and rotated; no shared personal admin login
- [ ] Break-glass access policy documented (approval + audit trail)
- [ ] Incident response runbook reviewed for current on-call rotation + SLA (`docs/guides/incident-response-runbook.md`)
- [ ] Privacy/trust copy shared with beta users

Reference guide: [`privacy-trust-mvp.md`](./privacy-trust-mvp.md)

## Infrastructure

- **API**: FastAPI on port 8000
- **Web**: Next.js (Vercel or self-hosted)
- **Workers**: RQ workers connected to Redis queue `turn_updates`
- **Database**: PostgreSQL with pgvector extension

## Quick Commands

```bash
# Start API
make dev

# Start workers
make worker

# Run migrations
make db-migrate

# Build web
cd apps/web && pnpm build
```
