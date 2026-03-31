# Codebase Context (Working Baseline)

> Last audited: 2026-03-25  
> Source of truth refresh command: `./scripts/context-audit.sh`

## Purpose

This document is the operational context baseline for coding tasks.  
It captures what is actually in code right now (not roadmap intent), where
critical flows live, and what is verified broken vs working.

Use this first before substantial code edits.

## How To Refresh

1. Run:

```bash
./scripts/context-audit.sh
```

2. If counts or health signals change, update this file and related docs:
   - `docs/ARCHITECTURE.md`
   - `docs/WHAT_WE_BUILT.md`
   - `docs/TEST_STATUS.md`
   - `CHANGELOG.md` (`[Unreleased]`)

## Current Snapshot (2026-03-25)

### Repository Shape

| Metric | Value |
|---|---:|
| Tracked files | 1495 |
| Python files | 866 |
| TypeScript files (`.ts`, `.tsx`) | 425 |
| API route modules (`sakhi/apps/api/routes`, excluding `__init__`/`.bak`) | 81 |
| API service modules (`sakhi/apps/api/services`, excluding `__init__`) | 234 |
| Worker modules (`sakhi/apps/worker`, excluding `__init__`) | 114 |
| Worker task modules (`sakhi/apps/worker/tasks`, excluding `__init__`, `_stubs.py`) | 86 |
| Engine modules (`sakhi/apps/engine`, excluding `__init__`) | 34 |
| Web pages (`apps/web/app/**/page.tsx`) | 83 |
| Web API routes (`apps/web/app/api/**/route.ts`) | 119 |
| Mobile screens (`apps/mobile/app/**/*.tsx`) | 15 |
| Kala source modules | 49 |
| Kala test functions | 552 |

### API Wiring Reality Check

| Signal | Value |
|---|---:|
| `include_router(...)` calls in `sakhi/apps/api/main.py` | 99 |
| Duplicate `focus_path_router` imports | 2 |
| Duplicate `micro_momentum_router` imports | 2 |
| Duplicate `app.include_router(person_router.router)` | 2 |
| Duplicate `app.include_router(micro_momentum_router)` | 2 |

## Critical Runtime Paths

### MVP Narrative Demo

- Protected web UI: `apps/web/app/mvp/page.tsx`
- Public GSAP cinematic story: `apps/web/app/(marketing)/story/page.tsx`
- Public aligned pitch deck: `apps/web/app/pitch/page.tsx`
- Preserved scroll narrative: `apps/web/app/(marketing)/story-scroll/page.tsx`
- Password gate: `apps/web/app/mvp/unlock/page.tsx`, `apps/web/middleware.ts`
- Narrative data: `packages/narrative/mvp/roadmap.ts`
- Content package: `packages/narrative/package.json` (`@sakhi/narrative`)
- Web components: `apps/web/components/mvp/Slide.tsx`, `apps/web/components/mvp/LoopDiagram.tsx`, `apps/web/components/mvp/PhaseGrid.tsx`
- Web story components: `apps/web/components/story/*`
- Web pitch components: `apps/web/components/pitch/*`
- GSAP story shell: `apps/web/components/story/StoryContainer.tsx`, `apps/web/components/story/useStoryTimeline.ts`
- Demo home handoff page: `apps/demo/app/page.tsx`
- Parked demo cinematic components: `apps/demo/components/cinematic/*`

### Investor Simulation (Web)

- UI: `apps/web/app/lab/simulation/client.tsx`
- Page entry: `apps/web/app/lab/simulation/page.tsx`
- Web API proxy: `apps/web/app/api/demo/simulation/add-journal/route.ts`
- Backend route: `sakhi/apps/api/routes/demo.py` → `POST /demo/simulation/add-journal`
- Service: `sakhi/apps/api/services/demo/simulation_profile_updater.py`

### Add-Journal Flow (Current Behavior)

1. UI posts `persona_id`, `content`, `time_of_day`.
2. Backend appends a new journal day to simulation persona.
3. Journal is processed through `/v2/turn` (production path).
4. Daily worker set runs (15 workers from shared registry:
   `sakhi/apps/worker/simulation_worker_registry.py`).
5. Snapshot is captured from DB (`personal_model`, episodic/pattern/theme tables).
6. JSON profile in `apps/web/public/simulation/<persona>.json` is rewritten.
7. Replay uses updated entries immediately.

### Simulation Worker Cadence (Current)

- Default simulation cadence is now daily (`daily_worker_interval=1`) in:
  - `sakhi/tests/longitudinal/simulation_harness.py`
  - `sakhi/tests/longitudinal/export_real_simulation.py`
  - `scripts/run_demo_personas.py`
- Inspect production vs simulation frequency map with:
  - `python -m sakhi.tests.longitudinal.export_real_simulation --list-worker-frequency`
  - `python scripts/run_demo_personas.py --list-worker-frequency`

## Simulation Data Health (Verified)

Source: `./scripts/context-audit.sh` on 2026-03-25.

| File | Days | Entries | Coherence | Alignment | Identity | Themes | Patterns | Worker failures |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `vidhya.json` | 117 | 68 | 118 | 118 | 118 | 104 | 0 | none |
| `diya.json` | 30 | 30 | 31 | 31 | 31 | 25 | 18 | none |
| `bigd.json` | 30 | 30 | 31 | 31 | 31 | 25 | 18 | none |
| `anxious_achiever.json` | 1 | 2 | 2 | 2 | 2 | 1 | 0 | `weekly.weekly_rhythm_rollup: relation "rhythm_daily_curve" does not exist` |
| `hormonal_harmony.json` | 30 | 56 | 0 | 0 | 0 | 0 | 0 | none |
| `stuck_creative.json` | 70 | 122 | 0 | 0 | 0 | 0 | 0 | none |

Current read:
- Primary investor personas (`vidhya`, `diya`, `bigd`) have healthy deep-state snapshots.
- `anxious_achiever` still shows a deferred rhythm rollup schema gap from legacy snapshot runs.
- `hormonal_harmony` and `stuck_creative` remain legacy/low-fidelity for deep-state outputs.

## Test Reality (2026-03-25 Context Audit)

### Harness Signals

- `make quick-test` now resolves correctly:
  - Context audit validates the Makefile target by checking all referenced test files exist.
  - Current signal: `quick_test_target=present (5 files)`.

### Audit Counts

- `sakhi/tests` path-prefix count: `71`
- `test_*.py` pattern count under `sakhi/tests`: `74`
- Integration test files: `9`
- Unit test files: `59`

## Observability Signals (2026-03-25 Context Audit)

- `metrics_endpoint=present`
- `health_readiness=present`
- `request_telemetry=present`
- `external_alerting_sink=present`

## Quality Gates For Future Changes

### If touching simulation/demo flow

Run:

```bash
poetry run pytest sakhi/tests/unit/services/test_simulation_profile_updater.py -v --tb=short
poetry run pytest sakhi/tests/unit/workers/test_pattern_workers.py -q
poetry run pytest sakhi/tests/unit/workers/test_state_workers.py -q
```

### If touching governance kernel

Run:

```bash
poetry run pytest kala/tests -q
```

### If touching API route wiring

Run:

```bash
python -c "from sakhi.apps.api.main import app; print('API imports OK')"
rg -n "include_router\\(" sakhi/apps/api/main.py
```

### Before release-facing commits

Run:

```bash
./scripts/context-audit.sh
make check-env
make ready-to-commit
```

If `make ready-to-commit` fails, use `./scripts/context-audit.sh` output to identify whether the failure is in the quick-test files themselves or another verification stage.
