# Deployment Checklist

> Last Updated: 2026-02-03

## Environment Variables

| Variable | Dev | Prod | Status |
|----------|-----|------|--------|
| `LAB_DISABLE_STM_EVICT` | `1` (disabled) | `0` or unset | Ensure STM cleanup runs in prod |
| `SAKHI_DISABLE_QUEUE` | `1` (inline) | `0` or unset | Workers run async via Redis in prod |
| `REDIS_URL` | `redis://localhost:6379/0` | Production Redis URL | Required for async workers |
| `DATABASE_URL` | Local PostgreSQL | Production PostgreSQL | Required |
| `OPENAI_API_KEY` | Set | Set | Required for LLM calls |

## Pre-Deploy Checklist

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
