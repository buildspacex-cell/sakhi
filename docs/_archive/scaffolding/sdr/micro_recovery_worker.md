# Scaffolding Decision Record (SDR)

File: sakhi/apps/worker/tasks/micro_recovery_worker.py  
Scaffold Type (A / B / C / D): C  
Status (UNCHANGED | GATED | RESTRICTED): RESTRICTED  
Sensitivity (low / medium / high): medium  

Purpose (1–2 factual lines):  
Emits a deterministic mid-day micro-recovery nudge based on task load, gaps since last turn, and leftover items; persists the day’s nudge for retrieval.  

Inputs Read:  
- morning_momentum_cache (momentum_hint, suggested_start)  
- micro_momentum_cache (nudge)  
- daily_closure_cache (pending)  
- tasks table (open/active counts)  
- conversation_turns (latest created_at)  
- person_id resolution  

Outputs Produced:  
- micro_recovery_cache insert/update (nudge, reason, date)  
- personal_model.micro_recovery_state (date, nudge, reason, generated_at)  

Consent Model:  
- Implicit scaffold; execution allowed only when suppression allows.  

Suppression Required:  
- yes (already enforced)  

Allowed Behavior:  
- Generate one deterministic micro-recovery nudge (no LLM, no health inference).  
- Persist nudge to cache and personal_model for the same day only.  
- Respect suppression gate; exit silently when suppressed.  

Disallowed Behavior:  
- Health/wellness advice or prescriptive rest instructions.  
- Identity, performance, or bodily-state claims.  
- Multiple nudges or follow-ups.  
- Writing to personal_model fields beyond micro_recovery_state.  
- Ignoring suppression outcome.  

Persistence Rules:  
- Day-scoped cache entry (micro_recovery_cache) mirrored to personal_model.micro_recovery_state; no accumulation beyond the day.  

Reason for Status:  
- Recovery-oriented nudges touch bodily/emotional sensitivity and can feel prescriptive; restricted in v1 to avoid unintended health guidance.  

Lab Display Name:  
- Micro Recovery  

Lab Description (factual, non-narrative):  
- Deterministic mid-day recovery nudge with reason; cached per day.  

Tests Required:  
- [ ] ALLOW path  
- [ ] SUPPRESS path  

Test Status:  
- ALLOW:  
- SUPPRESS:  

File Lock Status:  
- LOCKED (intent)  
