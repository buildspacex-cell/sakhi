# Sakhi Complete Vision Master Plan (Codex)

> Last updated: 2026-02-11  
> Scope: End-to-end execution plan for the full Sakhi vision, staged and test-gated  
> Companion doc: `docs/codex/AYURVEDIC_FIRST_EXECUTION_PLAN.md`

## 1. Why CLAUDE.md Build Instructions Help

Yes, they help materially. They provide:
1. A strict verification cadence: `make verify` before commits, `make pre-deploy` before major releases.
2. A single commit readiness command: `make ready-to-commit`.
3. Required testing expectations by change type (unit + integration for larger modules).
4. A clear docs-update policy (`docs/BUILD_PLAN.md`, feature docs, architecture docs).
5. A repeatable build/test/deploy workflow aligned with Railway/Vercel auto-deploy behavior.

This reduces ambiguity and gives us enforceable quality gates for staged rollout.

## 2. Program Goal and Operating Principle

### Goal
Build the complete Sakhi vision as a reliable product:
1. Immediate inner value (Ayurvedic/Yogic companion).
2. Immediate outer value (task execution).
3. Real coordination (people and businesses).
4. Long-term adaptation (missions and memory-driven personalization).

### Operating principle
No stage advances until:
1. Functional acceptance criteria pass.
2. Test matrix for that stage passes.
3. Instrumentation confirms user-value signals.

## 3. Stage-by-Stage Delivery Plan

## Stage 0: Foundation and Truth Layer (Week 1)

### Objective
Eliminate hidden simulation and contract drift.

### Epics
1. Demo API wiring in web (`/api/demo/*` proxy coverage).
2. Contract alignment (voice and health sync payloads).
3. Identity alignment (remove demo-only hardcoded runtime paths in real flows).
4. Visibility (live/partial/simulated badges).
5. Baseline telemetry.

### Execution order
1. Implement missing web proxy routes for demo endpoints.
2. Add runtime badges in demo UI.
3. Fix mobile voice payload contract (`text`).
4. Fix mobile health payload contract (`source`).
5. Remove hardcoded demo IDs in real user runtime paths.
6. Add smoke tests for these contracts and UI states.

### Exit criteria
1. No silent fallback behavior in production mode.
2. Demo path truth labels are visible.
3. Voice and health sync contracts pass integration tests.

## Stage 1: Ayurvedic/Yogic Companion First (Weeks 2-5)

### Objective
Deliver immediate in-session value before long-history benefits.

### Epics
1. Check-in intake flow (`symptom + energy + body cues + optional note`).
2. Causal explanation with evidence and confidence.
3. Action protocols (2/5/10 minute).
4. Follow-up loop (reminder + effect capture).
5. Trust/safety language boundaries.
6. Funnel instrumentation and KPI dashboard.

### Execution order
1. Define and ship API contracts for check-in, explanation, protocol, follow-up.
2. Ship web and mobile check-in and protocol surfaces with parity in flow.
3. Add evidence snippets and uncertainty markers to responses.
4. Add follow-up scheduler and outcome capture.
5. Add KPI events and baseline analytics view.
6. Run pilot and evaluate gates.

### Exit criteria
1. Median TTFV under 2 minutes.
2. Session-to-protocol selection rate above threshold.
3. Same-day benefit reports above threshold.
4. Week-1 retention improves against baseline cohort.

## Stage 2: Immediate Outer Value (Weeks 6-7)

### Objective
Prove practical external friction removal in one high-frequency workflow.

### Reference
Flow reality map + closure sequence: `docs/codex/STAGE2_FLOW_REALITY_MAP.md`

### Epics
1. Ask -> propose -> approve -> execute loop.
2. Reliable execution states + recoverable errors.
3. Approval boundary for risky actions.

### Exit criteria
1. End-to-end completion rate meets target.
2. User-perceived time saved is positive.
3. Approval flow reliability is stable.

## Stage 3: Personal Coordination (Weeks 8-9)

### Objective
Ship real multi-party scheduling and conflict resolution.

### Epics
1. Availability resolution.
2. Conflict alternatives generation.
3. Confirm-and-create event flow.
4. Why-this-slot explanation.

### Exit criteria
1. Coordination completion rate target met.
2. Manual back-and-forth reduced.

## Stage 4: Business Handoff (Weeks 10-11)

### Objective
Ship one consent-based user-to-business context exchange flow.

### Epics
1. Consent packet and policy.
2. Minimum-necessary context sharing.
3. Business response integration.
4. User-visible context-sharing audit.

### Exit criteria
1. Consent completion target met.
2. Business flow utility validated.
3. User trust and satisfaction acceptable.

## Stage 5: Mission Spine (Weeks 12-13)

### Objective
Attach longitudinal mission planning to real behavior outcomes.

### Epics
1. Mission progression tied to executed actions.
2. Weekly adaptation from outcomes.
3. Better checkpoints and mission health tracking.

### Exit criteria
1. Mission adherence improves.
2. Mission usefulness score improves.

## Stage 6: Hardening and Scale (Week 14+)

### Objective
Production reliability and operational readiness.

### Epics
1. Replace in-memory pending critical state with durable infrastructure.
2. SLOs, alerting, retry/idempotency strategy.
3. Auditability and incident playbooks.

### Exit criteria
1. Reliability targets met.
2. Operational readiness accepted.

## 4. Detailed Test Matrix (Execution Contract)

## Global test gates for every stage
1. `make verify` (mandatory before each commit).
2. `make test` (mandatory before stage sign-off).
3. `make integration-test` (mandatory for service/route integration changes).
4. `cd apps/web && pnpm build` (mandatory for web-impacting stages).
5. `python -c "from sakhi.apps.api.main import app; print('API OK')"` (API import sanity).

## Stage-specific test matrix

| Stage | Unit Tests | Integration Tests | E2E/Smoke | Build Gates | Data/Contract Checks |
|---|---|---|---|---|---|
| Stage 0 | API proxy handlers, payload validators | Voice turn contract, health sync contract, demo API proxy pass-through | Demo pages show truthful mode badges; fallback behavior explicit | `make verify`, web build | Request/response schema assertions for `/v2/turn` and `/health/sync/{person_id}` |
| Stage 1 | Check-in parser, recommendation assembly, safety formatter | Check-in -> explanation -> protocol -> follow-up DB cycle | User loop smoke: start check-in to benefit report | `make verify`, `make test`, web build | Event emission checks (`checkin_started`, etc.) |
| Stage 2 | Task proposal and approval logic | Ask->approve->execute route/service chain | One outer workflow end-to-end | `make verify`, `make integration-test` | Approval-required path assertions |
| Stage 3 | Slot ranking/conflict resolver | Calendar/coordination transaction tests | Multi-party coordination smoke | `make verify`, `make pre-deploy` | Event creation and rollback checks |
| Stage 4 | Consent packet builder | Consent -> share -> business response loop | Business handoff smoke | `make verify`, `make pre-deploy` | Shared-field allowlist assertions |
| Stage 5 | Mission scoring and adaptation logic | Weekly review -> plan adaptation chain | Mission week lifecycle smoke | `make verify`, `make test` | Progress metric consistency checks |
| Stage 6 | Retry/idempotency modules | Durable pending-state and failure recovery | Chaos/failure simulation smoke | `make pre-deploy`, `make ready-to-commit` | Reliability SLO dashboard checks |

## Required test locations
1. Unit tests in `sakhi/tests/unit/`.
2. Route integration tests in `sakhi/tests/integration/routes/`.
3. Worker/service integration tests in `sakhi/tests/integration/workers/` and related service integration folders.
4. E2E flow tests in `sakhi/tests/e2e/` for critical loops.

## Evidence artifacts per stage
1. Command output summary for all required commands.
2. Test pass counts and failures (if any).
3. Stage KPI snapshot.
4. Known risk list and residual gaps.

## 5. Sprint Execution Model with Codex

### Weekly cadence
1. Day 1: lock sprint scope, dependencies, acceptance criteria.
2. Day 2-4: implementation + tests + instrumentation.
3. Day 5: run stage gate commands, prepare demo, decide ship/hold.

### Definition of ready (ticket)
1. Clear objective and user value statement.
2. Explicit acceptance criteria.
3. Test cases listed (unit + integration where needed).
4. Owner and dependency map defined.

### Definition of done (ticket)
1. Functional behavior implemented.
2. Required tests added and passing.
3. Docs updated (`docs/BUILD_PLAN.md` + relevant feature docs).
4. `make verify` passes.

## 6. Initial Backlog Decomposition (Actionable)

## Stage 0 ticket set (ordered)
1. `S0-T01` Add web proxy route: `POST /api/demo/run/vision`.
2. `S0-T02` Add web proxy route: `POST /api/demo/run/reflection`.
3. `S0-T03` Add demo mode badge component and wire to demo pages.
4. `S0-T04` Fix mobile voice turn request body contract to `text`.
5. `S0-T05` Fix mobile health sync request body to include `source`.
6. `S0-T06` Remove hardcoded runtime demo person IDs in production path usage.
7. `S0-T07` Add integration tests for S0 contracts.
8. `S0-T08` Add smoke checks for demo mode labeling.

## Stage 1 ticket set (ordered)
1. `S1-T01` Define check-in request/response schema and endpoint.
2. `S1-T02` Build explanation payload with evidence/confidence fields.
3. `S1-T03` Build 2/5/10 minute protocol recommendation endpoint.
4. `S1-T04` Add web check-in UI + protocol selection.
5. `S1-T05` Add mobile check-in UI parity with web flow logic.
6. `S1-T06` Implement follow-up scheduler and outcome capture endpoint.
7. `S1-T07` Implement funnel event instrumentation.
8. `S1-T08` Add integration and E2E tests for full Stage 1 loop.

## 7. Risk Register and Mitigation

1. Risk: Scope bleed into full vision too early.
2. Mitigation: strict stage gates and KPI threshold before expansion.

1. Risk: Demo/real mismatch erodes trust.
2. Mitigation: explicit mode labeling and no silent fallback in prod.

1. Risk: Contract drift across web/mobile/backend.
2. Mitigation: integration contract tests as required gate.

1. Risk: Reliability issues from in-memory pending state.
2. Mitigation: Stage 6 durability migration with failure simulation tests.

## 8. What We Execute Next

If approved, execution begins at Stage 0 with:
1. Ticket breakdown converted into working tasks.
2. Implementation in order.
3. Test gate run and evidence capture after each ticket group.
