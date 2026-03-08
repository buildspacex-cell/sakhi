# Incident Response Runbook (MVP)

> Last Updated: 2026-03-08  
> Scope: Sakhi API + worker incidents for known-user beta

## Purpose

Provide a single response path for security/privacy incidents and production reliability alerts.

## Alert Classes

- `repeated_auth_failures_detected`: auth failures crossed threshold within time window.
- `operator_access_granted` / `operator_access_denied`: break-glass path was used or rejected.
- `data_access_spike_detected`: export/delete operations crossed spike threshold.
- `crash_loop_detected`: same exception signature repeated above threshold in window.

## Severity and SLA

- `P0` (critical privacy/security, ongoing data risk): acknowledge in 15 min, mitigate in 60 min.
- `P1` (major reliability degradation): acknowledge in 30 min, mitigate in 4 hours.
- `P2` (contained issue/no user-facing impact): acknowledge same business day, resolve in 2 business days.

## Ownership Rotation

- Maintain one primary on-call owner and one secondary backup each week.
- Rotation cadence: weekly, Monday 00:00 local team time.
- Handover artifact required: active alerts, open incidents, pending mitigations, known risks.

## First 15 Minutes Checklist

1. Confirm alert source and current blast radius.
2. Check `/health/live` and `/health/ready`.
3. Validate latest deploy SHA and env drift (`SAKHI_RELEASE`).
4. Determine whether break-glass access is required.
5. Start incident log with timestamped actions.

## Playbooks

### Repeated Auth Failures

1. Confirm endpoint/path and failure reason.
2. Check for abusive source pattern (IP, user-agent, token misuse).
3. Tighten route guards/rate limits if active abuse.
4. If internal route misuse: enforce `SAKHI_ENABLE_INTERNAL_ROUTES_IN_PROD=0`.
5. Document root cause and required preventive change.

### Break-Glass Event

1. Verify operator id, approval ref, and reason are present.
2. Ensure event maps to an approved ticket/incident.
3. Time-box access window and track explicit start/end.
4. After action, confirm no persistent elevated access remains.

### Data Access Spike (Export/Delete)

1. Identify route(s) and subject scope affected.
2. Validate whether activity matches approved workflow.
3. If unexpected, disable relevant internal route or endpoint immediately.
4. Snapshot audit trail and notify privacy owner.

### Crash Loop

1. Identify signature (`where`, `exception_type`) and first-seen time.
2. Roll back or gate the offending path if user-facing.
3. Verify worker queue depth and API error rates stabilize.
4. Add regression test before re-enable.

## Required Post-Incident Outputs

- Timeline with UTC timestamps.
- Customer/user impact statement.
- Root cause and contributing factors.
- Mitigation completed + follow-up tasks with owners and due dates.
- Checklist update in `docs/guides/TODO_DEPLOY.md` if process changed.

## Environment Policy Knobs

- `SAKHI_ALERT_AUTH_FAILURE_THRESHOLD` (default `5`)
- `SAKHI_ALERT_AUTH_FAILURE_WINDOW_SEC` (default `300`)
- `SAKHI_ALERT_CRASH_LOOP_THRESHOLD` (default `5`)
- `SAKHI_ALERT_CRASH_LOOP_WINDOW_SEC` (default `300`)
- `SAKHI_ALERT_DATA_ACCESS_SPIKE_THRESHOLD` (default `8`)
- `SAKHI_ALERT_DATA_ACCESS_WINDOW_SEC` (default `600`)

Use platform env settings (Railway/Vercel) as source of truth in production.
