# Bug Audit Report

> Generated: 2026-03-10
> Scope: Python backend, React Native mobile app, Next.js web frontend
> Method: Static analysis across all three layers

---

## Quick Summary

| Layer | Critical | High | Medium | Low | Total |
|-------|----------|------|--------|-----|-------|
| Python backend | 0 | 2 | 1 | 0 | **3** |
| Mobile app | 1 | 4 | 5 | 3 | **13** |
| Web frontend | 3 | 4 | 5 | 2 | **14** |
| **Total** | **4** | **10** | **11** | **5** | **30** |

---

## Fix Priority Order

### 🔴 Fix Immediately (Critical + Security)

| # | Layer | File | Lines | Issue |
|---|-------|------|-------|-------|
| 1 | Mobile | `apps/mobile/app/soul/index.tsx` | 84–90 | Auth token never attached to API requests — all calls go unauthenticated |
| 2 | Web | `apps/web/app/api/friction/state/current/route.ts` | 13–42 | No auth check — any client can read any `person_id`'s friction state |
| 3 | Web | `apps/web/app/api/demo/simulation/ledger/route.ts` | 14–24 | No auth check on ledger endpoint — open information disclosure |
| 4 | Web | `apps/web/app/api/chat/route.ts` | 4–5 | `NEXT_PUBLIC_API_KEY` / `EXPO_PUBLIC_API_KEY` used in server route — should be server-only secret |
| 5 | Web | `apps/web/app/api/continuity/policy/route.ts` | 16 | `res.json()` called without `res.ok` check — upstream errors crash the handler |
| 6 | Web | `apps/web/app/api/continuity/reflection/run/route.ts` | 16 | Same `res.json()` without `res.ok` pattern |
| 7 | Web | `apps/web/app/api/events/stream/[person]/route.ts` | 16–22 | `res.body` not null-checked — SSE stream crashes silently when upstream fails |
| 8 | Python | `sakhi/apps/api/routes/turn_v2.py` | 1471–1495 | `relationship_nudges` only defined inside `if nudge_relationships:` block — `NameError` at runtime when list is empty or exception is swallowed |

### 🟠 Fix Soon (High)

| # | Layer | File | Lines | Issue |
|---|-------|------|-------|-------|
| 9 | Mobile | `apps/mobile/app/experience/converse/index.tsx` | 318–349 | `activeContinuitySignal` passes null-check then used unsafely — race condition crash |
| 10 | Mobile | `apps/mobile/app/experience/converse/index.tsx` | 183–235 | Poll loop final `fetchResult()` errors silently swallowed |
| 11 | Mobile | `apps/mobile/app/soul/topic-reflection.tsx` | 287–332 | `setDeepReflectText` called after component unmount — no mounted guard |
| 12 | Mobile | `apps/mobile/lib/auth/AuthContext.tsx` | 180–185 | Safety timeout not properly cleared on dependency change — orphaned timeouts |
| 13 | Python | `sakhi/apps/api/services/agent/chat_bridge.py` | 756–797 | `_task_executions` dict mutated by background `asyncio.create_task` with no lock |
| 14 | Web | `apps/web/app/api/calendar/today/route.ts` | 10–20 | No auth check — calendar data for any `user` param accessible |
| 15 | Web | `apps/web/app/api/turn-v2/route.ts` | 8–11 | `user` query param not validated as UUID before forwarding to backend |

### 🟡 Fix When Possible (Medium)

| # | Layer | File | Lines | Issue |
|---|-------|------|-------|-------|
| 16 | Mobile | `apps/mobile/app/experience/converse/index.tsx` | 237–315 | Stale auth token if session refreshes mid-request — `useCallback` captures old token |
| 17 | Mobile | `apps/mobile/app/experience/converse/index.tsx` | 179–181 | `ensureContinuityPolicyEnabled()` rejection silently ignored via `void` |
| 18 | Mobile | `apps/mobile/lib/config.ts` | 67–74 | Bypass `person_id` env vars not validated as UUIDs — invalid values pass silently |
| 19 | Mobile | `apps/mobile/app/soul/topic-reflection.tsx` | 391–407 | Non-fetch errors not typed correctly — 403 retry logic silently breaks |
| 20 | Mobile | `apps/mobile/app/soul/topic-reflection.tsx` | 363–374 | Rapid `openMoment` calls leave animation state inconsistent |
| 21 | Python | `sakhi/apps/api/main.py` | 145–149 | `focus_path_router` and `micro_momentum_router` imported twice — second import shadows first |
| 22 | Web | `apps/web/app/api/turn-v2/route.ts` | 18–22 | Silent JSON parse fallback may leak raw backend error messages |
| 23 | Web | `apps/web/app/api/agent/approvals/` | 25–29 | Same silent JSON parse fallback pattern in agent approval routes |
| 24 | Web | `apps/web/app/api/events/stream/[person]/route.ts` | 15–22 | Hardcoded `text/event-stream` content-type even on error responses |
| 25 | Web | `apps/web/lib/hooks/useVoice.ts` | 225–310 | `onstop` async callback runs after unmount — state update on unmounted component |
| 26 | Web | `apps/web/app/experience/calendar/client.tsx` | 144–148 | `.catch(() => null)` swallows all errors — shows "No events" instead of error state |

### ⚪ Low Priority

| # | Layer | File | Lines | Issue |
|---|-------|------|-------|-------|
| 27 | Mobile | `apps/mobile/lib/auth/AuthContext.tsx` | 144–162 | No defensive check on `newSession.user.id` shape |
| 28 | Mobile | `apps/mobile/app/experience/converse/index.tsx` | 422, 444 | Route names cast as `never` — typos not caught at compile time |
| 29 | Mobile | `apps/mobile/app/soul/topic-reflection.tsx` | 71–76 | `shortDate()` returns `""` — some callsites render empty string instead of "Undated" |
| 30 | Web | `apps/web/app/experience/converse/page.tsx` | 137–139 | `<Suspense>` without error boundary — unhandled throws not caught gracefully |

---

## Detailed Findings

### Python Backend

#### BUG-08 — `NameError` on `relationship_nudges` (High)
**File:** `sakhi/apps/api/routes/turn_v2.py:1495`

`relationship_nudges` is only assigned inside `if nudge_relationships:` (line 1477). If the list is empty or an exception is thrown (and swallowed at line 1489), the variable is never defined. The `logger.info` call at line 1495 then raises `NameError`.

```python
# Fix: initialize before the conditional block
relationship_nudges = []
if not scheduling_context.get("intent"):
    try:
        nudge_relationships = await get_relationships_needing_attention(user_id, limit=2)
        if nudge_relationships:
            relationship_nudges = [...]
    except Exception as nudge_exc:
        logger.warning(...)
```

---

#### BUG-13 — Race condition on shared `_task_executions` dict (High)
**File:** `sakhi/apps/api/services/agent/chat_bridge.py:756–797`

`_task_executions` is a module-level dict. A `TaskExecutionState` object is stored at line 756, then a background `asyncio.create_task` mutates the same object (lines 797–798) with no lock. Concurrent requests on the same `task_id` can corrupt state.

**Fix:** Add an `asyncio.Lock` per task entry, or use `asyncio.Queue` to serialize state updates.

---

#### BUG-21 — Duplicate router imports in `main.py` (Medium)
**File:** `sakhi/apps/api/main.py:145–149`

`focus_path_router` is imported twice (lines 145 and 148). `micro_momentum_router` is imported twice (lines 143 and 149). The second import silently shadows the first with no runtime error.

**Fix:** Remove the duplicate import lines 148–149.

---

### Mobile App

#### BUG-01 — Missing auth token in `soul/index.tsx` (Critical)
**File:** `apps/mobile/app/soul/index.tsx:84–90`

The fetch call sends no `Authorization` header. Any backend route enforcing auth binding will reject these requests with 401/403.

```typescript
// Missing:
headers: {
  "Content-Type": "application/json",
  ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
}
```

---

#### BUG-09 — Null-check race on `activeContinuitySignal` (High)
**File:** `apps/mobile/app/experience/converse/index.tsx:318–349`

The condition at line 318 checks `activeContinuitySignal?.topic_key`, but at line 349 the value is accessed directly without optional chaining. If state updates between the guard and the access, this throws.

```typescript
// Line 349 — should be:
topic_key: activeContinuitySignal?.topic_key ?? "",
```

---

#### BUG-11 — setState after unmount in `topic-reflection.tsx` (High)
**File:** `apps/mobile/app/soul/topic-reflection.tsx:287–332`

After `pollTopicReflection()` resolves, `setDeepReflectText()` is called with no check that the component is still mounted. If the user navigates away during polling, this produces a React warning and potential crash.

```typescript
// Fix: add a mounted ref
const mountedRef = useRef(true);
useEffect(() => () => { mountedRef.current = false; }, []);

// Then in runDeepReflect:
const deepText = await pollTopicReflection(reflectionId, personId);
if (deepText && mountedRef.current) {
  setDeepReflectText(deepText);
}
```

---

### Web Frontend

#### BUG-02 / BUG-03 — `res.json()` without `res.ok` check (Critical)
**Files:**
- `apps/web/app/api/continuity/policy/route.ts:16`
- `apps/web/app/api/continuity/reflection/run/route.ts:16`

Calling `await res.json()` on a non-2xx response that returns HTML or plain text (e.g. a 502 from Railway) throws a parse error that crashes the entire route handler, returning 500 to the client.

```typescript
// Fix pattern for all proxy routes:
const res = await fetch(...);
if (!res.ok) {
  return NextResponse.json({ error: "upstream error" }, { status: res.status });
}
const data = await res.json();
```

---

#### BUG-04 / BUG-05 / BUG-14 — Unauthenticated proxy routes (High)
**Files:**
- `apps/web/app/api/friction/state/current/route.ts`
- `apps/web/app/api/demo/simulation/ledger/route.ts`
- `apps/web/app/api/calendar/today/route.ts`

All three accept a `user` or `personId` query parameter with no verification that the authenticated session owns that ID. Any logged-in user can query data belonging to any other user.

**Fix:** Verify session ownership before forwarding:
```typescript
const session = await getServerSession();
if (!session || session.personId !== user) {
  return NextResponse.json({ error: "forbidden" }, { status: 403 });
}
```

---

#### BUG-07 — Null `res.body` in SSE stream (Critical + High)
**File:** `apps/web/app/api/events/stream/[person]/route.ts:16–22`

`res.body` is `null` when the upstream fetch fails. Passing `null` to `new Response()` creates a broken stream with no error returned to the client.

```typescript
// Fix:
if (!res.ok || !res.body) {
  return new Response("upstream error", { status: res.status || 502 });
}
return new Response(res.body, { headers: { "Content-Type": "text/event-stream" } });
```

---

## Status Tracking

- [ ] BUG-01: Mobile auth token missing (`soul/index.tsx`)
- [ ] BUG-02: `res.json()` without `res.ok` (continuity/policy)
- [ ] BUG-03: `res.json()` without `res.ok` (continuity/reflection/run)
- [ ] BUG-04: No auth check (friction/state/current)
- [ ] BUG-05: No auth check (demo/simulation/ledger)
- [ ] BUG-06: No auth check (calendar/today) ← see BUG-14
- [ ] BUG-07: Null `res.body` in SSE stream
- [ ] BUG-08: `NameError` on `relationship_nudges` (turn_v2.py)
- [ ] BUG-09: Null-check race on `activeContinuitySignal`
- [ ] BUG-10: Silent error swallow in poll loop
- [ ] BUG-11: setState after unmount (topic-reflection)
- [ ] BUG-12: Orphaned timeout in AuthContext
- [ ] BUG-13: Race condition on `_task_executions` dict
- [ ] BUG-14: No auth check (calendar/today)
- [ ] BUG-15: Unvalidated `user` param in turn-v2
- [ ] BUG-16: Stale auth token in sendMessage callback
- [ ] BUG-17: `ensureContinuityPolicyEnabled` rejection ignored
- [ ] BUG-18: Bypass person IDs not validated
- [ ] BUG-19: Non-fetch errors break 403 retry logic
- [ ] BUG-20: Rapid `openMoment` animation inconsistency
- [ ] BUG-21: Duplicate router imports (main.py)
- [ ] BUG-22: Silent JSON parse leaks backend errors (turn-v2)
- [ ] BUG-23: Silent JSON parse in agent approvals routes
- [ ] BUG-24: Wrong content-type on SSE error responses
- [ ] BUG-25: `useVoice` setState after unmount
- [ ] BUG-26: Calendar client swallows all errors
- [ ] BUG-27: No defensive check on session shape
- [ ] BUG-28: Route names cast as `never`
- [ ] BUG-29: `shortDate()` empty string not handled
- [ ] BUG-30: Converse page missing error boundary
