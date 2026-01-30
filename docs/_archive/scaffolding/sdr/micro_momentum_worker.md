# Scaffolding Decision Record (SDR)

File: sakhi/apps/worker/tasks/micro_momentum_worker.py  
Scaffold Type (A / B / C / D): C  
Status (UNCHANGED | GATED | RESTRICTED): RESTRICTED  
Sensitivity (low / medium / high): medium  

Purpose (1–2 factual lines):  
Emits a deterministic mid-day micro-momentum nudge derived from morning preview/ask/momentum, closure, and open tasks; persists the day’s nudge for retrieval.  

Inputs Read:  
- morning_preview_cache (focus_areas, key_tasks, reminders)  
- morning_momentum_cache (momentum_hint, suggested_start, reason)  
- morning_ask_cache (question, reason)  
- daily_closure_cache (pending)  
- tasks table (todo labels)  
- person_id resolution  

Outputs Produced:  
- micro_momentum_cache insert/update (nudge, reason, date)  
- personal_model.micro_momentum_state (date, nudge, reason, generated_at)  

Consent Model:  
- Implicit mid-day scaffold; execution allowed only if suppression allows.  

Suppression Required:  
- yes (already enforced)  

Allowed Behavior:  
- Generate one deterministic micro-momentum nudge (no LLM).  
- Persist nudge to cache and personal_model for the same day only.  
- Respect suppression gate; exit silently when suppressed.  

Disallowed Behavior:  
- Motivational coaching or performance framing.  
- Multiple nudges or conversational follow-ups.  
- Writing to personal_model fields beyond micro_momentum_state.  
- Ignoring suppression outcome.  

Persistence Rules:  
- Day-scoped cache entry (micro_momentum_cache) mirrored to personal_model.micro_momentum_state; no accumulation beyond the day.  

Reason for Status:  
- Nudge framing is action-leaning and potentially intrusive; restricted in v1 to avoid motivational pressure.  

Lab Display Name:  
- Micro Momentum  

Lab Description (factual, non-narrative):  
- Deterministic mid-day micro-momentum nudge with reason; cached per day.  

Tests Required:  
- [ ] ALLOW path  
- [ ] SUPPRESS path  

Test Status:  
- ALLOW:  
- SUPPRESS:  

File Lock Status:  
- LOCKED (intent)  
