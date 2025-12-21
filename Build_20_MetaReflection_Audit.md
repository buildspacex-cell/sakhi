# Build 20 – Meta-Reflection & Self-Improvement Audit

| Category | Check | Result | Notes / Fix |
| --- | --- | --- | --- |
| Worker | Expected `apps/worker/tasks/meta_reflection.py` with `run_meta_reflection` | ❌ | Only `synthesize_meta_reflection` exists (`sakhi/apps/worker/tasks/synthesize_meta_reflection.py`) and it merely summarizes reflections; no helpfulness/clarity scoring or JSON output. |
| Worker | Fetch last 10 insights/reflections with kinds filtering | ⚙️ | Current task pulls *all* reflections via `db_find` without limiting by kind or count; insights table never consulted. |
| Worker | call_llm with scoring schema {helpfulness_score, clarity_score, tone_feedback} | ❌ | Task calls `llm_reflect(..., mode="meta_reflection")` and stores plain text; no structured response or scoring fields. |
| Data Persistence | Update `insights.confidence` or `meta_reflection_scores` table | ❌ | Output inserted into `meta_reflections` via `db_insert` without touching insights or a dedicated scores table. No schema for `meta_reflection_scores` found. |
| Scheduler | schedule_meta_reflection_jobs weekly on reflection queue | ❌ | Scheduler only enqueues `synthesize_meta_reflection` from `schedule_learning_self_jobs`; no weekly cron guard or dedicated helper. |
| Scheduler | DEFAULT_USER_ID + queue parity | ⚙️ | Existing enqueue helpers default to reflection queue and DEFAULT_USER_ID, but without dedicated schedule it rides whichever loop calls `schedule_learning_self_jobs`. |
| Schema | insights.confidence column present | ⚙️ | Insights model referenced elsewhere but migrations not in repo; cannot verify column or constraints. |
| Schema | meta_reflection_scores table structure | ❌ | No table or migration located via `rg`; scoring persistence missing. |
| Prompting | Prompt text matches “Evaluate the following reflections…” etc. | ⚙️ | Prompt summarizes learnings; does not request scoring or tone feedback explicitly. |
| Feedback propagation | Updated values flow into insights + reflections | ❌ | Task writes separate summary only; no confidence adjustments or follow-up jobs triggered. |
| Logging | “[Meta-Reflection] Completed …” log emitted | ❌ | Task performs no logging, so monitoring can’t confirm execution. |
| End-to-end | Manual trigger updates insight rows without duplicates | ❌ | No public API/worker entry point `run_meta_reflection`; can’t trigger required behavior; running `synthesize_meta_reflection` merely appends meta_reflections rows. |

## Metrics
- Mean helpfulness: N/A – helpfulness scoring not implemented.
- Mean clarity: N/A – clarity scoring not implemented.
- Confidence variance: N/A – insights.confidence unchanged by current task.

## Recommended Remediation
1. Implement `apps/worker/tasks/meta_reflection.py` with `run_meta_reflection(person_id)` that queries latest insights/reflections, calls `call_llm` with a JSON schema, and persists scores.
2. Add `schedule_meta_reflection_jobs()` in the scheduler (weekly cron, reflection queue, DEFAULT_USER_ID) and wire it into `scripts/run_schedulers.py`.
3. Extend the DB schema (migration) to add `meta_reflection_scores` table or augment `insights` with meta fields; include FK + cascade behavior.
4. After scoring, write summaries back to `insights.confidence` (or `reflections.meta_feedback`) and emit structured logs for observability.
5. Provide API/CLI trigger plus integration tests verifying averages and persistence without duplicates.
