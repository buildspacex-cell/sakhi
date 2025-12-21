# Conversation Stack & Memory Upgrade – Validation Checklist

- **Schema migrations**
  - Apply `0014_conversation_state.sql` in staging.
  - Confirm `dialog_states` and `user_memories` tables exist with indices.

- **API smoke tests**
  - Exercise `/chat` outer-intent flow; verify `dialog_states.state` captures the pushed `outer_intent` frame.
  - Exercise inner-reflection-only turn; confirm frame resumes instead of duplicating.
  - Trigger recall or planner tool activation to ensure legacy flow still responds.
  - Call `GET /memories` and confirm the output matches the most recent `user_memories` rows and that `/chat` responses reference these memories in metadata.

- **Memory capture sanity**
  - Inspect `user_memories` rows for the test user to confirm summaries, importance score, and metadata payload.
  - Validate opt-out path: anonymous / missing `user_id` should not write rows.

- **Performance instrumentation**
  - Capture P95 latency before/after change; ensure added DB ops <15 ms on average.
  - Watch async task failure logs for `capture_salient_memory` to catch LLM routing issues.

- **Privacy & retention**
  - Run export/delete scripts to confirm `dialog_states` & `user_memories` are included and respect redaction rules.
  - Document data retention window for memories and schedule pruning job if needed.

- **Rollback plan**
  - Feature flag LLM memory summarizer by toggling `MODEL_MEMORY`; falling back to heuristic summary keeps flow safe.
  - Dropping the tables cleanly reverts to stateless behavior; ensure migrations are reversible in change log.
