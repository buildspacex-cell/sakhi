# Mobile Usage Metrics — Event Contract

> Analytics provider: **PostHog React Native** (client) + **PostHog Python SDK** (server mirror)
> Typed callers: `apps/mobile/lib/analytics/events.ts`
> Client wrapper: `apps/mobile/lib/analytics/client.ts`
> Server helper: `sakhi/libs/analytics.py`

---

## Envelope Properties

Every client event includes these properties automatically (added in `trackEvent()`):

| Property | Type | Description |
|----------|------|-------------|
| `schema_version` | `number` | Schema version (currently `1`). Increment when envelope shape changes. |
| `session_id` | `string` | Per app-open session ID (reset on sign-out) |
| `platform` | `string` | `"ios"` or `"android"` |
| `app_version` | `string` | Expo `version` or build number |

Server-side mirrored events additionally include:

| Property | Type | Description |
|----------|------|-------------|
| `server_side` | `true` | Always `true` — distinguishes server from client events in PostHog |

---

## Phase 1 Events

### Chat Screen (`converse/index.tsx`)

| Event | Trigger | Properties |
|-------|---------|------------|
| `message_sent` | User taps send | — |
| `turn_completed` | API `/v2/turn` returns 2xx | `latency_ms`, `status`, `request_id?`, `has_continuity` |
| `turn_failed` | Non-2xx or network error | `latency_ms`, `status`, `reason` (`timeout`/`network`/`http_error`/`unknown`), `request_id?` |
| `deep_button_shown` | Deep Reflect button becomes enabled | `mode: "whole_story"` |
| `deep_started` | User taps Run Deep | `mode: "whole_story"` |
| `deep_completed` | Deep Reflect result rendered | `mode: "whole_story"`, `latency_ms`, `request_id?` |

### Reflection Screen (`soul/topic-reflection.tsx`)

| Event | Trigger | Properties |
|-------|---------|------------|
| `reflection_opened` | Screen mounts | — |
| `topic_selected` | User taps a topic bubble | `topic_key` |
| `topic_story_completed` | Topic story result rendered | `latency_ms`, `request_id?` |
| `me_story_completed` | Me Story (cross-context) result rendered | `topic_count`, `latency_ms`, `request_id?` |

### Support Console (`account/support.tsx`)

| Event | Trigger | Properties |
|-------|---------|------------|
| `support_report_created` | Report submitted successfully | `diagnostics_enabled` |
| `support_debug_session_started` | Live debug session started | — |

---

## Server-Side Mirroring

`turn_completed` is also emitted from the Python backend (`turn_v2.py` background task) so that client-side drops (network kill, app crash mid-turn) don't create invisible funnel gaps.

Use `server_side = True` in PostHog filters to deduplicate or analyze source breakdown.

| Backend env var | Required | Default |
|-----------------|----------|---------|
| `POSTHOG_SERVER_KEY` | No (prod) | — (server analytics disabled if missing) |
| `POSTHOG_HOST` | No | `https://us.i.posthog.com` |

---

## Privacy Rules (enforced in `events.ts`)

- **No free text**: no message content, journal text, prompt text, or user-input strings in any property
- **No raw IDs**: person_id is set via PostHog `identify()`, never in event properties
- All callers go through `Analytics.*` — no raw `posthog.capture()` from screens
- Analytics opt-out persists via AsyncStorage; respects user toggle in Settings

---

## Identity

- `identifyUser(personId)` called once after auth resolves (`app/_layout.tsx`)
- `resetUser()` called on sign-out (resets PostHog identity + generates new session ID)

---

## Configuration

### Mobile (client)

| Env var | Required | Default |
|---------|----------|---------|
| `EXPO_PUBLIC_POSTHOG_KEY` | Yes (prod) | — (analytics disabled if missing) |
| `EXPO_PUBLIC_POSTHOG_HOST` | No | `https://us.i.posthog.com` |
| `EXPO_PUBLIC_ANALYTICS_ENABLED` | No | `1` (set to `0` to force-disable at build time) |

### Environment Separation

Use a **separate PostHog project per environment** to prevent test data from polluting production dashboards:

| Environment | PostHog project | `EXPO_PUBLIC_POSTHOG_KEY` |
|-------------|----------------|---------------------------|
| dev (local) | — (leave blank) | *(empty — analytics disabled)* |
| staging | "Sakhi Staging" | staging project API key |
| prod | "Sakhi Production" | production project API key |

EAS build profiles (`eas.json`) inject the correct key per profile. Never put a prod key in `.env.local`.

### Kill Switches

- **Build-time**: Set `EXPO_PUBLIC_ANALYTICS_ENABLED=0` to fully disable for a build (useful for CI, automation testing)
- **Runtime (production)**: Use PostHog dashboard → Project Settings → "Pause data ingestion" to stop all new events without a deploy

---

## Data Lifecycle (GDPR / Privacy)

When a user deletes their account or requests data erasure:

1. **DB**: all rows deleted via `POST /dev/reset-user-data` (dev) or the production account-deletion endpoint (to be built)
2. **PostHog**: `analytics.delete_person(person_id)` is called from `sakhi/libs/analytics.py`, which fires the PostHog person deletion API
3. **Retention**: PostHog project retention is set to **90 days** — events older than 90 days are automatically purged

> **When adding a production account-deletion endpoint**: call `from sakhi.libs.analytics import delete_person; delete_person(person_id)` as part of the deletion flow (see note in `dev.py`).

---

## PostHog Dashboards to Build (Phase 2)

- **Activation funnel**: session → message_sent → turn_completed
- **Deep Reflect funnel**: deep_button_shown → deep_started → deep_completed
- **Reflection funnel**: reflection_opened → topic_selected → topic_story_completed
- **Error rate**: turn_failed by `reason` over time
- **Latency p50/p95**: `latency_ms` on `turn_completed`
- **Client vs server coverage**: `turn_completed` grouped by `server_side` to measure client drop rate
