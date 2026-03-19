# Production Launch Guide

> **Status:** Ready to execute — not yet done
> **Scope:** Fresh production environment (Supabase + Railway + Vercel + Mobile)
> **Pre-condition:** All features tested on dev. This is a one-way door — once beta users are on prod, dev stays dev.

---

## Overview

| Layer | Dev (current) | Prod (to create) |
|-------|--------------|-----------------|
| Database | `yiitskcbrcbgbsumxxrx` (Supabase, ap-south-1) | New Supabase project, same region |
| API | Railway — same service, new env vars | Railway — swap env vars, redeploy |
| Web | Vercel — same project, new env vars | Vercel — swap env vars, redeploy |
| Mobile | Dev builds / TestFlight-vidhya profile | New production build → App Store / TestFlight |
| Auth | Dev Supabase auth (dev users) | Fresh auth — zero users |

---

## Step 1 — Create new Supabase project

1. Go to [supabase.com](https://supabase.com) → New project
2. Settings:
   - **Name:** `sakhi-prod`
   - **Region:** `ap-south-1` (Mumbai) — same as dev, keeps Railway latency low
   - **Database password:** Generate strong password, save in 1Password/secure vault
3. Wait for provisioning (~2 min)
4. Collect credentials from **Settings → API**:
   - Project URL: `https://[NEW-REF].supabase.co`
   - `anon` public key
   - `service_role` key (keep secret, never in client code)
5. Collect DB connection strings from **Settings → Database**:
   - **Pooler URL** (for API runtime): Session mode, port 6543
   - **Direct URL** (for migrations only): port 5432, no pooler

---

## Step 2 — Run all migrations on prod DB

Use the **direct connection** (port 5432) — pgbouncer cannot run DDL migrations.

If you are bringing up the current continuity/chat MVP on a slim production database instead of the full legacy schema, do not use the full migration loop below. Use [prod-mvp-database-manifest.md](./prod-mvp-database-manifest.md) as the source of truth for the curated table set and import order, and run [mvp_prod_bootstrap.sql](/Users/fanantics/Documents/Sakhi/sakhi/infra/scripts/migrations/mvp_prod_bootstrap.sql) instead.

```bash
# Direct connection — get from Supabase → Settings → Database → URI
export PROD_DIRECT_URL="postgresql://postgres:[PASSWORD]@db.[NEW-REF].supabase.co:5432/postgres"

# Run all 17 migrations in order
for f in $(ls sakhi/infra/scripts/migrations/*.sql | sort); do
  echo "Running $f..."
  /opt/homebrew/Cellar/libpq/18.1/bin/psql "$PROD_DIRECT_URL" -f "$f"
done
```

**Verify:**
```bash
/opt/homebrew/Cellar/libpq/18.1/bin/psql "$PROD_DIRECT_URL" -c "\dt" | wc -l
# Should be 180+ lines (179 tables + header rows)
```

Expected output: no errors on any migration file. All files use `IF NOT EXISTS` guards so they are safe to re-run if needed.

---

## Step 3 — Construct the prod DATABASE_URL

Take the pooler connection string and append the required pgbouncer params:

```
postgresql://postgres.[NEW-REF]:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require&pgbouncer=true&connect_timeout=15&pool_timeout=0
```

This matches the pattern in the current dev `DATABASE_URL`.

---

## Step 4 — Update Railway (API backend)

Railway → sakhi-api service → Variables tab. **Replace** these 4 vars:

| Variable | New value |
|----------|-----------|
| `DATABASE_URL` | Pooler URL from Step 3 |
| `SUPABASE_URL` | `https://[NEW-REF].supabase.co` |
| `SUPABASE_ANON_KEY` | New anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | New service_role key |

Also set:
| Variable | Value |
|----------|-------|
| `ENV` | `production` |
| `SAKHI_ENFORCE_USER_BINDING` | `1` |
| `SAKHI_SUPPORT_TELEGRAM_BOT_TOKEN` | Your bot token |
| `SAKHI_SUPPORT_TELEGRAM_CHAT_ID` | Your chat ID |

Railway auto-redeploys on save.

**Verify:** `GET https://[railway-url]/health` returns `{"status": "ok"}`.

---

## Step 5 — Update Vercel (web frontend)

Vercel → Project → Settings → Environment Variables. **Replace** these:

| Variable | New value |
|----------|-----------|
| `SUPABASE_URL` | `https://[NEW-REF].supabase.co` |
| `SUPABASE_ANON_KEY` | New anon key |
| `SUPABASE_SERVICE_KEY` | New service_role key |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://[NEW-REF].supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | New anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | New service_role key |

Trigger a manual redeploy after saving.

---

## Step 6 — Update mobile app

### 6a. Create `apps/mobile/.env.prod` (do not commit)

```bash
EXPO_PUBLIC_SUPABASE_URL=https://[NEW-REF].supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=[new anon key]
EXPO_PUBLIC_BACKEND_URL=https://[your-railway-prod-url]

# Production: no bypass
EXPO_PUBLIC_DEV_BYPASS_PERSON_ID=
```

### 6b. Update `apps/mobile/eas.json` production profile

Ensure the `production` profile points to the new Supabase URL and uses normal Supabase auth.

### 6c. Build and submit

```bash
cd apps/mobile

# TestFlight (internal beta)
eas build --platform ios --profile production
eas submit --platform ios --latest

# Or if building for direct TestFlight install:
eas build --platform ios --profile production --auto-submit
```

---

## Step 7 — Smoke test checklist

Run through these manually after deploy:

- [ ] Sign up as a brand new user on prod → email confirmation arrives
- [ ] Complete onboarding flow end to end
- [ ] Send first message in chat → Sakhi responds
- [ ] Send 3+ messages → continuity signal appears
- [ ] Open "Report an issue" → submit a test report → Telegram notification arrives
- [ ] Check Railway logs — no errors, no DB connection failures
- [ ] Verify `/health` endpoint returns OK
- [ ] Verify no dev/test data visible (empty journal, no demo user)

---

## What stays on dev

| Item | Stays on dev |
|------|-------------|
| Vidhya demo user (`6b5b2fbc...`) | ✅ |
| Simulation runs | ✅ |
| Dev resets (`/dev/reset-user-data`) | ✅ |
| Your co-founder test accounts | ✅ |
| All seed/fixture data | ✅ |

---

## Co-founder accounts on prod

You will both create **fresh accounts** on prod — same as any beta user. This means:
- Real onboarding flow (good — you'll feel what users feel)
- Real data accumulation
- No bypass env vars in the production build

For internal testing continue to use the dev environment and the dev-only mobile bypass when needed.

---

## Rollback plan

If prod has issues after launch:
1. Point Railway env vars back to dev DB credentials
2. Vercel: revert env vars, redeploy
3. Mobile: distribute previous TestFlight build

No data loss — dev DB is untouched throughout.

---

## Future migrations

After prod is live, every new migration runs on **both** databases:

```bash
# Apply to prod
export PROD_DIRECT_URL="..."
/opt/homebrew/Cellar/libpq/18.1/bin/psql "$PROD_DIRECT_URL" -f sakhi/infra/scripts/migrations/NNNN_new.sql

# Apply to dev
/opt/homebrew/Cellar/libpq/18.1/bin/psql "$DATABASE_URL_DIRECT" -f sakhi/infra/scripts/migrations/NNNN_new.sql
```

Update `docs/DATABASE_MIGRATIONS.md` to note both environments once prod is live.
