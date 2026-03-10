# Sakhi Startup Guide

> **Status: Application is COMPLETE** — just needs configuration and startup.

---

## What's Already Built

| Component | Status |
|-----------|--------|
| Google OAuth Login | ✅ `/auth/login` with full OAuth flow |
| OAuth Callback | ✅ `/auth/callback` creates `auth_users` record |
| Auth Middleware | ✅ Protects `/experience/*` routes |
| Onboarding Flow | ✅ 7-screen questionnaire → Operating System |
| Chat UI | ✅ Full conversation interface |
| Turn Processing | ✅ `/v2/turn` with context loading |
| 51 Workers | ✅ All tested and passing |
| Inline Worker Mode | ✅ `SAKHI_DISABLE_QUEUE=1` for no-Redis mode |
| Migration Script | ✅ `python -m sakhi.infra.scripts.migrate` |

---

## Quick Start (Development)

### 1. Start Infrastructure

```bash
# Start PostgreSQL and Redis
docker-compose -f docker-compose.local.yml up -d
```

### 2. Configure Environment

**Create `apps/web/.env.local`:**
```bash
# Supabase (get from Supabase dashboard)
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# API Base (Python backend)
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

**Create `.env` (root) for Python API:**
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/sakhi

# Supabase
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# LLM (using OpenRouter with DeepSeek)
LLM_ROUTER=OPENROUTER
OPENROUTER_API_KEY=sk-or-...
MODEL_CHAT=deepseek/deepseek-chat
MODEL_TOOL=deepseek/deepseek-chat

# Workers - INLINE MODE (no Redis required)
SAKHI_DISABLE_QUEUE=1

# Or for async mode with Redis:
# REDIS_URL=redis://localhost:6379/0
```

### 3. Apply Database Migrations

```bash
cd sakhi
python -m sakhi.infra.scripts.migrate
```

### 4. Start Services

**Terminal 1 - Python API:**
```bash
cd sakhi
python -m uvicorn apps.api.main:app --reload --port 8000
```

**Terminal 2 - Next.js Frontend:**
```bash
cd apps/web
pnpm install
pnpm dev
```

### 5. Access the App

1. Open http://localhost:3000
2. You'll be redirected to `/auth/login`
3. Click "Continue with Google"
4. Complete onboarding questionnaire
5. Start chatting!

---

## Supabase Setup

### Required Configuration

1. **Create Supabase Project** at https://supabase.com

2. **Enable Google OAuth:**
   - Go to Authentication → Providers → Google
   - Enable and add your Google OAuth credentials
   - Set redirect URL: `http://localhost:3000/auth/callback`

3. **Create `auth_users` table** (if not using migrations):
```sql
CREATE TABLE auth_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supabase_user_id UUID UNIQUE NOT NULL,
    email TEXT NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    onboarding_completed_at TIMESTAMPTZ,
    last_sign_in_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

4. **Get API Keys:**
   - Project Settings → API
   - Copy `URL`, `anon public`, and `service_role` keys

---

## Worker Modes

### Option A: Inline Mode (Simplest - No Redis)

Set in `.env`:
```bash
SAKHI_DISABLE_QUEUE=1
```

Workers run synchronously after each turn. Simpler but adds ~2-5s to response time.

### Option B: Async Mode (Production)

Set in `.env`:
```bash
REDIS_URL=redis://localhost:6379/0
# Don't set SAKHI_DISABLE_QUEUE
```

Start worker process:
```bash
cd sakhi
rq worker turn_updates
```

Workers run in background. Faster responses, requires Redis.

---

## Full Environment Variables Reference

**Source-of-truth policy**
- Local development:
  - API/worker runtime reads `.env.local` (if present), then `.env`.
  - Web runtime reads `apps/web/.env.local`.
- Production:
  - Set env vars in Railway (API/worker) and Vercel (web).
  - Do not rely on `.env` files in production containers.
- No template env files are maintained; update `.env.local`/`.env` directly for local runtime.

### Next.js (`apps/web/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key (server-side) |
| `NEXT_PUBLIC_API_BASE` | Yes | Python API URL (default: `http://localhost:8000`) |

### Expo Mobile (`apps/mobile/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `EXPO_PUBLIC_BACKEND_URL` | Yes | Python API URL reachable by simulator/device |
| `EXPO_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `EXPO_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anon/public key |
| `EXPO_PUBLIC_DEV_BYPASS_PERSON_ID` | Optional (dev only) | Bypass mobile login in `__DEV__` and force a specific `person_id` for end-to-end profile testing (works with backend dev mode / `SAKHI_ENFORCE_USER_BINDING=0`) |
| `EXPO_PUBLIC_RELEASE_BYPASS_ENABLED` | Optional (internal TestFlight only) | Enables release fixed-profile bypass in non-dev builds (Fastlane/EAS) |
| `EXPO_PUBLIC_RELEASE_BYPASS_PERSON_ID` | Optional (internal TestFlight only) | Fixed `person_id` used by release bypass |

### Python API (`.env` in root)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase service role key |
| `LLM_ROUTER` | Yes | `OPENROUTER` or `OPENAI` |
| `OPENROUTER_API_KEY` | If OpenRouter | OpenRouter API key |
| `OPENAI_API_KEY` | If OpenAI | OpenAI API key |
| `MODEL_CHAT` | Yes | Chat model (e.g., `deepseek/deepseek-chat`) |
| `MODEL_TOOL` | Yes | Tool model (e.g., `deepseek/deepseek-chat`) |
| `SAKHI_DISABLE_QUEUE` | Optional | Set to `1` for inline worker mode |
| `REDIS_URL` | If async | Redis connection URL |

---

## Verification Checklist

After starting, verify each component:

### 1. Auth Flow
```bash
# Visit and expect redirect to login
curl -I http://localhost:3000/experience
# Should return 307 redirect to /auth/login
```

### 2. API Health
```bash
curl http://localhost:8000/health
# Should return {"status": "ok"}
```

### 3. Database Connection
```bash
cd sakhi
python -c "import asyncio; from sakhi.apps.api.core.db import q; print(asyncio.run(q('SELECT 1')))"
# Should print [{'?column?': 1}]
```

### 4. Worker Test
```bash
cd sakhi
python -m sakhi.tests.all_workers_test --user-id <YOUR_USER_ID>
# Should show 51/51 passing
```

---

## Troubleshooting

### "Not authenticated" on API calls
- Check Supabase keys are correct
- Verify cookies are being set (check browser DevTools)
- Ensure `SUPABASE_SERVICE_ROLE_KEY` is set for server routes

### Workers not running
- If using inline mode: Check `SAKHI_DISABLE_QUEUE=1` is set
- If using async mode: Ensure `rq worker turn_updates` is running
- Check Redis is accessible: `redis-cli ping`

### Database errors
- Run migrations: `python -m sakhi.infra.scripts.migrate`
- Check `DATABASE_URL` is correct
- Verify PostgreSQL is running: `docker ps`

### LLM errors
- Verify `OPENROUTER_API_KEY` or `OPENAI_API_KEY` is valid
- Check model names are correct for your provider
- Test with: `curl https://openrouter.ai/api/v1/models -H "Authorization: Bearer $OPENROUTER_API_KEY"`

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js)                                              │
│  localhost:3000                                                  │
│  ├─ /auth/login → Google OAuth                                  │
│  ├─ /auth/callback → Creates auth_users, redirects              │
│  ├─ /experience/onboarding → 7-screen questionnaire             │
│  └─ /experience/converse → Chat interface                       │
└────────────────────────┬────────────────────────────────────────┘
                         │ POST /api/turn-v2 (proxied)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI)                                               │
│  localhost:8000                                                  │
│  ├─ POST /v2/turn → Process message, generate response          │
│  ├─ POST /onboarding/complete → Compute Operating System        │
│  └─ Workers (inline or async) → Enrich personal_model           │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌─────────────────────────────────────────────────────────────────┐
│  DATABASE                                                        │
│  ├─ PostgreSQL (Supabase or local)                              │
│  │   ├─ auth_users → User identity (person_id)                  │
│  │   ├─ personal_model → All intelligence state                 │
│  │   └─ memory_episodic → Episodes with state vectors           │
│  └─ Redis (optional, for async workers)                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## What Happens When a User Signs Up

1. **User clicks "Continue with Google"** → Redirected to Google OAuth
2. **Google authenticates** → Redirects to `/auth/callback`
3. **Callback handler**:
   - Exchanges code for Supabase session
   - Creates `auth_users` record (this ID = `person_id`)
   - Redirects to `/experience`
4. **Middleware checks** → No onboarding? Redirect to `/experience/onboarding`
5. **User completes onboarding** → POST to `/onboarding/complete`
   - Computes dosha baseline (Prakruti)
   - Creates `personal_model` with Operating System
   - Sets `onboarding_completed_at`
6. **User starts chatting** → Each turn:
   - Loads all context from `personal_model`
   - Generates personalized response
   - Workers enrich understanding in background

---

## Production Deployment

For production, you'll want:

1. **Supabase** (managed PostgreSQL + Auth)
2. **Railway/Render/Fly.io** for Python API
3. **Vercel** for Next.js frontend
4. **Upstash Redis** (if using async workers)

Set environment variables in each platform's dashboard.

---

The application is architecturally complete. Just add configuration and run!
