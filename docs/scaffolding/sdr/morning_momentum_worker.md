# Scaffolding Decision Record (SDR)

File: sakhi/apps/worker/tasks/morning_momentum_worker.py  
Scaffold Type (A / B / C / D): C  
Status (UNCHANGED | GATED | RESTRICTED): RESTRICTED  
Sensitivity (low / medium / high): medium  

Purpose (1–2 factual lines):  
Surfaces a deterministic morning momentum hint and optional suggested start derived from prior preview, closure, and open tasks. Persists the daily hint to cache and personal_model for retrieval.  

Inputs Read:  
- morning_preview_cache (focus_areas, key_tasks, reminders)  
- morning_ask_cache (question, reason)  
- daily_closure_cache (pending)  
- tasks table (todo labels)  
- person_id resolution  

Outputs Produced:  
- morning_momentum_cache insert/update (momentum_hint, suggested_start, reason, date)  
- personal_model.morning_momentum_state (date, momentum_hint, suggested_start, reason, generated_at)  

Consent Model:  
- Implicit daily scaffold; execution allowed only when suppression allows.  

Suppression Required:  
- yes (already enforced)  

Allowed Behavior:  
- Generate one deterministic momentum hint and optional suggested_start (no LLM).  
- Persist hint to cache and personal_model for the same day only.  
- Respect suppression gate; exit silently when suppressed.  

Disallowed Behavior:  
- Motivational coaching tone or multiple prompts.  
- Advice, interpretation, or performance framing.  
- Writing to personal_model fields beyond morning_momentum_state.  
- Ignoring suppression outcome.  

Persistence Rules:  
- Day-scoped cache entry (morning_momentum_cache) mirrored to personal_model.morning_momentum_state; no accumulation beyond the day.  

Reason for Status:  
- Produces action-leaning momentum hints; to avoid motivational pressure in v1 it is restricted pending further governance.  

Lab Display Name:  
- Morning Momentum  

Lab Description (factual, non-narrative):  
- Deterministic daily momentum hint and optional starting point; cached per day.  

Tests Required:  
- [ ] ALLOW path  
- [ ] SUPPRESS path  

Test Status:  
- ALLOW:  
- SUPPRESS:  

File Lock Status:  
- LOCKED (intent)  
