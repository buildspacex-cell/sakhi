# Codebase Context (Working Baseline)

> Last audited: 2026-02-26  
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

## Current Snapshot (2026-02-26)

### Repository Shape

| Metric | Value |
|---|---:|
| Tracked files | 1321 |
| Python files | 815 |
| TypeScript files (`.ts`, `.tsx`) | 357 |
| API route modules (`sakhi/apps/api/routes`, excluding `__init__`/`.bak`) | 79 |
| API service modules (`sakhi/apps/api/services`, excluding `__init__`) | 221 |
| Worker modules (`sakhi/apps/worker`, excluding `__init__`) | 113 |
| Worker task modules (`sakhi/apps/worker/tasks`, excluding `__init__`, `_stubs.py`) | 86 |
| Engine modules (`sakhi/apps/engine`, excluding `__init__`) | 34 |
| Web pages (`apps/web/app/**/page.tsx`) | 76 |
| Web API routes (`apps/web/app/api/**/route.ts`) | 108 |
| Mobile screens (`apps/mobile/app/**/*.tsx`) | 30 |
| Kala source modules | 46 |
| Kala test functions | 547 |

### API Wiring Reality Check

| Signal | Value |
|---|---:|
| `include_router(...)` calls in `sakhi/apps/api/main.py` | 96 |
| Duplicate `focus_path_router` imports | 2 |
| Duplicate `micro_momentum_router` imports | 2 |
| Duplicate `app.include_router(person_router.router)` | 2 |
| Duplicate `app.include_router(micro_momentum_router)` | 2 |

## Critical Runtime Paths

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

### What Works

- For `vidhya`, `diya`, `bigd`, `anxious_achiever`:
  - Coherence/alignment/identity momentum states are present in snapshots.
  - Replay and append-journal pipeline are functional.

### What Is Empty / Broken

1. Theme evolution mostly empty:
   - `themes` is `0` snapshots across all primary demo personas.
   - `simulation_profile_updater` runs `run_theme_inference_incremental` only.
   - Incremental mode depends on crystallized `theme` patterns; no full theme generation fallback in updater.

2. Ayurvedic pipeline worker failing in simulation runs:
   - Error observed in worker results: `No module named 'core'`
   - File: `sakhi/apps/worker/tasks/ayurvedic_pipeline.py`
   - Cause: imports from `core.workers.*` (legacy path not present in this repo layout).

3. Crystallization can fail in simulation:
   - Observed error: `'str' object does not support item assignment`
   - Likely site: `sakhi/apps/api/services/crystallization/engine.py` where `trajectory_data`
     is mutated without robust JSON coercion from DB row values.

4. Two public simulation files are older/incompatible with current deep-state sections:
   - `stuck_creative.json`, `hormonal_harmony.json` have zero snapshots with `brain_states`.

## Test Reality (Verified Today)

### Passing

- `poetry run pytest sakhi/tests/unit/services/test_simulation_profile_updater.py -v --tb=short`
- `poetry run pytest sakhi/tests/unit/workers/test_pattern_workers.py -q`
- `poetry run pytest sakhi/tests/unit/workers/test_state_workers.py -q`
- `poetry run pytest kala/tests -q`

### Broken Harness Target

- `make quick-test` currently fails:
  - Target points to missing file: `sakhi/tests/v2/test_smoke.py`
  - Impact: `make verify` and `make ready-to-commit` inherit this failure.

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
make ready-to-commit
```

If `make ready-to-commit` fails because of the stale quick-test path, fix the target first or run equivalent explicit checks.
