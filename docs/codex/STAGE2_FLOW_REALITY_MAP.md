# Stage 2 Flow Reality Map

> Last updated: 2026-02-14  
> Purpose: Make current demo reality explicit and define the exact closure sequence to reach full production behavior.

## 1. Reality Map (Current)

| Flow | Path | Current State | What is Real Today | What is Still Simulated / Missing |
|---|---|---|---|---|
| Stage 2 task execution loop | `/experience/actions` | **Production-ready** | Real ask -> plan -> explicit approval -> execution states -> completion/failure surface | Coverage still limited to planner/tool path quality and tool reliability per task type |
| Ayurvedic check-in loop | `/experience/checkin` | **Production-ready** | Real check-in, causal explanation, protocol options, follow-up + outcome logging | Broader protocol catalog and richer personalization still expanding |
| Vision loop demo | `/demo/vision` | **Simulated** | Demo API hook and status labeling | Browser actions and screen loop are simulated in demo path |
| Search demo (quick/research/recurring) | `/demo/search` | **Simulated** | UI flow and narrative | Retrieval, ranking, and recurring execution are scripted for demo |
| Coordination demo | `/demo/coordination` | **Simulated** | UI story and sequence | Real multi-party negotiation and calendar transactions not wired in this path |
| Restaurant customer demo | `/demo/dine` | **Simulated** | Consent narrative and payload examples | Real consent packet exchange with business systems not active in demo flow |
| Restaurant dashboard demo | `/demo/restaurant` | **Simulated** | Business-side visualization | Real inbound mesh handoff and fulfillment integration not active |
| Reveal demo | `/demo/reveal` | **Partially real** | Reflection endpoint can call real reasoning path | Falls back to simulated content when service/dependencies fail |
| Reflect demo | `/demo/reflect` | **Simulated** | Pattern storytelling UX | Entire causal analysis in page is scripted data |
| Mission demo | `/demo/mission` | **Partially real** | Mission endpoint and plan object creation are live | Uses demo profile defaults and limited execution linkage |

## 2. Exact Closure Sequence

## Phase A: Lock Stage 2 Core Reliability
1. Stabilize planner storage and route telemetry for `/api/v1/agent/task*`.
2. Keep approval mandatory by default (`pending_approval`) for all high-impact actions.
3. Expand integration tests around create/approve/cancel/active-task route chain.
4. Add retries and clearer failure reasons at step level for user-visible recovery.

## Phase B: Convert Demo Search to Real Loop
1. Repoint `/demo/search` quick mode to Stage 2 task loop with real planning.
2. Keep deep research as async task plan with explicit status polling.
3. Replace static recurring simulation with real scheduled job scaffolding and logs.
4. Preserve demo UX but remove scripted result payloads from primary path.

## Phase C: Convert Vision and Browser Execution
1. Replace `/demo/vision?mode=simulated` default with real browser execution mode.
2. Keep simulated fallback only behind explicit demo toggle.
3. Add approval checkpoints before click/submit actions with side effects.
4. Add run transcript and action audit for trust.

## Phase D: Convert Coordination and Business Handoff
1. Wire `/demo/coordination` to real availability + conflict resolver APIs.
2. Add confirm-and-create calendar transaction with rollback on failure.
3. Introduce real consent packet for `/demo/dine` and `/demo/restaurant`.
4. Add user-facing audit: what was shared, why, and with whom.

## Phase E: Connect Mission to Executed Behavior
1. Link mission steps to completed Stage 2 actions and outcomes.
2. Replace static mission progress with execution-derived progress updates.
3. Add weekly adaptation from actual outcomes and task completion quality.
4. Add KPI readout: completion, time saved, approval acceptance, repeat usage.

## 3. Stage 2 KPI Instrumentation Spine

1. `task_plan_created`
2. `task_plan_approved`
3. `task_plan_cancelled`
4. `task_plan_failed`
5. `task_plan_completed`

These events should be queryable per user and per flow entry point (experience vs demo).
