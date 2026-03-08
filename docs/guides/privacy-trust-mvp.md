# MVP Privacy & Trust Hardening (Known-User Beta)

> Last Updated: 2026-03-08  
> Scope: Early real users who personally know the Sakhi team

## Goal

Reduce the risk and fear that founders/operators can read private journals, and create verifiable trust controls before broader rollout.

## Claim Boundary (Use This Exact Language)

- **Allowed claim for MVP:** "No routine human access to journal content. Access is restricted, auditable, and break-glass only."
- **Do not claim yet:** "No one at Sakhi can read your data."

That stronger claim requires end-to-end encryption with user-held keys or confidential-compute guarantees.

## Threat Model (Known-User Beta)

Primary trust risks:
- Founder/operator can open prod DB and read journals.
- Journal content leaks via logs, traces, debug payloads, screenshots.
- Shared credentials make access untraceable.
- No clear deletion/retention policy.

## 7-Day Hardening Plan

### Day 0-1: Access Isolation (Highest Priority)

- [ ] Remove personal production DB credentials from all team machines.
- [ ] Create least-privilege runtime DB user for app/worker only.
- [x] Require break-glass path for privileged internal API access (code-enforced in prod when internal routes are enabled):
  - two-person approval
  - ticket/incident reference required
  - operator identity + reason required via headers (`x-sakhi-operator-id`, `x-sakhi-approval-ref`, `x-sakhi-breakglass-reason`, `x-sakhi-operator-token`)
- [ ] Extend break-glass policy to DB/operator console access (operational control outside app code):
  - time-limited access window
  - audited role-assumption on infra provider
- [ ] Enable immutable access logs (platform + DB audit trail) and keep for at least 180 days.
- [ ] Rotate all production secrets after access model changes.

### Day 1-2: Logging/Debug Lockdown

- [ ] Confirm `SAKHI_DEBUG_RESPONSE=0` in production.
- [ ] Confirm `SAKHI_ENABLE_INTERNAL_ROUTES_IN_PROD=0` (or unset).
- [x] Enforce authenticated person binding on user-scoped API routes (`/v2/turn`, conversation history, memory, continuity) so mismatched `?user=<uuid>` requests are rejected in production.
- [x] Scope deep reflection status/result reads by both reflection id and `person_id`.
- [x] Ensure no plaintext journal text in API logs, worker logs, alert payloads, or error traces (observability redaction wired for telemetry + monitoring + formatted logs).
- [x] Redact prompt payloads by default in production observability.
- [x] Review simulation/dev routes are blocked in production (route guardrails now include `/lab`, `/dev`, `/demo`, `/admin`, `/debug`, `/memory/dev`, `/system/audit`).

### Day 2-3: Encryption & Key Handling

- [ ] Keep TLS enforced end-to-end.
- [ ] Enable/confirm managed disk encryption for DB + backups.
- [x] Add per-user application-layer journal encryption on write (`raw_encrypted`) with `SAKHI_JOURNAL_MASTER_KEY` and `SAKHI_JOURNAL_WRITE_MODE`.
- [x] Complete strict rollout path (`encrypted_only`) with decrypt-read compatibility across workers, recall flows, and continuity surfaces.
- [ ] Set key policy so human operator principals cannot decrypt without break-glass role assumption.

### Day 3-4: Monitoring & Incident Response

- [ ] Set `SAKHI_MONITORING_ENABLED=1` in production.
- [ ] Configure at least one external sink:
  - `SAKHI_SENTRY_DSN`, and/or
  - `SAKHI_ALERT_WEBHOOK_URL` (PagerDuty/Opsgenie relay).
- [x] Alert policies in code now cover:
  - repeated auth failures (threshold-window burst detector)
  - break-glass access events (granted/denied standard alerts)
  - unexpected export/delete spikes (threshold-window burst detector)
  - worker/API crash loops (exception signature burst detector)
- [x] Create incident runbook with owner rotation and response SLA (`docs/guides/incident-response-runbook.md`).

### Day 4-5: Data Lifecycle Controls

- [ ] Publish retention defaults (for example: journals retained until user deletes, with account deletion purge SLA).
- [ ] Publish deletion policy with hard SLA (for example: full purge within 30 days).
- [ ] Add beta user export + delete request handling workflow (manual is acceptable for MVP if SLA is clear and tracked).

### Day 5-7: User-Facing Trust Artifacts

- [ ] Add in-product "Privacy & Trust" page:
  - what data is collected
  - who can access it
  - break-glass policy summary
  - retention/deletion policy
  - last updated date
- [ ] Add concise onboarding copy for known users:
  - no routine human reading
  - audited exceptional access only
  - deletion available on request
- [ ] Share a one-page beta privacy promise before invite acceptance.

## Railway + Vercel Implementation Mapping

### Railway (API/Worker/DB)

- Configure production env in Railway dashboard (source of truth).
- Required trust-related checks:
  - `SAKHI_MONITORING_ENABLED=1`
  - `SAKHI_DEBUG_RESPONSE=0`
  - `SAKHI_ENABLE_INTERNAL_ROUTES_IN_PROD=0` (or unset)
  - If internal routes must be enabled for emergency ops: set `SAKHI_OPERATOR_ACCESS_TOKEN` and send required break-glass headers
  - `SAKHI_JOURNAL_MASTER_KEY=<high-entropy-secret-at-least-32-chars>`
  - `SAKHI_JOURNAL_WRITE_MODE=encrypted_only` (default; `dual_write` only as temporary migration override)
  - `SAKHI_ALERT_WEBHOOK_URL` and/or `SAKHI_SENTRY_DSN`
- Keep app and worker credentials scoped to runtime needs only.
- Do not share owner/root project credentials for day-to-day support.

### Vercel (Web)

- Confirm production env does not expose debug toggles.
- Ensure app only talks to production API origin and never includes operator secrets.
- Keep auth/session secrets only in Vercel project env, not local files.

## Verification Gates (Run Before Each Beta Cohort)

```bash
make check-env
make check-env-prod-api
make check-env-prod-web
make pre-deploy
```

Manual gate:
- [ ] Attempted internal-route access in production is blocked.
- [ ] Prompt/journal text does not appear in log sinks.
- [ ] Break-glass access path is tested and audited.

## User Copy Template (Known-User MVP)

"Your journals are private by default. Sakhi team members do not routinely read personal journal content. Any exceptional access is time-limited, approval-based, and logged for audit. You can request export or deletion of your data at any time."

## Next Step to Reach "We Cannot Read" Claim

Move from access-control trust to cryptographic trust:
- end-to-end encryption with user-held keys, or
- confidential compute with remote attestation.

Until then, use the bounded MVP claim only.
