# Unified Messaging Strategy

> How Sakhi becomes the single pane of glass for all your messages — incrementally, pragmatically, and with a long-term pull into Sakhi's own messaging mesh.

---

## The Vision

Sakhi should triage and surface what matters across **all** messaging channels — Gmail, Outlook, Slack, Teams, WhatsApp, Telegram, SMS — so the user sees one intelligent feed, not seven inboxes.

---

## Integration Approaches Evaluated

We evaluated four approaches to cross-channel message intelligence. Each has fundamentally different trade-offs.

### 1. Per-Platform API (OAuth)

**How it works**: Each platform (Gmail, Outlook, Slack, Teams) has an OAuth API. User connects each one. Sakhi polls or subscribes to webhooks for messages.

| Pros | Cons |
|------|------|
| Works on all devices (iOS, Android, desktop) | Must build per-platform adapter |
| Deep access (full message content, threads, metadata) | Some platforms have no personal API (WhatsApp, SMS) |
| Reliable, well-documented | User must auth each service separately |
| Can send replies, not just read | Rate limits vary per platform |
| No app store approval issues | Doesn't cover apps without APIs |

**Feasibility by platform:**

| Platform | API Available? | OAuth? | Can Read? | Can Send? | Effort |
|----------|---------------|--------|-----------|-----------|--------|
| Gmail | Yes (done) | Yes | Yes | Yes | Done |
| Outlook / O365 | Yes (MS Graph) | Yes | Yes | Yes | ~1 week |
| Slack | Yes | Yes | Yes | Yes | ~1 week |
| MS Teams | Yes (MS Graph) | Yes | Yes | Yes | ~1 week (shares Outlook auth) |
| WhatsApp | Business API only | No (API key) | Limited | Yes | High (no personal account API) |
| Telegram | Bot API only | No | Via bot | Via bot | Medium (user must interact with bot) |
| SMS/iMessage | No | No | No | No | Not possible via API |
| Signal | No | No | No | No | Not possible via API |

### 2. Mobile Notification Listener

**How it works**: Android's `NotificationListenerService` reads ALL notifications from all apps. No per-app auth needed.

| Pros | Cons |
|------|------|
| One integration covers ALL apps | **Android only — iOS has no equivalent** |
| No per-app OAuth needed | Read-only (can't send replies) |
| Captures WhatsApp, SMS, Signal, etc. | Notifications only — no full message history |
| Low maintenance per app | Requires special Android permission |
| Gets sender + preview text | Truncated content (notification preview only) |

**iOS blocker**: Apple does not allow apps to read other apps' notifications. There is no `NotificationListenerService` equivalent on iOS. This is a fundamental platform restriction, not a technical challenge — Apple's security model explicitly prevents cross-app notification access. No workaround exists outside of jailbreaking.

**Android implementation**: Requires a native module in the Expo/React Native app:
```
expo-notification-listener (custom native module)
  └── Android NotificationListenerService
       └── onNotificationPosted() → extract sender, text, app
            └── POST to Sakhi API → message_events table
```

**Google Play Store risk**: Google restricts `NotificationListenerService` to accessibility and companion device apps. Apps using it purely for "reading other apps' messages" may be rejected or flagged. Would need careful framing.

### 3. Mobile Agent ("Computer Use" for Phone)

**How it works**: An Android `AccessibilityService` literally operates the phone like a human — opens apps, scrolls, reads screen content, taps buttons.

| Pros | Cons |
|------|------|
| Can read AND interact with any app | **iOS: completely impossible** |
| No per-app API needed | Play Store almost certainly rejects it |
| Full message content, not just notifications | Fragile — breaks when apps update UI |
| Could auto-reply, archive, etc. | Requires native Kotlin/Java module |
| Most powerful approach | Battery/performance impact |
| | Users nervous about "AI controlling my phone" |
| | Months of development for reliability |

**iOS blocker**: iOS has no `AccessibilityService` equivalent. Apps cannot control other apps, read screen content, or simulate taps. Full stop.

**Play Store blocker**: Google restricts `AccessibilityService` to actual accessibility apps. Using it to read other apps' content will likely get the app rejected, flagged, or removed. The policy explicitly prohibits "using AccessibilityService for purposes other than helping users with disabilities."

**Verdict**: Not viable for a shipping product. Interesting for research/prototype only.

### 4. Desktop Agent

**How it works**: Sakhi's existing desktop agent (browser automation, screen vision) reads messages from web-based apps (Gmail web, Slack web, Teams web).

| Pros | Cons |
|------|------|
| Already partially built | **Corporate IT blocks installations on work machines** |
| Can read web-based messaging apps | Only works on personal computers |
| Computer use is more mature than mobile use | Requires always-running desktop app |
| | Doesn't cover phone-only apps (WhatsApp, SMS) |
| | The people who need unified messaging most (office workers) can't install it |

**Corporate IT blocker**: Most companies use MDM (Mobile Device Management) that prevents installing unauthorized software. The exact audience that juggles Gmail + Outlook + Slack + Teams is the audience that can't install a desktop agent.

---

## Chosen Strategy: Incremental + Bridge + Long-Term Pull

Build incrementally. Solve what we can today with APIs. Bridge the gaps with "Share with Sakhi." Let the ecosystem mature. Pull users into Sakhi's own messaging over time.

### Layer 1: Contact Preferences & Priority System (Now)
**Time**: ~1 day | **Value**: High | **Risk**: None

Before adding more channels, make the existing email digest smarter with user-defined priorities. This layer is **channel-agnostic** — when we add Outlook, Slack, or Sakhi messaging, the same preference system applies.

See: [Contact Preferences Design](#contact-preferences-design) below.

### Layer 2: API Integrations for Work Tools (Next)
**Time**: ~1 week per platform | **Value**: High | **Risk**: Low

Add OAuth adapters for platforms with proper APIs:
1. **Outlook / O365** (Microsoft Graph API) — corporate email
2. **Slack** — async work messaging
3. **MS Teams** — shares MS Graph auth with Outlook

These three + Gmail cover 90% of work messaging for knowledge workers.

### Layer 3: "Share with Sakhi" Bridge (Parallel)
**Time**: ~3 days | **Value**: Medium-High | **Risk**: None

For channels with no API (WhatsApp, Telegram, SMS):
- **iOS Share Extension** + **Android Share Target** — user shares content from any app to Sakhi
- Sakhi extracts: commitments, deadlines, action items, sender context
- Stored in the same commitment/triage system as email
- One tap from any app — no API needed, no platform restrictions

This is the bridge for channels we can't access directly. It won't give us "nothing urgent on WhatsApp" confidence, but it captures **what matters** — the commitments and action items the user cares about.

**The habit-building angle**: Every time a user shares a WhatsApp message to Sakhi and gets a tracked commitment back, they're training themselves that "Sakhi is where my commitments live." This is how you organically pull people toward Sakhi messaging later.

### Layer 4: Desktop Agent for B2C Power Users (Later)
**Time**: ~2-3 weeks | **Value**: High for personal users | **Risk**: Low (no gatekeepers)

For B2C personal use, the desktop is unrestricted. Every messaging app has a web/desktop version:
- WhatsApp Web, Telegram Web/Desktop, Signal Desktop, iMessage (macOS), Google Messages Web
- Desktop agent reads these via screen capture + vision
- User's personal computer = no corporate IT blocking, no App Store approval

This gives full "nothing urgent anywhere" confidence for users willing to run the desktop agent. Complements APIs (which are more reliable but don't cover WhatsApp/Telegram).

### Layer 5: Sakhi Messaging + Mesh (Long-Term)
**Time**: Months | **Value**: Transformative | **Risk**: Adoption

The endgame: people start messaging **through** Sakhi instead of through WhatsApp/Telegram.
- Sakhi-to-Sakhi mesh already architecturally planned (Phase 3 in BUILD_PLAN)
- If Sakhi is where commitments, triage, and context live, messaging through Sakhi is the natural next step
- "Why am I copying messages from WhatsApp to Sakhi? I'll just message through Sakhi."
- Each layer above trains the habit and builds the value that makes this adoption organic

### Layer 6: Ecosystem Maturity (Hope + Position)
**Time**: TBD | **Value**: Varies | **Risk**: Out of our control

Things that may improve over time:
- WhatsApp may open a personal messaging API (they've been moving toward business APIs)
- Apple may relax iOS restrictions (unlikely but possible under regulatory pressure)
- Android notification listener policies may become clearer
- New standards for cross-app messaging intelligence may emerge

**Position, don't wait**: Build the adapter interface now so when a new API opens, adding it is a 1-week task, not a redesign.

### Enterprise Track (Parallel Opportunity)
**Time**: After B2C proven | **Value**: Very high revenue | **Risk**: Compliance overhead

Position Sakhi as employee wellness + productivity for enterprises:
- Company deploys via MDM, SSO via Okta/Azure AD
- Admin-consented OAuth covers Gmail/Outlook/Slack/Teams for entire org
- Desktop agent is IT-sanctioned (not blocked, pushed)
- Aggregate anonymized burnout/boundary dashboards for HR
- Individual Ayurvedic wellness + triage for employees
- Personal messaging (WhatsApp) intentionally out of scope — that's a feature ("we protect your work boundaries, we don't touch your personal life")

---

## Contact Preferences Design

The highest-value, lowest-effort next step. Works with the existing email infrastructure.

### Data Model

```sql
CREATE TABLE contact_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,

    -- Contact identification (works across channels)
    contact_identifier TEXT NOT NULL,  -- email address, phone number, Slack handle
    channel TEXT NOT NULL DEFAULT 'email',  -- email, slack, teams, whatsapp, etc.

    -- Relationship
    display_name TEXT,           -- "Sarah Chen"
    relationship TEXT,           -- boss, family, colleague, client, vendor, friend
    organization TEXT,           -- "Acme Corp", "Mom's side"

    -- Priority
    priority TEXT NOT NULL DEFAULT 'normal',  -- critical, high, normal, low, muted

    -- Behavior notes (for LLM context)
    notes TEXT,                  -- "Always reply same day", "Can wait until Monday"

    -- Auto-learned
    learned_from TEXT,           -- 'user_set', 'dismiss_pattern', 'reply_speed'
    confidence FLOAT DEFAULT 1.0,  -- 1.0 for user-set, lower for inferred

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(person_id, contact_identifier, channel)
);
```

### How It Improves the Digest

The LLM triage prompt gets injected with preference context:

```
The user has set these contact preferences:
- sarah@acme.com: BOSS at "Acme Corp" (priority: critical) — "Always reply same day"
- mom@gmail.com: FAMILY (priority: high)
- newsletter@substack.com: priority MUTED
- vendor@saas.com: VENDOR (priority: low) — "Only urgent if mentions 'renewal'"
```

This transforms generic triage into personalized intelligence.

### Contextual Learning (Automatic)

Every user action teaches Sakhi about priorities:
- **Dismiss 3 emails from same sender** → suggest "Mute this sender?"
- **Always open emails from X immediately** → infer high priority
- **Reply to Y within minutes** → infer critical relationship
- **Never reply to Z** → infer low priority

These inferences get stored with `learned_from='dismiss_pattern'` and lower confidence, so explicit user settings always win.

### UI: "People & Priorities" Panel

On the Me page, a new settings section:

```
┌─────────────────────────────────────────────────┐
│  People & Priorities                              │
│                                                   │
│  ★ Critical                                       │
│  ┌───────────────────────────────────────────┐   │
│  │ Sarah Chen · Boss at Acme Corp             │   │
│  │ sarah@acme.com · "Always reply same day"   │   │
│  └───────────────────────────────────────────┘   │
│                                                   │
│  ▲ High                                           │
│  ┌───────────────────────────────────────────┐   │
│  │ Mom · Family                               │   │
│  │ mom@gmail.com                              │   │
│  └───────────────────────────────────────────┘   │
│                                                   │
│  🔇 Muted (3)                                     │
│  newsletter@substack.com, promo@store.com, ...   │
│                                                   │
│  [+ Add contact]                                  │
│                                                   │
│  💡 Sakhi noticed you always dismiss emails from  │
│     vendor@saas.com. Mute them?  [Yes] [No]      │
└─────────────────────────────────────────────────┘
```

### API Endpoints

```bash
# List preferences
GET /email/preferences?person_id=<uuid>

# Set/update a preference
PUT /email/preferences
Body: {
  "contact_identifier": "boss@acme.com",
  "channel": "email",
  "display_name": "Sarah Chen",
  "relationship": "boss",
  "organization": "Acme Corp",
  "priority": "critical",
  "notes": "Always reply same day"
}

# Delete a preference
DELETE /email/preferences/<id>?person_id=<uuid>

# Get Sakhi's suggestions (from dismiss/reply patterns)
GET /email/preferences/suggestions?person_id=<uuid>
```

---

## Platform Limitation Summary

| Capability | Android | iOS |
|-----------|---------|-----|
| Per-platform API (Gmail, Outlook, Slack) | Yes | Yes |
| Notification listener (all apps) | Yes (NotificationListenerService) | **No** |
| Mobile agent (control other apps) | Technically yes (AccessibilityService) but Play Store blocks | **No** |
| Desktop agent | Yes (but corporate IT blocks) | Yes (but corporate IT blocks) |

**Bottom line**: For a shipping product, **API-first is the only approach that works across iOS and Android**. The notification listener is an Android-only bonus. The mobile agent is not viable for production.

---

## Files

| File | Purpose |
|------|---------|
| This doc | Strategy and approach analysis |
| [email-intelligence.md](./email-intelligence.md) | Current email pipeline (V1 complete) |
| [BUILD_PLAN.md](../BUILD_PLAN.md) | Unified Messaging Pipeline architecture decision |

---

## Timeline

| Layer | What | When | Depends On |
|-------|------|------|------------|
| 1 | Contact Preferences & Priorities | Next sprint | Nothing (standalone) |
| 2a | Outlook adapter (MS Graph) | After Layer 1 | Layer 1 for smart triage |
| 2b | Slack adapter | After 2a | Shared adapter interface |
| 2c | Teams adapter | With 2a (shared MS Graph auth) | Same as Outlook |
| 3 | Share-to-Sakhi (iOS Share Extension + Android Share Target) | Parallel with Layer 2 | Mobile app (Expo) |
| 4 | Desktop agent messaging triage (WhatsApp Web, Telegram Web) | After Layer 2 | Existing desktop agent |
| 5 | Sakhi messaging + mesh | After adoption proves value | Layers 1-4 building habits |
| 6 | Ecosystem maturity (new APIs, policy changes) | Ongoing | Position adapter interface now |
| E | Enterprise track (SSO, admin consent, HR dashboards) | After B2C proven | SOC 2, DPA, security review |

---

## Key Insight: The Funnel

```
Layer 1-2: APIs give Sakhi deep access to work channels
                    ↓
Layer 3: "Share with Sakhi" teaches users that Sakhi = where commitments live
                    ↓
Layer 4: Desktop agent gives full coverage for power users
                    ↓
Layer 5: Users start messaging THROUGH Sakhi (natural pull, not forced)
                    ↓
Layer 6: Ecosystem opens up → Sakhi adds channels instantly (adapter already built)
```

Each layer is valuable on its own. Each layer also pulls users closer to Sakhi as their cognitive home base. The endgame isn't "read all their apps" — it's "they don't need 7 apps anymore."
