Step 1 – Episodic Artifacts (code, purpose, trigger)

memory_episodic.py – implements the episodic builder/promoter. Active. Called only when explicitly invoked (e.g., build_episodic_from_journals_v2 in lab worker or API route).
memory.py – debug routes to build/clear episodic; manual, not auto. Active.
lab.py – lab “episodic” worker maps to build_episodic_from_journals_v2. Active in lab only.
runner.py – does NOT build episodic; only STM etc.
context_refresh_worker.py – reads episodic vectors into merged_context_vector. Active per turn/job.
synthesis.py – reads episodic records alongside STM for drift/theme synthesis. Active where synthesis is called.
turn_personal_model_update.py – reads episodic context_tags for longitudinal_state. Active via weekly scheduler/job.
engine.py, engine.py, engine.py, engine.py, various deep workers (identity_momentum_deep, rhythm_soul_deep, esr_deep, decision_graph_deep, narrative_deep, brain_goals_themes_refresh, weekly_learning_worker) – all query memory_episodic. Active when those workers run.
Schema/migrations: multiple *memory_episodic*.sql and 0024_memory_episodic_context_tags.sql define/add columns. Active.
Tests/docs mention but are non-executable.
Step 2 – How Episodes Are Built (exact)

Builder: build_episodic_from_journals_v2 (memory_episodic.py).
Inputs: journals from journal_entries for a supplied time window (start_ts, end_ts), filtered by user_id.
Grouping: strictly 1 journal → 1 episode (no clustering).
Fields written (via promote_to_episode):
id (new UUID), user_id (only; person_id and entry_id not populated), record JSON with source_entry_ids and summary, vector_vec from embedding of shallow summary, content_hash (md5 of journal content), context_tags (empty list), created_at (journal created_at).
No updated_at set (defaults).
Dedup: skips if content_hash already exists in memory_episodic for that user.
When it runs: only when invoked explicitly (lab episodic worker, debug route). Not triggered per turn.
Step 3 – Consumption Audit

Rhythm worker (turn_rhythm_update / run_rhythm_engine): does not read episodic (search finds no episodic reads in rhythm service).
Persona worker (turn_persona_update): does not read episodic; uses session persona, soul/narrative engines, journals/facets.
Personal model (turn_personal_model_update): reads memory_episodic.context_tags for current/previous window; otherwise uses rhythm/planner rollups. Does not read episodic text/vec/summary.
Insight generation (turn_insight_update / insight_engine): no episodic reads found.
Context builder (context_refresh_worker): reads episodic vector_vec (dedup by content_hash, applies 180-day cutoff) to build merged_context_vector. It does not include episodic entries content in entries (only vectors).
Memory synthesis (synthesis.py): combines STM + episodic records (record JSON, created_at) for theme/drift calculations when synthesis is called.
Other engines/workers: pattern_sense, emotion_loop, forecast, evidence_pack, deep workers (identity_momentum_deep, rhythm_soul_deep, esr_deep, decision_graph_deep, narrative_deep, weekly_learning_worker, brain_goals_themes_refresh) all query memory_episodic (usually selecting fields like record/summary/context_tags/vector_vec). These are active when those workers are scheduled/invoked.
Weekly signals worker explicitly avoids episodic (“Do NOT fetch anchors from memory_episodic”).
Step 4 – Data Flow (text)

Journal Entry → STM (memory_short_term) per turn.
Journal Entry → Episodic: only if build_episodic_from_journals_v2 is run; one episode per journal with summary/vector/content_hash.
STM is read by: context refresh, synthesis, most turn workers, personal model short_term ingestion, etc.
Episodic is read by: context refresh (vectors only for merged_context_vector); memory synthesis (records for themes/drift); personal model update (context_tags only); various deep/engine workers (pattern_sense, emotion_loop, forecast, evidence_pack, identity/decision/narrative deep, rhythm_soul_deep, weekly_learning_worker, brain_goals_themes_refresh) when those jobs run.
Components ignoring episodic: rhythm turn worker, persona turn worker, insight turn worker, planner turn worker, main turn context assembly (uses context cache; entries are STM-derived).
Step 5 – Reality Summary

Episodic memory exists but is manually built (not per turn) and is 1:1 with journals (shallow summaries). No entry_id/person_id linkage stored.
Consumption is partial: mainly vectors into context refresh and context_tags into personal model longitudinal_state; deeper workers can read episodic when scheduled, but turn-level workers (rhythm/persona/insight/planner) ignore it.
Context assembly uses episodic only via merged vector (no episodic entries in cache).
If memory_episodic were removed: merged_context_vector would lose long-horizon vectors; personal model longitudinal_state would lose context_tags input; any deep workers expecting episodic would have no data. Core turn flow (rhythm/persona/insight/planner/STM) would still operate.