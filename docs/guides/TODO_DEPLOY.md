# Deployment Checklist

> Last Updated: 2026-03-08

## Environment Variables

Source-of-truth:
- Local dev uses `.env.local` (fallback `.env`) for API/worker and `apps/web/.env.local` for web.
- Production uses Railway/Vercel env dashboards; template files are documentation only.

| Variable | Dev | Prod | Status |
|----------|-----|------|--------|
| `LAB_DISABLE_STM_EVICT` | `1` (disabled) | `0` or unset | Ensure STM cleanup runs in prod |
| `SAKHI_DISABLE_QUEUE` | `1` (inline) | `0` or unset | Workers run async via Redis in prod |
| `REDIS_URL` | `redis://localhost:6379/0` | Production Redis URL | Required for async workers |
| `DATABASE_URL` | Local PostgreSQL | Production PostgreSQL | Required |
| `OPENAI_API_KEY` | Set | Set | Required for LLM calls |
| `SAKHI_MONITORING_ENABLED` | `0` or `1` | `1` recommended | Enables external incident sink |
| `SAKHI_ALERT_WEBHOOK_URL` | Optional | Set | On-call webhook relay (PagerDuty/Opsgenie/custom) |
| `SAKHI_SENTRY_DSN` | Optional | Optional | Sentry sink for crash/error events |
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
