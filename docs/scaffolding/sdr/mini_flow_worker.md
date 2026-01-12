# Scaffolding Decision Record (SDR)

File: sakhi/apps/worker/tasks/mini_flow_worker.py  
Scaffold Type (A / B / C / D): C  
Status (UNCHANGED | GATED | RESTRICTED): RESTRICTED  
Sensitivity (low / medium / high): medium  

Purpose (1–2 factual lines):  
Generates a deterministic mini flow block (warmup, focus block, closure, optional reward) based on focus_path or tasks, adjusted by rhythm slot; persists the day’s flow for retrieval.  

Inputs Read:  
- focus_path_cache (anchor_step, progress_step, closure_step, intent_source)  
- tasks table (todo/in_progress labels)  
- rhythm slot from current timestamp (determine_rhythm_slot)  
- person_id resolution  

Outputs Produced:  
- mini_flow_cache insert/update (steps, source, rhythm_slot, date)  
- personal_model.mini_flow_state and mini_flow_rhythm_slot  

Consent Model:  
- Implicit scaffold; execution allowed only when suppression allows.  

Suppression Required:  
- yes (already enforced)  

Allowed Behavior:  
- Produce one deterministic mini flow structure (no LLM).  
- Persist flow to cache and personal_model for the same day only.  
- Respect suppression gate; exit silently when suppressed.  

Disallowed Behavior:  
- Coaching language or claims about optimal performance.  
- Multiple flows, follow-ups, or conversational guidance.  
- Writing to personal_model fields beyond mini_flow_state/mini_flow_rhythm_slot.  
- Ignoring suppression outcome.  

Persistence Rules:  
- Day-scoped cache entry (mini_flow_cache) mirrored to personal_model.mini_flow_state and mini_flow_rhythm_slot; no accumulation beyond the day.  

Reason for Status:  
- Outputs directional steps for work blocks; to avoid prescriptive focus coaching in v1, this scaffold is restricted.  

Lab Display Name:  
- Mini Flow  

Lab Description (factual, non-narrative):  
- Deterministic short flow block with rhythm-slot adjustments; cached per day.  

Tests Required:  
- [ ] ALLOW path  
- [ ] SUPPRESS path  

Test Status:  
- ALLOW:  
- SUPPRESS:  

File Lock Status:  
- LOCKED (intent)  
