# Execution Priority

> Ship order for Sakhi — foundation first, differentiation second, distribution third, expansion last.

Last Updated: 2026-02-26

---

## The Sequence Logic

```
[1] Preferences     → Make existing email intelligence personalized
[2] Ayurvedic Engine → Make Sakhi's core intelligence world-class
[3] App Store Ship   → Get it into users' hands
[4] Share to Sakhi   → Bridge the messaging gap (no API needed)
[5] API Connects     → Outlook, Slack, Teams integration
[6] Desktop Agent    → Full coverage for B2C power users
[7] Android          → Second platform
```

Each layer depends on the ones above it being solid. Shipping a mediocre app fast is worse than shipping a differentiated app slightly later.

---

## Priority 1: Contact Preferences & Priority System

**Status**: Complete
**Effort**: ~3-5 days
**Depends on**: Nothing (standalone, builds on existing Gmail infrastructure)

### What

User-defined contact priorities that make the email digest (and future channels) personally intelligent. Transforms generic triage ("this email looks important") into personalized triage ("your boss emailed — she's marked critical, and you told Sakhi to always reply same day").

### Why First

- Highest value-to-effort ratio on the board
- Makes the existing email digest dramatically better with minimal code
- The preference system is **channel-agnostic** — when Outlook/Slack/Teams arrive, same preferences apply
- Builds the "People & Priorities" UI that becomes the relationship layer for all of Sakhi

### Scope

- `contact_preferences` table (person_id, contact_identifier, channel, relationship, priority, notes)
- API: CRUD endpoints for preferences
- Digest enhancement: inject preference context into LLM triage prompt
- Frontend: "People & Priorities" panel on Me page
- Auto-learning foundation: track dismiss/reply patterns, suggest priority changes

### Key Design

See [unified-messaging-strategy.md — Contact Preferences Design](./features/unified-messaging-strategy.md#contact-preferences-design) for full schema, API, and UI mockup.

---

## Priority 2: Ayurvedic Engine — Contextual Intelligence

**Status**: Context Router complete. Context injection complete. Governance kernel (kala) complete and integrated into pipeline. Conversation quality improvements (personalization, adaptive prompt, JSONB parsing fixes) complete.
**Effort**: ~2-3 weeks
**Depends on**: Priority 1 (preferences feed context)

### What

Nail the Ayurvedic reasoning engine with contextual "open claw" approach for context injection. Sakhi should reason about the user's state (Vata/Pitta/Kapha imbalance) using all available signals — email patterns, journal entries, calendar density, time of day, boundary erosion — and inject this context into every conversation naturally.

### Context Router (Complete)

The Context Router (OpenClaw approach) ensures the LLM always has 360-degree awareness while keeping prompts focused:

- **Tier 1 (always)**: Compact one-liner per module from cheap/always-computed data — identity momentum, emotional state, moment mode, friction, morning/evening/micro cache, reflection
- **Tier 2 (router-gated)**: Full detailed sections only for modules the router selects — identity & growth, emotional attunement, moment intelligence, morning/evening ritual, micro flow, daily reflection
- **Hybrid router**: Deterministic keyword/pattern classification first (13 modules), GPT-4o-mini LLM fallback when confidence < 0.5
- **Cost optimization**: Expensive LLM calls (inner_dialogue, evidence_pack, causal reasoning, recommendations) gated by router. Cheap computations (identity frames, moment_model, cache reads) always run.

See [features/context-routing.md](./features/context-routing.md) for full architecture.

### Why Second

- This is Sakhi's **core differentiator**. Without deep Ayurvedic intelligence, Sakhi is just another email triage tool.
- The engine needs to be compelling before we ship to App Store — first impressions matter.
- Preferences (Priority 1) feed the engine: "You've been avoiding emails from your boss for 12 days. That's Kapha stagnation in your professional relationships."
- Email signals already detect boundary erosion, cognitive load, avoidance — the engine needs to *reason* about them, not just report them.

### Scope

- Context injection pipeline: gather signals from all sources → compose context window → inject into conversation
- Causal reasoning: connect behavioral patterns to Ayurvedic states ("late-night emails 3 days in a row → Vata aggravation → recommend grounding")
- Proactive surfacing: engine decides *when* to bring up insights, not just respond when asked
- Friction framework integration: map email/calendar/behavioral signals to Vata/Pitta/Kapha friction types
- Personalized recommendations based on user's prakruti (constitution) + current vikriti (imbalance)

### Key Outcome

A user who talks to Sakhi should feel *understood* — not just informed. "Your email load is high" is a dashboard. "You've been firefighting all week — your Pitta is running hot. Let's look at what you can delegate before the weekend" is Sakhi.

---

## Priority 3: App Store Ship

**Status**: Mobile app scaffolded (Expo), not feature-complete
**Effort**: ~2-4 weeks
**Depends on**: Priorities 1-2 (ship with differentiated experience)

### What

Get Sakhi into the iOS App Store with a focused, polished experience: onboarding, Gmail connect, email digest, Ayurvedic conversation, voice input.

### Why Third

- Nothing matters until users can use it
- But shipping *before* the engine is great means a mediocre first impression and poor retention
- Priorities 1-2 make the shipped product worth talking about
- App Store review takes time — submit early, iterate during review

### Scope

- Mobile onboarding flow (prakriti assessment, Gmail OAuth, permissions)
- Core screens: conversation, Me page (digest + wellness), settings
- Voice input (already built for web, port to mobile)
- Push notifications (digest ready, proactive insights)
- App Store assets (screenshots, description, privacy policy)
- TestFlight beta → App Store submission

### Ship Criteria

- User can: connect Gmail, see digest, have Ayurvedic conversation, use voice
- Performance: <2s load, smooth animations
- Privacy: clear data handling disclosure for App Store review
- Stability: no crashes in core flows

---

## Priority 4: Share to Sakhi

**Status**: Not started
**Effort**: ~3-5 days
**Depends on**: Priority 3 (needs mobile app in App Store)

### What

iOS Share Extension + Android Share Target. User shares content from any app (WhatsApp, Telegram, SMS, any browser) to Sakhi. Sakhi extracts commitments, deadlines, action items, and stores them in the same system as email commitments.

### Why Fourth

- Bridges the messaging gap for channels without APIs (WhatsApp, Telegram, SMS, Signal)
- Zero platform risk — Share Extensions are a standard, approved iOS/Android feature
- Builds the habit: "Sakhi is where my commitments live" — regardless of which app the commitment came from
- Each share teaches Sakhi about the user's communication patterns and relationships
- This is the bridge to Sakhi messaging (Priority 5 in unified messaging strategy)

### Scope

- iOS Share Extension (receives text/URLs/images from any app)
- Android Share Target (equivalent)
- Extraction pipeline: parse shared content → identify commitments, deadlines, senders
- Store in existing `email_commitments` table (generalized to `commitments` with channel field)
- UI: shared items appear in Me page alongside email commitments

### Key Insight

Every time a user shares a WhatsApp message to Sakhi and gets a tracked commitment back, they're training themselves that "Sakhi is where my commitments live." This organic habit is what makes Sakhi messaging (long-term) feel like a natural next step, not a forced migration.

---

## Priority 5: API Connects — Outlook, Slack, Teams

**Status**: Not started (Gmail adapter done, pattern established)
**Effort**: ~1 week per platform
**Depends on**: Priority 1 (preferences make multi-channel triage personalized)

### What

OAuth adapters for work messaging platforms with proper APIs: Outlook (Microsoft Graph), Slack, MS Teams (shares MS Graph auth with Outlook).

### Why Fifth

- Gmail + Outlook + Slack + Teams covers ~90% of knowledge worker messaging
- Pattern is established from Gmail — each new adapter follows the same interface
- Contact preferences (Priority 1) make cross-channel triage actually useful ("Sarah emailed AND Slacked you — she's critical priority, surface both")
- Enterprise value: admin-consented OAuth means IT deploys once, covers the whole org

### Scope

Per platform:
- OAuth adapter (connect, refresh tokens, disconnect)
- Sync pipeline (fetch messages/events, normalize to common model)
- Triage integration (same LLM prompt, channel badge in digest)
- Preference system integration (same contact, different channel)

### Sequencing

1. **Outlook** (MS Graph) — biggest unlock for corporate users
2. **Slack** — async messaging, high volume, high noise
3. **Teams** — shares MS Graph auth with Outlook, incremental effort

---

## Priority 6: Desktop Agent — Full B2C Coverage

**Status**: Partially built (browser automation, screen vision exist)
**Effort**: ~2-3 weeks
**Depends on**: Priorities 1-5 (APIs handle what they can, agent fills gaps)

### What

Desktop agent reads web-based messaging apps (WhatsApp Web, Telegram Web/Desktop, Signal Desktop, iMessage on macOS, Google Messages Web) via screen capture + vision. Gives full "nothing urgent anywhere" confidence for B2C users.

### Why Sixth

- Solves the WhatsApp/Telegram/SMS gap that APIs cannot
- Personal computers have zero platform restrictions — no App Store gatekeepers, no corporate IT blocking
- Complements APIs: APIs are more reliable + 24/7, agent covers apps without APIs
- Every messaging app has a web/desktop version
- Desktop agent infrastructure already partially exists

### Scope

- Extend existing desktop agent to read messaging apps
- Vision pipeline: screenshot → OCR/vision model → extract messages → triage
- Per-app adapters: WhatsApp Web, Telegram Web, Signal Desktop, iMessage (macOS)
- Integration with existing triage system (same commitment extraction, same digest)
- Setup guide: "Open these apps in your browser, Sakhi will read them"

### Two-Track Strategy

| Track | Mechanism | Coverage | Reliability | Availability |
|-------|-----------|----------|-------------|-------------|
| API | OAuth per platform | Gmail, Outlook, Slack, Teams | High (polling/webhooks) | 24/7 |
| Desktop Agent | Screen capture + vision | WhatsApp, Telegram, SMS, Signal, any app | Medium (requires desktop on) | When desktop is running |

Together: comprehensive coverage.

---

## Priority 7: Android

**Status**: Expo scaffolded (cross-platform), not built out
**Effort**: ~2-3 weeks (mostly testing + Play Store submission)
**Depends on**: Priority 3 (iOS app proven and stable)

### What

Ship Sakhi on Android via the same Expo/React Native codebase. Plus Android-specific features: home screen widgets, notification listener (optional), Share Target.

### Why Last

- iOS first narrows the testing surface and speeds up iteration
- Expo makes the port mostly automatic — but testing, Play Store review, and Android-specific features still take time
- Android opens up notification listener as a bonus (reads all app notifications — Android-only capability)
- Play Store review is generally faster than App Store

### Scope

- Build and test on Android devices/emulators
- Android-specific UI adjustments (navigation, back button, status bar)
- Android Share Target (Priority 4 equivalent)
- Play Store assets and submission
- **Bonus**: Android `NotificationListenerService` — reads notification previews from all apps (WhatsApp, SMS, Telegram) without per-app auth. Requires careful Play Store positioning.

### Android-Only Advantage

The notification listener gives Android users something iOS users can never have: passive reading of all messaging app notifications. If positioned correctly (wellness/productivity framing), this could be a significant Android differentiator.

---

## Timeline View

```
Month 1          Month 2          Month 3          Month 4+
─────────────────────────────────────────────────────────────
[P1: Preferences]
    [P2: Ayurvedic Engine──────]
                  [P3: App Store Ship────]
                       [P4: Share──]
                                   [P5: API Connects────────]
                                        [P6: Desktop Agent──]
                                                  [P7: Android──]
```

Some of these run in parallel (P4 can start while P3 is in App Store review). The critical path is P1 → P2 → P3.

---

## Decision Log

| Decision | Rationale |
|----------|-----------|
| iOS before Android | Narrower surface, faster iteration, premium market |
| Engine before ship | First impression matters — ship differentiated, not generic |
| Share Extension before API connects | Zero platform risk, bridges the gap immediately |
| Desktop agent after APIs | APIs are more reliable, agent fills remaining gaps |
| Preferences before everything | Channel-agnostic foundation, highest ROI |

---

## Related Docs

| Doc | What |
|-----|------|
| [BUILD_PLAN.md](./BUILD_PLAN.md) | Full feature roadmap with status tracking |
| [unified-messaging-strategy.md](./features/unified-messaging-strategy.md) | Integration approach analysis and layered strategy |
| [email-intelligence.md](./features/email-intelligence.md) | Email V1 architecture (complete) |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture |
