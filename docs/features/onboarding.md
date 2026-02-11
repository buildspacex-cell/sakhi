# Onboarding — Phased Operating System Calibration

## Overview

The onboarding flow determines a user's Personal Operating System (OS) through progressive calibration. It runs identically on web and mobile with platform-appropriate design.

## Flow

### Welcome Screen (`/experience`)
- Centered headline: "This is a quiet space to unload your mind."
- **BEGIN** button (gates on auth check completing)
- "What is Sakhi?" modal with 3 swipeable intro cards
- Auth routing: authenticated+onboarded → converse, authenticated → onboarding, unauthenticated → login

### Phase 1 — Core Calibration (3 questions)
1. **Framing**: "What should I call you?" (text input)
2. **Transition**: "I will get to know you gently. Just 3 questions to start."
3. **Clarity time**: When do you feel most clear? (5 options)
4. **Demanding days**: When days get demanding, you usually... (3 options)
5. **First signal**: When life gets busy, what do you notice first? (4 options)
6. **Mirror**: API call `POST /onboarding/submit` (phase1) → OS result with dosha bars
   - "About your Personal OS" modal (Adaptive, Performance, Conservation explained)
   - No strengths/patterns shown (insufficient data after 3 questions)
7. **Follow-up**: "Start a conversation" or "Refine this now"

### Phase 2a — Intermediate Refinement (2 questions)
1. Refine intro transition
2. Current energy (4 options)
3. Body request (4 options)
4. **Intermediate OS**: API call (phase2a) → updated bars + teaser: "Refine further to see your strengths and patterns."
   - "Refine more" or "Start a conversation"

### Phase 2b — Full Calibration (8 questions)
5. Life phase
6. Time horizon
7. Fastest recovery
8. Active roles (multi-select)
9. Responsibility load
10. Decision driver
11. Flexibility under load
12. Body rhythms (skippable — sensitive question)
13. **Final OS**: API call (phase2b) → three-column layout (web) with bars, strengths, and patterns

### Exit
All paths lead to `/experience/converse?user={person_id}`.

## Key Files

| File | Purpose |
|------|---------|
| `apps/web/app/experience/page.tsx` | Welcome screen + auth gate |
| `apps/web/app/experience/onboarding/page.tsx` | Full onboarding flow (web) |
| `apps/mobile/app/onboarding/index.tsx` | Full onboarding flow (mobile) |
| `apps/web/app/api/onboarding/submit/route.ts` | Next.js proxy → FastAPI backend |
| `apps/web/app/api/auth/update-name/route.ts` | Saves name on skip |
| `apps/web/lib/supabase/middleware.ts` | Auth guards for protected routes |
| `sakhi/apps/api/routes/friction_framework.py` | Backend `POST /onboarding/submit` |

## API

### `POST /onboarding/submit`
```json
{
  "person_id": "uuid",
  "source": "web" | "mobile",
  "phase": "phase1" | "phase2a" | "phase2b",
  "responses": { "clarity_window": "early_morning", ... },
  "completed_at": "2024-01-01T00:00:00Z"
}
```

Returns: `OnboardingResponse` with `operating_system`, `dosha_baseline` (vata/pitta/kapha), `os_label`, `os_details` (strengths, patterns_to_watch).

## Design Decisions

- **No skip before Phase 1**: 3 questions is low enough commitment. Users must see their OS result before they can exit.
- **Progressive disclosure**: Phase 1 shows only bars + framework explanation. Phase 2a teases strengths/patterns. Phase 2b reveals everything.
- **Web three-column layout**: Final OS uses `flex-wrap` responsive layout — three columns on wide screens, stacks on narrow.
- **Name saved on any exit**: Fire-and-forget `POST /api/auth/update-name` before navigation.
- **Middleware handles auth races**: If an authenticated user hits `/auth/login?redirect=X`, middleware redirects to X directly.
