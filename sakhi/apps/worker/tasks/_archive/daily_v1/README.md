# Archived Daily Workers (v1 Cleanup)

**Archived:** 2026-01-28
**Reason:** These workers did not serve the core v1 vision of Sakhi

## Workers in this archive

### Abstract/Vague Purpose (7)

| File | Purpose | Why Archived |
|------|---------|--------------|
| `alignment_refresh.py` | Value-behavior alignment | Too abstract for v1 |
| `narrative_arc_refresh.py` | Life narrative arcs | Too abstract |
| `pattern_sense_refresh.py` | Pattern sensing | Vague purpose |
| `inner_dialogue_refresh.py` | Internal voice state | Too abstract |
| `identity_drift_refresh.py` | Identity drift detection | Duplicate with turn worker |
| `inner_conflict.py` | Inner conflict state | Too abstract |
| `coherence.py` | Coherence state | Too abstract |

### Proactive Outreach - Never Wired (10)

These were developed but never connected to scheduler.py's main block:

| File | Purpose | Why Archived |
|------|---------|--------------|
| `evening_closure_worker.py` | Evening closure ritual | Never wired |
| `morning_preview_worker.py` | Morning snapshot | Never wired |
| `morning_ask_worker.py` | Morning question | Never wired |
| `morning_momentum_worker.py` | Morning momentum nudge | Never wired |
| `micro_momentum_worker.py` | Mid-morning nudge | Never wired |
| `micro_recovery_worker.py` | Afternoon recovery | Never wired |
| `focus_path_worker.py` | Focus guidance | Never wired |
| `mini_flow_worker.py` | Mini-flow session | Never wired |
| `micro_journey_worker.py` | Micro-journey | Never wired |
| `planner_auto_summary.py` | Daily planner summary | Low value for v1 |

## Restoring

If you need to restore any of these workers:

1. Move the file back to `sakhi/apps/worker/tasks/`
2. Add import to `scheduler.py`
3. Add schedule function call to `__main__` block
4. Add any required config variables

## References

- Main docs: `docs/WORKERS.md`
- Scheduler: `sakhi/apps/worker/scheduler.py`
