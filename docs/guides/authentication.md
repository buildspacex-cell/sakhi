# Google OAuth Authentication Setup

This document explains how to set up Google OAuth authentication for Sakhi using Supabase Auth.

## Overview

The authentication flow:
1. User clicks "Continue with Google" on `/auth/login`
2. Supabase redirects to Google OAuth consent screen
3. User grants permission
4. Google redirects back to `/auth/callback`
5. Callback creates/updates `auth_users` record (the `id` becomes `person_id`)
6. User is redirected to `/experience`

## Setup Steps

### 1. Install Dependencies

```bash
cd apps/web
pnpm install
```

This installs `@supabase/ssr` which was added to package.json.

### 2. Run Database Migration

```bash
# From the sakhi directory
psql $DATABASE_URL -f sakhi/infra/scripts/migrations/0029_supabase_auth.sql
```

This creates the `auth_users` table which links Supabase Auth users to person IDs.

### 3. Configure Supabase Project

#### Enable Google Provider in Supabase Dashboard:

1. Go to your Supabase project dashboard
2. Navigate to **Authentication** → **Providers**
3. Find **Google** and enable it
4. You'll need to provide:
   - Google Client ID
   - Google Client Secret

#### Get Google OAuth Credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth client ID**
5. Application type: **Web application**
6. Add Authorized JavaScript origins:
   - `http://localhost:3000` (development)
   - `https://your-production-domain.com` (production)
7. Add Authorized redirect URIs:
   - `https://<your-supabase-project>.supabase.co/auth/v1/callback`
8. Copy the Client ID and Client Secret
9. Paste them into Supabase Dashboard

### 4. Configure Environment Variables

Update `apps/web/.env.local`:

```env
# Supabase
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_KEY=<your-service-role-key>
# Mirror to Next.js public vars (required for client bundle)
NEXT_PUBLIC_SUPABASE_URL=${SUPABASE_URL}
NEXT_PUBLIC_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_KEY} # server-only, do not expose to browser

# API
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
```

The Supabase URL and anon key can be found in your Supabase project settings under **API**.

### 5. Configure Supabase Redirect URL

In Supabase Dashboard:
1. Go to **Authentication** → **URL Configuration**
2. Add to **Redirect URLs**:
   - `http://localhost:3000/auth/callback` (development)
   - `https://your-production-domain.com/auth/callback` (production)

## File Structure

```
apps/web/
├── app/
│   ├── auth/
│   │   ├── login/
│   │   │   └── page.tsx          # Login page with Google button
│   │   └── callback/
│   │       └── route.ts          # OAuth callback handler
│   ├── api/
│   │   └── auth/
│   │       └── me/
│   │           └── route.ts      # Get current user's person_id
│   └── experience/
│       └── page.tsx              # Updated to use authenticated user
├── lib/
│   ├── supabase/
│   │   ├── client.ts             # Browser Supabase client
│   │   ├── server.ts             # Server Supabase client
│   │   ├── middleware.ts         # Session refresh middleware
│   │   └── index.ts              # Re-exports
│   └── hooks/
│       └── useAuth.ts            # Auth hook for components
└── middleware.ts                 # Next.js middleware for auth
```

## Database Schema

The `auth_users` table links Supabase Auth users to Sakhi person records:

```sql
CREATE TABLE auth_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  -- This IS the person_id
    supabase_user_id UUID UNIQUE,                   -- Links to auth.users
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_sign_in_at TIMESTAMPTZ,
    onboarding_completed_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);
```

## Flow Diagram

```
┌─────────────────┐
│  /auth/login    │
│  (Google btn)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Supabase Auth  │
│  → Google OAuth │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ /auth/callback  │
│ (creates user)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   /experience   │
│ (fetches user)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   /onboarding   │
│ (with person_id)│
└─────────────────┘
```

## Testing

1. Start the Next.js dev server: `pnpm dev`
2. Navigate to `http://localhost:3000/experience`
3. You should be redirected to `/auth/login`
4. Click "Continue with Google"
5. After authentication, you'll be redirected to `/experience`
6. Check the `auth_users` table to verify the user was created

## Troubleshooting

### "Invalid redirect URI"
- Ensure the redirect URI in Google Cloud Console matches exactly:
  `https://<project>.supabase.co/auth/v1/callback`

### "Failed to fetch user"
- Check that `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are set
- Verify the `auth_users` table exists

### User created but onboarding fails
- Check that the FastAPI backend is running
- Verify `NEXT_PUBLIC_API_BASE_URL` points to the correct endpoint

## Security Notes

- The `person_id` is the `auth_users.id`, NOT the Supabase `auth.users.id`
- All API calls should use this `person_id` for data scoping
- The middleware protects `/experience/*` routes, requiring authentication
- Sessions are managed by Supabase Auth with automatic refresh
