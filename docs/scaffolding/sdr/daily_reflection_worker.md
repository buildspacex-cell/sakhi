# Scaffolding Decision Record (SDR)

File: sakhi/apps/worker/tasks/daily_reflection_worker.py  
Scaffold Type (A / B / C / D): A  
Status (UNCHANGED | GATED | RESTRICTED): GATED  
Sensitivity (low / medium / high): low  

Purpose (1–2 factual lines):  
Generates a deterministic end-of-day reflection summary from session continuity and cached states; persists the summary for the day.  

Inputs Read:  
- session_continuity.continuity_state (recent turns, tasks, emotion/microreg snapshots, nudges)  
- personal_model (emotion_state, tone_state, microreg_state, coherence_state, conflict_state, identity_state)  
- forecast_cache.forecast_state  
- person_id resolution  

Outputs Produced:  
- daily_reflection_cache insert/update (summary, reflection_date)  
- personal_model.daily_reflection_state (summary payload)  

Consent Model:  
- Implicit end-of-day scaffold; execution allowed only when suppression allows.  

Suppression Required:  
- yes (already enforced)  

Allowed Behavior:  
- Produce one deterministic reflection summary (no LLM).  
- Persist summary to cache and personal_model for the same day only.  
- Respect suppression gate; exit silently when suppressed.  

Disallowed Behavior:  
- Evaluative language (“good/poor day”), coaching, or improvement framing.  
- Identity, performance, or emotional judgments.  
- Writing to personal_model fields beyond daily_reflection_state.  
- Ignoring suppression outcome.  

Persistence Rules:  
- Day-scoped cache entry (daily_reflection_cache) mirrored to personal_model.daily_reflection_state; no accumulation beyond the day.  

Reason for Status:  
- End-of-day recall summary is low sensitivity but still proactive; remains suppression-gated in v1.  

Lab Display Name:  
- Daily Reflection  

Lab Description (factual, non-narrative):  
- Deterministic end-of-day reflection summary; cached per day.  

Tests Required:  
- [ ] ALLOW path  
- [ ] SUPPRESS path  

Test Status:  
- ALLOW:  
- SUPPRESS:  

File Lock Status:  
- LOCKED (intent)  
