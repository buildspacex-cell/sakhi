### Scaffolding Decision Record (SDR)

File: `sakhi/apps/worker/tasks/morning_preview_worker.py`  
Scaffold Type (A / B / C / D): B — Capacity Surfacing  
Status (UNCHANGED | GATED | RESTRICTED): GATED  
Sensitivity (low / medium / high): medium  

Purpose (1–2 factual lines):  
- Generate a deterministic morning preview (focus areas, key tasks, reminders, rhythm hint) for the day.  
- Persist preview to cache and personal_model for retrieval.  

Inputs Read:  
- daily_closure_cache  
- personal_model (goals_state, rhythm_state)  
- tasks (status=todo)  
- person_id via resolve_person_id  

Outputs Produced:  
- morning_preview_cache  
- personal_model.morning_preview_state  

Consent Model:  
- Suppression enforced via decorator; logs decision and exits if suppressed.  

Suppression Required:  
- yes (already enforced)  

Allowed Behavior:  
- Deterministic preview generation (no LLM), summary string of counts/hints, storage in cache and personal_model.  
- Writes are ephemeral, day-scoped, and non-identity-forming; preview output must not influence sensemaking layers.  

Disallowed Behavior:  
- Narrative/advice generation, identity claims, bypassing suppression, multi-model writes beyond cache + personal_model.morning_preview_state.  

Reason for Status:  
- Proactive support scaffold that must honor suppression and remain deterministic; already guarded.  

Lab Display Name:  
- Morning Preview  

Lab Description (factual, non-narrative):  
- Morning forecast and readiness check  
