# Codex Execution Plan: Ayurvedic/Yogic Companion First

> Last updated: 2026-02-11  
> Status: Approved sequencing, execution-ready  
> Working mode: Ship in stages, prove value fast, expand only after validated gates

## 1. Vision and Business Positioning

### Product vision
Sakhi is a personal life operating system that removes friction in two domains:
1. Internal friction: overwhelm, scattered energy, emotional load, low clarity.
2. External friction: search fatigue, coordination fatigue, repeated explanation, execution overhead.

### Core promise
Users should feel: "I feel better now, and I can act better now."

### Positioning
Sakhi is not a journaling app and not a generic chatbot.  
Sakhi is an Ayurvedic/Yogic companion that turns personal state into immediate action, then expands into real-world execution and coordination.

### Strategic wedge
Lead with immediate embodied value:
1. "How I feel right now."
2. "Why this may be happening for me."
3. "What I should do in the next 2-10 minutes."
4. "Did it help?"

This creates retention before introducing broader "Sakhi mesh" behaviors.

## 2. Product Thesis and Non-Negotiables

### Thesis
Reflection-only value arrives too late for most users. Immediate regulation + immediate action must come first.

### Non-negotiables
1. No hidden simulation in production paths.
2. Every core interaction produces immediate value within the same session.
3. Explanations include traceable evidence or uncertainty language.
4. High-impact actions always remain user-approved.

## 3. North Star and Success Metrics

### North Star
Percent of active users who complete at least one "state -> action -> outcome" loop per week.

### Stage-level KPI spine
1. Time-to-first-value (TTFV).
2. Session-to-action conversion.
3. Same-day self-reported benefit.
4. Week-1 retention.
5. Task completion rate for outer-friction loops.

## 4. Staged Roadmap

## Stage 0: Foundation and Truth Layer (Week 1)

### Goal
Remove technical ambiguity so all demo and product flows clearly indicate real vs simulated.

### Build
1. Wire missing web demo API paths for `/api/demo/*` and remove silent dependency confusion.
2. Add explicit state badges in demo/product experiences: `live`, `partially real`, `simulated`.
3. Fix voice turn payload contract (`text` alignment).
4. Fix health sync payload contract (`source` required by backend).
5. Fix identity consistency (remove hardcoded demo person paths from real user surfaces).
6. Add baseline instrumentation events for funnel tracking.

### Known blockers to close in this stage
1. `/demo/vision` and `/demo/reveal` call `/api/demo/...` from web, but web proxy routes are missing.
2. Mobile voice sends `message`, while turn API expects `text`.
3. Mobile health sync omits `source`, while health API requires it.
4. Dev fallback person resolution defaults to `a` when user identity is missing.

### Exit gate
1. No silent fallbacks.
2. All critical flows declare real/simulated status in UI.
3. Contracts pass smoke tests end-to-end.

## Stage 1: Ayurvedic/Yogic Companion First (Weeks 2-5)

### Goal
Deliver immediate in-session value and prove the core wedge.

### User loop to ship
1. User reports present state.
2. Sakhi explains likely causes with personal context.
3. Sakhi gives 2/5/10-minute options.
4. User executes one action.
5. Sakhi follows up and records outcome.

### Workstream A: Experience
1. Fast check-in entry flow with symptom + energy + body cues + optional free text.
2. Context card that is short, actionable, and non-lecture.
3. Protocol cards with duration and expected effect.
4. Follow-up prompt after 30-180 minutes.

### Workstream B: Intelligence
1. Personal explanation model with dosha-context framing.
2. Pattern evidence from recent behavior/state history.
3. "Last time this helped" retrieval where available.
4. Confidence labeling and uncertainty handling.

### Workstream C: Action layer
1. Breath protocol suggestions.
2. Yoga/movement micro-protocol suggestions.
3. Food/timing adjustments for same day.
4. Reminder and check-back scheduling.
5. "Helped / Not helped" feedback capture.

### Workstream D: Trust and safety
1. Transparent reasoning snippets.
2. Safe language boundaries for non-medical support.
3. Escalation prompts for severe or persistent distress.

### Workstream E: Measurement
1. Capture funnel event `checkin_started`.
2. Capture funnel event `insight_shown`.
3. Capture funnel event `protocol_selected`.
4. Capture funnel event `protocol_completed`.
5. Capture funnel event `followup_submitted`.
6. Capture funnel event `benefit_reported`.

### Stage 1 KPIs
1. TTFV under 2 minutes.
2. Protocol selection rate above 40%.
3. Self-reported same-day benefit above 35%.
4. Week-1 retention lift vs current baseline.

### Exit gate
Companion loop demonstrates immediate value without requiring long journaling history.

## Stage 2: Immediate Outer Value (Weeks 6-7)

### Goal
Prove Sakhi can reduce external execution friction in one high-frequency flow.

### Build
1. One real action loop: ask -> Sakhi researches/filters -> user approves -> done.
2. Clear approval boundary before high-impact actions.
3. Explicit execution states and failure recovery.

### KPIs
1. Completed-action rate.
2. Time saved per task.
3. Approval accept/reject ratio.

### Exit gate
At least one external loop is reliable and trusted.

## Stage 3: Personal Coordination (Weeks 8-9)

### Goal
Replace scripted coordination with real multi-party scheduling behavior.

### Build
1. Availability negotiation.
2. Conflict resolution options.
3. Confirm-and-create calendar flow.
4. Explanation of why recommended slot was selected.

### KPIs
1. Coordination completion rate.
2. Reduced back-and-forth count.
3. User trust score after coordination.

### Exit gate
Personal coordination is real and repeatable.

## Stage 4: Business Handoff (Weeks 10-11)

### Goal
Ship one real consent-based context exchange with a business workflow.

### Build
1. User consent packet definition.
2. Share-minimum-necessary context.
3. Business-side response in structured form.
4. User-side "what was shared and why" audit view.

### KPIs
1. Consent completion rate.
2. Partner utility score.
3. User satisfaction with personalization quality.

### Exit gate
One production-grade user-to-business handoff works end-to-end.

## Stage 5: Mission Spine (Weeks 12-13)

### Goal
Connect long-term mission planning to real executed behavior.

### Build
1. Mission plans tied to completed actions and outcomes.
2. Weekly adaptation driven by actual results.
3. Better checkpoint and progress quality.

### KPIs
1. Weekly mission adherence.
2. Mission usefulness score.
3. Progress rate to milestone.

### Exit gate
Missions act as a retention spine, not a standalone planning artifact.

## Stage 6: Hardening and Scale (Week 14+)

### Goal
Make the system robust for sustained production usage.

### Build
1. Replace in-memory pending critical state with durable store.
2. Reliability SLOs and error-budget monitoring.
3. Retry strategy + idempotent execution for high-risk operations.
4. Operational playbooks and auditability.

### Exit gate
Stable release cadence and production reliability targets are met.

## 5. Execution Model with Codex

### Cadence
1. Weekly sprint planning.
2. Daily build + validation loop.
3. End-of-week demo and gate decision.

### Definition of done
1. End-to-end behavior works in real path.
2. Tests cover critical paths and failure modes.
3. Instrumentation events are emitted and queryable.
4. UI communicates status, confidence, and failures clearly.
5. No hidden simulated dependency in production mode.

### Working protocol
1. Every ticket has acceptance criteria and a metric target.
2. If a ticket cannot show user value or reliability gain, defer it.
3. Sequence is stage-gated: no forward jump without passing gate.

## 6. Initial Sprint Backlog Seed

## Sprint A (Stage 0)
1. Implement web proxy routes for `/api/demo/run/vision` and `/api/demo/run/reflection`.
2. Add live/partial/simulated labels on demo pages.
3. Align mobile voice request body to turn API schema (`text`).
4. Align mobile health sync body to include `source`.
5. Remove hardcoded demo IDs from user-facing runtime paths.
6. Add smoke tests for demo and mobile contract endpoints.

## Sprint B (Stage 1)
1. Build state check-in API contract and UI entry.
2. Build "why now" explanation response object with confidence.
3. Build protocol recommendation object (2/5/10 minute).
4. Build follow-up scheduler and outcome capture.
5. Instrument full Stage 1 funnel and dashboard.
6. Run pilot and evaluate Stage 1 KPI gates.

## 7. Decisions Locked for This Plan

1. Ayurvedic/Yogic companion is first productized wedge.
2. Journaling/reflection-only flow is not the lead value proposition.
3. Full Sakhi mesh vision remains the direction, but release is stage-gated.
