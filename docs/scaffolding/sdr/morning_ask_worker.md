# Scaffolding Decision Record (SDR)

File: sakhi/apps/worker/tasks/morning_ask_worker.py  
Scaffold Type (A / B / C / D): B — Capacity Surfacing  
Status (UNCHANGED | GATED | RESTRICTED): GATED  
Sensitivity (low / medium / high): medium  

Purpose (1–2 factual lines):  
Surfaces a single deterministic morning question based on prior day closure, preview focus, and open tasks. Persists the daily ask to cache and personal_model for retrieval.  

Inputs Read:  
- morning_preview_cache (focus_areas, key_tasks, reminders)  
- daily_closure_cache (pending)  
- tasks table (todo labels)  
- person_id resolution  

Outputs Produced:  
- morning_ask_cache insert/update (question, reason, ask_date)  
- personal_model.morning_ask_state (date, question, reason, generated_at)  

Consent Model:  
- Implicit daily scaffold; execution allowed only if suppression check returns ALLOW.  

Suppression Required:  
- yes (already enforced)  

Allowed Behavior:  
- Generate one deterministic morning question and reason (no LLM).  
- Persist ask to cache and personal_model for the same day only.  
- Writes are ephemeral, day-scoped, and non-identity-forming; preview output must not influence sensemaking layers.  

Disallowed Behavior:  
- Multiple questions, follow-ups, or conversational flow.  
- Narrative, advice, or interpretation of state.  
- Writing to any personal_model fields beyond morning_ask_state.  
- Bypassing suppression or running when suppressed.  

Persistence Rules:  
- Day-scoped cache entry (morning_ask_cache) and same ask mirrored to personal_model.morning_ask_state; no long-term accumulation.  

Reason for Status:  
- User-facing prompt surfaced proactively; must remain suppression-gated with bounded, non-identity persistence.  

Lab Display Name:  
- Morning Ask  

Lab Description (factual, non-narrative):  
- Deterministic daily morning question with reason; cached per day.  

Tests Required:  
- [ ] ALLOW path  
- [ ] SUPPRESS path  

Test Status:  
- ALLOW:  
- SUPPRESS:  

File Lock Status:  
- LOCKED (intent)  

Notes (factual only):  
- Suppression enforced via @require_suppression_check with sensitivity=MEDIUM.  
- Uses resolve_person_id to map user/person identifiers.  
