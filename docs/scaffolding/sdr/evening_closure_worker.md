# Scaffolding Decision Record (SDR)

File: sakhi/apps/worker/tasks/evening_closure_worker.py  
Scaffold Type (A / B / C / D): A  
Status (UNCHANGED | GATED | RESTRICTED): GATED  
Sensitivity (low / medium / high): low  

Purpose (1–2 factual lines):  
Generates a deterministic end-of-day closure summary from session continuity (completed/pending tasks, simple signals) and persists it for the day.  

Inputs Read:  
- session_continuity.continuity_state (last_tasks, last_emotion_snapshots)  
- person_id resolution  

Outputs Produced:  
- daily_closure_cache insert/update (completed, pending, signals, summary, date)  
- personal_model.closure_state (closure payload)  

Consent Model:  
- Implicit end-of-day scaffold; execution allowed only when suppression allows.  

Suppression Required:  
- yes (already enforced)  

Allowed Behavior:  
- Produce one deterministic closure summary (no LLM).  
- Persist closure to cache and personal_model for the same day only.  
- Respect suppression gate; exit silently when suppressed.  

Disallowed Behavior:  
- Evaluative language, performance judgment, or improvement framing.  
- Advising tomorrow’s actions or scoring the day.  
- Writing to personal_model fields beyond closure_state.  
- Ignoring suppression outcome.  

Persistence Rules:  
- Day-scoped cache entry (daily_closure_cache) mirrored to personal_model.closure_state; no accumulation beyond the day.  

Reason for Status:  
- Closure is low sensitivity but proactive; remains suppression-gated to prevent unintended evaluation drift.  

Lab Display Name:  
- Evening Closure  

Lab Description (factual, non-narrative):  
- Deterministic end-of-day closure summary; cached per day.  

Tests Required:  
- [ ] ALLOW path  
- [ ] SUPPRESS path  

Test Status:  
- ALLOW:  
- SUPPRESS:  

File Lock Status:  
- LOCKED (intent)  
