# Scaffolding Decision Record (SDR)

File: sakhi/apps/worker/tasks/focus_path_worker.py  
Scaffold Type (A / B / C / D): C  
Status (UNCHANGED | GATED | RESTRICTED): RESTRICTED  
Sensitivity (low / medium / high): medium  

Purpose (1–2 factual lines):  
Generates a deterministic focus path (anchor/progress/closure steps, intent_source) based on preview key tasks, leftovers, focus intent, tasks, and prior micro-scaffolds; persists the day’s path for retrieval.  

Inputs Read:  
- morning_preview_cache (key_tasks, reminders)  
- morning_momentum_cache (suggested_start)  
- micro_momentum_cache (nudge)  
- micro_recovery_cache (nudge)  
- daily_closure_cache (pending)  
- tasks table (todo/in_progress labels)  
- person_id resolution  

Outputs Produced:  
- focus_path_cache insert/update (anchor_step, progress_step, closure_step, intent_source, date)  
- personal_model.focus_path_state (date, steps, intent_source, generated_at)  

Consent Model:  
- Implicit scaffold; execution allowed only when suppression allows.  

Suppression Required:  
- yes (already enforced)  

Allowed Behavior:  
- Produce one deterministic focus path (no LLM).  
- Persist path to cache and personal_model for the same day only.  
- Respect suppression gate; exit silently when suppressed.  

Disallowed Behavior:  
- Advising priorities, performance framing, or multiple paths.  
- Coaching or claims about what “matters most.”  
- Writing to personal_model fields beyond focus_path_state.  
- Ignoring suppression outcome.  

Persistence Rules:  
- Day-scoped cache entry (focus_path_cache) mirrored to personal_model.focus_path_state; no accumulation beyond the day.  

Reason for Status:  
- Focus shaping is directional and may constrain user attention; restricted in v1 to avoid prescriptive prioritization.  

Lab Display Name:  
- Focus Path  

Lab Description (factual, non-narrative):  
- Deterministic focus path (anchor/progress/closure) derived from daily signals; cached per day.  

Tests Required:  
- [ ] ALLOW path  
- [ ] SUPPRESS path  

Test Status:  
- ALLOW:  
- SUPPRESS:  

File Lock Status:  
- LOCKED (intent)  
