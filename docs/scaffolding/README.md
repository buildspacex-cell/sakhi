# Scaffolding v1 — SDR Template + Lock Checklist

This document is authoritative for Scaffolding v1. It must be used as-is for every scaffold file.

## Part 1 — Scaffolding Decision Record (SDR) Template

Create one SDR per scaffold file. Store it at:

`docs/scaffolding/sdr/<file_name>.md`

Copy this template exactly:

```
# Scaffolding Decision Record (SDR)

File:
Scaffold Type (A / B / C / D):
Status (UNCHANGED | GATED | RESTRICTED):
Sensitivity (low / medium / high):

Purpose (1–2 factual lines):

Inputs Read:
- 

Outputs Produced:
- 

Consent Model:
- 

Suppression Required:
- yes / no
  (If yes, reference decorator or call site)

Allowed Behavior:
- 

Disallowed Behavior:
- 

Persistence Rules:
- (ephemeral / cache-only / day-scoped / non-identity-forming)

Reason for Status:
- 

Lab Display Name:
Lab Description (factual, non-narrative):

Tests Required:
- [ ] ALLOW path
- [ ] SUPPRESS path (if proactive)

Test Status:
- ALLOW:
- SUPPRESS:

File Lock Status:
- DRAFT / LOCKED (intent) / CLOSED (tests passed)

Notes (factual only):
- 
```

Rules for the SDR:
- Descriptive only — no future plans
- No marketing language
- No opinions
- If something feels ambiguous → write it down
- If it’s not in the SDR → it doesn’t exist

## Part 2 — Scaffolding File Lock Checklist

Complete these steps for every file, in order.

### Phase A — Classification (No Code Yet)
- File identified in Scaffolding v1 scope
- SDR created using template
- Scaffold Type assigned (A / B / C / D)
- Sensitivity assigned (low / medium / high)
- Status chosen (UNCHANGED / GATED / RESTRICTED)
- Allowed vs Disallowed behavior explicitly written
- Persistence rules explicitly stated

Stop if the SDR is not clear.

### Phase B — Governance Enforcement
- Suppression required?
  - Decorator present OR
  - Central suppression call enforced
- Sensitivity correctly wired into suppression
- Early exit on SUPPRESS verified (code inspection)

### Phase C — Minimal Refactor (Only If Needed)
- No logic rewritten
- No new intelligence added
- No cadence changed
- Signal separated from language (if applicable)
- No new personal_model writes introduced
- Scope unchanged

### Phase D — Tests (Mandatory)
- ALLOW path tested (suppression returns ALLOW, expected output emitted)
- SUPPRESS path tested (suppression returns SUPPRESS, no output emitted, reason logged)
  - If proactive

Tests may be unit, worker dry-run, or lab-triggered. “Ran once” ≠ test.

### Phase E — Lab Visibility (Non-Negotiable)
- Scaffold appears in Lab
- Lab shows: Name, Type, Sensitivity, Status (Active / Suppressed / Disabled), Last Evaluated, Suppression decision + reason, Debug signal (no prose/advice)

### Phase F — Lock & Close
- SDR updated with final status
- Tests marked PASS
- File Lock Status = CLOSED
- Commit message includes: `Scaffolding v1: lock <file_name>`
- File will not be revisited in v1

## Part 3 — Definition of “Scaffolding v1 Done”

Scaffolding v1 is complete when:
- Every scaffold file has an SDR
- Every SDR is CLOSED
- Every proactive scaffold is suppression-gated
- Every scaffold is visible in Lab
- No scaffold emits language without signal
- Silence is observable and logged
- No ambiguity remains

At that point: “Sakhi’s support layer is governed, explainable, and safe.”
