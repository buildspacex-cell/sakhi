# Scaffolding Decision Record (SDR)

File: sakhi/apps/worker/tasks/nudge_worker.py  
Scaffold Type (A / B / C / D): C  
Status (UNCHANGED | GATED | RESTRICTED): RESTRICTED  
Sensitivity (low / medium / high): high  

Purpose (1–2 factual lines):  
Checks forecast and tone to decide whether to send a proactive nudge; when active, writes nudge_log and updates personal_model.nudge_state.  

Inputs Read:  
- forecast_cache.forecast_state  
- personal_model.nudge_state  
- personal_model.tone_state  
- person_id resolution  

Outputs Produced:  
- nudge_log insert (category, message, forecast_snapshot)  
- personal_model.nudge_state (last_category, last_message, last_sent_at)  
- (best-effort) nudge message enqueue via _send_nudge_message  

Consent Model:  
- Implicit; execution allowed only when suppression allows and cooldown not active.  

Suppression Required:  
- yes (already enforced)  

Allowed Behavior:  
- Evaluate forecast/tone signals to decide if a nudge should be sent.  
- If should_send, record nudge in log and personal_model.nudge_state.  
- Respect suppression gate and cooldown; do nothing when suppressed or cooldown active.  

Disallowed Behavior:  
- Persuasion, motivational language, or behavioral steering beyond the single nudge decision.  
- Running when suppressed or during cooldown.  
- Writing to personal_model fields beyond nudge_state.  
- Multiple or cascading nudges in one run.  

Persistence Rules:  
- Logs each sent nudge to nudge_log; mirrors last sent info to personal_model.nudge_state.  
- No accumulation beyond recorded log entries; state is “last nudge” only.  

Reason for Status:  
- Nudges are inherently persuasive/steering and high sensitivity; restricted in v1 to prevent unintended behavior.  

Lab Display Name:  
- Nudge  

Lab Description (factual, non-narrative):  
- Proactive nudge check using forecast/tone; writes to nudge_log when enabled.  

Tests Required:  
- [ ] ALLOW path  
- [ ] SUPPRESS path  

Test Status:  
- ALLOW:  
- SUPPRESS:  

File Lock Status:  
- LOCKED (intent)  
