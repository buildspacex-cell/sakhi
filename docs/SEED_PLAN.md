# Sakhi Seed Plan
## Technical + External Implementation Roadmap

> Objective: Get to 20 paying users with retention data before seed close.
> The core bet to prove: continuity becomes a retained behaviour and users pay for it.

Last Updated: 2026-04-25

---

## The Hierarchy of Problems

| Priority | Problem | Why It's Critical |
|----------|---------|-------------------|
| 1 | Value is invisible on day 1 | Users leave before the aha moment |
| 2 | No paywall | Can't prove willingness to pay |
| 3 | Multi-model routing claimed, not built | Investor credibility gap |
| 4 | Deep Dive reports, doesn't guide | Continuity feels passive not useful |
| 5 | Cross-thread linking unreliable | Core differentiator claim is weak |
| 6 | No beta users / retention data | Seed pitch has no proof |

---

## Phase 1 — Engineer the Aha Moment (Week 1–2)

**Goal:** A returning user knows within 5 seconds that Sakhi is different from ChatGPT.

### Technical

**Return-visit hook (highest priority build)**

When a user opens the app and has prior sessions, replace the blank input with a continuation card:

```
"Last time you were working through [topic].
You were [decision state] but hadn't resolved [unresolved question].
Continue →"
```

Backend:
- New endpoint `GET /v2/continuation-prompt` — takes `person_id`, returns `{ topic, decision_state, unresolved_question, last_session_ts, thread_key }`
- Logic: load most recent thread with `deep_reflect_signal.reason = ready` OR `decision_state IN (questioning, leaning_yes, leaning_no)` AND `last_active > 4 hours ago`
- Extract unresolved question from continuity arc's `unresolved_entries` — pick the last entry with no decision resolution
- Cache result per person (5 min TTL) — this runs on every app open

Mobile + Web:
- On app open: call `/v2/continuation-prompt`
- If result exists: show continuation card above input (not replacing it — user can still start new)
- Tap card → pre-fills session context, routes to that thread
- If no result (first session or no continuity signal): show normal blank input

Lower Deep Dive threshold from 8 → 4 messages. The current threshold is too conservative.

**Onboarding: the first session must plant the seed**

At end of first session (turn 4+), show a subtle message:
> "I'm tracking where this thinking goes. Come back tomorrow and I'll show you what I've noticed."

This sets expectation that the value compounds — users who know to come back will come back.

---

## Phase 2 — Paywall (Week 2–3)

**Goal:** First paying user before seed close. Even 1 counts more than projections.

### Technical

Stripe integration:
- `POST /billing/create-checkout` → Stripe Checkout session (Pro $20/mo or $180/yr)
- `POST /billing/webhook` → handle `checkout.session.completed`, `customer.subscription.deleted`
- `auth_users` table: add `subscription_status` (free | pro | cancelled), `stripe_customer_id`
- Middleware check on gated routes (Deep Dive beyond 1/month on free, continuity window > 7 days on free)

Free tier limits (enforce in API, show in UI):
- 7-day continuity window (Pro: 90 days)
- 1 Deep Dive / month (Pro: unlimited)
- 1 linked thread in Whole Story (Pro: up to 5)

In-app upgrade flow:
- When free user hits a limit: modal with "You've used your Deep Dive for this month" + single CTA → Stripe Checkout
- No dark patterns — one clear screen, price visible, cancel anytime

### External

- Set up Stripe account, test mode first, live before first beta invite
- Pricing page at `/pricing` (single page, 2 tiers, clear comparison)
- No trial period initially — $20/mo is low enough that asking for a card on day 1 is a valid signal of intent

---

## Phase 3 — Multi-Model Routing or Cut It (Week 2–3, parallel)

**Decision to make before proceeding:**

| Option | What it takes | Risk |
|--------|--------------|------|
| Build it | ~3 days: LLMRouter live with GPT-4o + Claude Sonnet, model selector in UI, routing policy | Scope creep if done poorly |
| Cut from pitch | 30 min: update one-pager + deck language | Lose a differentiator claim |
| Reframe | Keep "Sakhi routes automatically" — remove user choice language, don't show model selector | Honest, still differentiating |

**Recommendation: Reframe.** "Sakhi routes to the best model automatically" is true (you can build the routing logic without a user-facing picker). Remove "power users can choose the model" from the one-pager. Add Claude as a second provider to LLMRouter — this is 1 day of backend work. Now the claim is honest and demonstrable.

### Technical (if reframe path)

- Add Anthropic provider to `sakhi/libs/llm_router/`
- Routing policy: use Claude for reflective/synthesis tasks (Deep Dive), GPT-4o for conversational turns
- No UI change needed — routing is invisible
- Update one-pager language: remove user model choice, keep "routes automatically"

---

## Phase 4 — Deep Dive Becomes a Thinking Partner (Week 3–4)

**Goal:** Deep Dive produces the next question, not just a summary of the past.

### Technical

Change the reflection result schema to include `next_question`:

```python
# reflection result currently returns:
{ "origin_story": "...", "key_pivots": [...], "current_stage": "..." }

# add:
{ ..., "next_question": "You've been circling X for 3 weeks. The unresolved question is: [specific unresolved entry as a question]." }
```

Backend changes:
- In `reflection.py`: after building the synthesis, extract the most recent `unresolved_entry` from the arc
- Run a single LLM call: "Given this decision arc, what is the one question this person has not yet answered? Return one sentence, framed as a direct question to the person."
- Store as `next_question` in reflection result
- Fallback: if no unresolved entry, omit `next_question`

Mobile + Web:
- After Whole Story renders, show `next_question` as a highlighted card with "Work through this now →" CTA
- Tapping it pre-fills the conversation input with the question as context
- This is the moment continuity becomes active, not passive

---

## Phase 5 — Cross-Thread Linking Surface (Week 4–5)

**Goal:** Make the across-thread connection visible to the user at least once in their first week.

This is the moment that proves Sakhi is not just within-session memory.

### Technical

**Cross-thread suggestion card** (new UI element):
- After any turn where `whole_story_signal.correlation_score > 0.6`, show a subtle card below the reply:
  > "This connects to something you were working through last week: [linked topic]. Want me to bring that context in?"
- User taps yes → linked thread context added to next turn
- User taps dismiss → logged, don't show again for that link

Backend:
- `whole_story_signal` already computed in `turn_v2.py` — expose it in the turn response if `correlation_score > 0.6` and `linked_topics` non-empty
- Frontend reads `continuity.whole_story_signal` from turn response and renders the card
- Persist user's dismiss action in `continuity_surface_policy.exclusions`

**Personal taxonomy visibility** (simple, high signal):
- In the profile/thread list screen: show the user's top 3 active topics (from `continuity_personal_taxonomy` ordered by `entry_count`)
- Tap a topic → see all threads tagged to it
- This makes the invisible visible: "Sakhi knows you have 7 conversations about fundraising"

---

## Phase 6 — 50 Beta Users (Weeks 2–6, parallel with above)

**Goal:** Find 10 users who come back consistently. Their story is your seed narrative.

### External

**Who to recruit:**
- Founders currently in fundraising (6-12 month process, high volume of AI-assisted thinking)
- Operators running a hiring search or product strategy cycle
- Specifically: people who already use ChatGPT/Claude heavily and are frustrated by context loss

**Where to find them:**
- Your network first — 10 direct asks from the founder's personal network
- YC Slack / Hacker News "Ask HN: who uses AI for decision-making"
- Twitter/X: post a specific use case ("I built something for founders who use ChatGPT to think through fundraising but lose context every session") — not a product launch, a specific problem statement
- Lenny's Newsletter community, First Round Review community

**How to onboard them:**
- Personal onboarding call (20 min) for first 20 users — watch them use it, see where they get stuck
- Single use case focus: "Use Sakhi for one ongoing decision you're working through right now"
- Check in at day 3, day 7, day 14

**What to measure:**
- D3 retention (came back at least once)
- D7 retention
- Did they hit Deep Dive at least once?
- Did they see the return-visit hook?
- NPS at day 14: "How disappointed would you be if Sakhi went away?"

**Finding the story:**
- At day 14, call every user who came back 3+ times
- Ask: "What made you come back?" and "What would you tell a friend this does that ChatGPT doesn't?"
- One real answer to that second question is your pitch opening line

---

## Phase 7 — Seed Pitch Refinement (Week 5–6)

**Goal:** Pitch deck that leads with proof, not thesis.

### External

**One-pager updates:**
- Remove: "power users can choose the model" → replace with "routes automatically to the right model"
- Add: return-visit hook screenshot as the product moment
- Replace the simulation demo with a real user quote (once you have beta users)
- The "10-second product moment": screenshot of the continuation card on return visit — that's the image that does the explaining

**Deck updates:**
- Slide 1: Problem — "Every AI conversation resets. Your thinking doesn't."
- Slide 4 (Traction): Number of beta users, D7 retention %, number of paying users — even if small
- Slide 5 (Product): Return-visit hook screenshot. Deep Dive → next question. Not the simulation.
- Remove Collective tier from the near-term pitch — it's Year 2 and distracts from the core bet
- Sharpen the ask: $1.25M to get to 500 retained paying users who use Sakhi for active decisions

**Investor targeting:**
- Lead with consumer AI investors who understand retention-first businesses (not growth-first)
- The story to tell: "We've found that users with an active decision return at [X]% D7. We need capital to find more of those users."
- Avoid pitching to investors who'll push for B2B pivot before you've proven B2C — it's the wrong path at this stage

---

## Success Metrics by Phase

| Phase | Metric | Target |
|-------|--------|--------|
| Phase 1 | D3 retention with return-visit hook live | > 40% |
| Phase 2 | First paying user | Week 3 |
| Phase 3 | Multi-model claim honest + demonstrable | Before any investor meeting |
| Phase 4 | % of Deep Dives that result in continued conversation | > 50% |
| Phase 5 | Users who see a cross-thread link and engage | > 30% of active users |
| Phase 6 | Beta users with > 3 return visits in 2 weeks | 10 of 50 |
| Phase 7 | Seed close | 8 weeks from now |

---

## The Single Most Important Thing

The return-visit hook in Phase 1 is the only thing that matters in week 1.

Everything else — paywall, routing, beta users, deck — depends on having a product that demonstrates its value before the user leaves. If someone comes back after 2 days and the app shows them exactly where their thinking left off and what they haven't resolved yet, you have a product. If it shows them a blank input box, you have a chat interface.

Build that first. Everything else follows.

---

## What Not to Do

- Don't add new AI features (voice, agents, email) before retention is proven
- Don't launch publicly before you have 10 users who came back 3+ times
- Don't pitch the Collective tier until B2C is working
- Don't build the Ayurveda layer back into the main surface
- Don't optimise for DAU before you've optimised for "did the product change how this person thinks"
