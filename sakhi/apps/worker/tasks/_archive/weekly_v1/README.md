# Archived Weekly Workers (v1 Cleanup)

**Archived:** 2026-01-28
**Reason:** These workers did not serve the core v1 vision or were duplicates of turn workers

## Workers in this archive

### Duplicate with Turn Workers (effectively running on every turn anyway)

| File | Purpose | Why Archived |
|------|---------|--------------|
| `meta_reflection.py` | Weekly reflection quality scoring | Low value for v1 |

### Abstract/Low Value (5)

| File | Purpose | Why Archived |
|------|---------|--------------|
| `meta_audit.py` | Reflection bias checking | Too abstract |
| `weekly_reflection.py` | Weekly reflection rendering | Low value |

### Multi-User Features (2)

| File | Purpose | Why Archived |
|------|---------|--------------|
| `collective_patterns.py` | Aggregate patterns across users | Multi-user feature, not v1 |
| `rhythm_adjustments.py` | Adjust rhythm based on collective | Depends on collective_patterns |

### Overlap/Redundant (2)

| File | Purpose | Why Archived |
|------|---------|--------------|
| `weekly_planner_pressure_worker.py` | Planner pressure rollup | Low value planning feature |
| `turn_personal_model_update.py` | PM trends update | Overlaps with weekly_learning |

## Main Worker Files (in sakhi/apps/worker/_archive/weekly_v1/)

| File | Purpose | Why Archived |
|------|---------|--------------|
| `esr_deep.py` | ESR weekly deep sync | Duplicate - turn worker has esr_worker |
| `decision_graph_deep.py` | Decision graph refresh | Too abstract |
| `identity_timeline_deep.py` | Identity timeline evolution | Too abstract |

## Note on identity_momentum_deep

`identity_momentum_deep.py` is **NOT archived** - it is used by turn workers for per-turn identity tracking.
The weekly schedule was removed but the worker file remains active.

## Restoring

If you need to restore any of these workers:

1. Move the file back to appropriate location:
   - Task files: `sakhi/apps/worker/tasks/`
   - Main workers: `sakhi/apps/worker/`
2. Add import to `scheduler.py`
3. Add schedule function
4. Add call to `__main__` block
5. Add any required config variables

## References

- Main docs: `docs/WORKERS.md`
- Scheduler: `sakhi/apps/worker/scheduler.py`
