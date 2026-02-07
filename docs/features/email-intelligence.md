# Email Intelligence

> Email as a signal generator, not a content store.

---

## Overview

The Email Intelligence service extracts behavioral patterns from email metadata to inform Sakhi's understanding of the user. It integrates with the Friction Framework to surface email-related friction (chaos, intensity, stagnation).

**Key Principle**: We store minimal metadata to extract patterns, not archive emails. No email bodies are stored.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Email Provider (Gmail)                                         │
│  - OAuth 2.0 (read-only scope)                                  │
│  - Metadata-only fetch (headers, timestamps, labels)            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Normalized Event Model                                         │
│  - EmailEvent (provider-agnostic)                               │
│  - EmailThread, EmailSender                                     │
│  - Direction, timestamps, flags                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Signal Extractors                                              │
│  ├── SubscriptionDetector → Newsletters, marketing              │
│  ├── AvoidanceDetector → Threads awaiting reply                 │
│  ├── BoundaryDetector → Work/life boundary erosion              │
│  └── CognitiveLoadAnalyzer → Overwhelm risk                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Sakhi Integration                                              │
│  ├── Conversation context                                       │
│  ├── Surfaceable insights                                       │
│  └── Friction framework contribution                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Signals

### 1. Subscription Detection

Identifies recurring newsletters and marketing emails.

**Signals**:
- Sender frequency and cadence
- `List-Unsubscribe` header presence
- Known newsletter domains (Substack, Mailchimp, etc.)

**Use Cases**:
- "You receive newsletters from 15 sources. Want to review?"
- Digital declutter recommendations

### 2. Avoidance Patterns

Detects email threads the user is avoiding.

**Signals**:
- Incoming thread with no reply for 7+ days
- Follow-up emails received without response
- Thread importance indicators

**Severity Levels**:
- Mild: 7-14 days
- Moderate: 14-21 days
- Significant: 21+ days

**Use Cases**:
- "There's an email from 2 weeks ago you haven't replied to. Want to look at it?"
- Surface mental load from pending obligations

### 3. Boundary Erosion

Measures work/life boundary health based on email timing.

**Metrics**:
- After-hours email percentage (after 6 PM)
- Weekend email activity
- Late-night emails (after 11 PM)

**Friction Mapping**:
- High late-night activity → Chaos Friction (Vata)
- High weekend/evening → Intensity Friction (Pitta)

**Use Cases**:
- "Your after-hours email is up 20% this week. That affects rest."
- Boundary recommendations

### 4. Cognitive Load

Measures email-related cognitive burden.

**Metrics**:
- Active thread count (activity in last 3 days)
- Heavy threads (10+ messages or 5+ participants)
- Top senders by volume

**Risk Levels**:
- Low: Few active threads
- Moderate: 15+ active or 3+ heavy threads
- High: Load score > 0.7 or 5+ heavy threads

**Use Cases**:
- "Your email load is high (12 complex threads). Need help prioritizing?"

---

## API Endpoints

### OAuth Flow

```bash
# Start OAuth
POST /email/connect/gmail?person_id=<uuid>
Body: {"app_redirect_uri": "http://localhost:3000/settings"}
# Returns: {"auth_url": "https://accounts.google.com/...", "state": "..."}

# User is redirected to Google, consents, then redirected to:
GET /email/connect/gmail/callback?code=...&state=...
# API processes tokens, redirects to app_redirect_uri with ?status=connected
```

### Sync & Status

```bash
# Get status
GET /email/status?person_id=<uuid>

# Trigger sync
POST /email/sync?person_id=<uuid>

# Pause/resume
POST /email/sync/pause?person_id=<uuid>
POST /email/sync/resume?person_id=<uuid>
```

### Signals

```bash
# All signals
GET /email/signals?person_id=<uuid>

# Specific signals
GET /email/signals/avoidance?person_id=<uuid>&min_days=7
GET /email/signals/subscriptions?person_id=<uuid>&category=news
GET /email/signals/boundary?person_id=<uuid>
```

### Conversation Integration

```bash
# Surfaceable insight (proactive mention)
GET /email/insight?person_id=<uuid>

# Context for conversation engine
GET /email/context?person_id=<uuid>
```

---

## Database Tables

### email_sync_state
Stores OAuth tokens (encrypted) and sync state per provider.

| Column | Type | Description |
|--------|------|-------------|
| person_id | UUID | User ID |
| provider | TEXT | 'gmail', 'outlook' |
| status | TEXT | connecting, syncing, active, paused, error |
| access_token_encrypted | TEXT | Fernet-encrypted |
| refresh_token_encrypted | TEXT | Fernet-encrypted |
| history_id | TEXT | Incremental sync cursor |

### email_events
Normalized email metadata (no body).

| Column | Type | Description |
|--------|------|-------------|
| message_id | TEXT | Provider's message ID |
| thread_id | TEXT | Thread grouping |
| direction | TEXT | incoming, outgoing |
| sender_email | TEXT | Sender address |
| timestamp | TIMESTAMPTZ | When sent/received |
| is_newsletter | BOOL | Newsletter flag |
| has_unsubscribe | BOOL | Has List-Unsubscribe |

### email_signals
Extracted intelligence signals.

| Column | Type | Description |
|--------|------|-------------|
| signal_type | TEXT | subscription, avoidance, boundary_erosion, cognitive_load |
| signal_data | JSONB | Type-specific data |
| confidence | FLOAT | 0-1 confidence score |
| extracted_at | TIMESTAMPTZ | When extracted |

---

## Configuration

### Environment Variables

```bash
# Google OAuth (from Google Cloud Console)
GOOGLE_CLIENT_ID=<your-client-id>
GOOGLE_CLIENT_SECRET=<your-secret>

# API callback URL (must match Google Console)
GMAIL_OAUTH_CALLBACK_URL=http://localhost:8080/email/connect/gmail/callback

# Token encryption key
SAKHI_ENCRYPTION_KEY=<fernet-key>
```

### Google Cloud Console Setup

1. Create project → Enable Gmail API
2. APIs & Services → Credentials → Create OAuth 2.0 Client ID
3. Application type: Web application
4. Add redirect URI: `http://localhost:8080/email/connect/gmail/callback`
5. Copy Client ID and Client Secret to env

---

## Email Cognitive Offload (LLM Digest)

> Sakhi reads your emails and tells you what actually matters.

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Select Emails (4-tier priority)                              │
│     Tier 1: Recent human emails (7d, not newsletter)             │
│     Tier 2: Avoidance candidates (threads with no reply)         │
│     Tier 3: Starred/important (30d)                              │
│     Tier 4: User's sent emails (commitments)                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Fetch Bodies (transient, never stored)                        │
│     - Gmail API format=full → base64 decode                      │
│     - Mini-batches of 5 with 200ms delay                         │
│     - Truncated to 800 chars per email                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. LLM Triage (GPT-4o-mini, batches of 3)                      │
│     - Classify: action / fyi / noise                             │
│     - Action items: summary, deadline, priority, draft reply     │
│     - Extract commitments from sent emails                       │
│     - PII masking: all emails replaced before LLM sees them     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Store Digest (bodies discarded)                              │
│     - email_digests table (JSONB columns)                        │
│     - triage_counts, action_items, fyi_items, noise_summary     │
│     - commitments (things user promised in sent emails)          │
│     - Cached 6 hours                                             │
└─────────────────────────────────────────────────────────────────┘
```

### API Endpoints

```bash
# Get latest digest (auto-generates if missing)
GET /email/digest?person_id=<uuid>

# Force regenerate
POST /email/digest/generate?person_id=<uuid>&background=true
```

### API Endpoints (Commitments & Subscriptions)

```bash
# People commitments (promises to real people)
GET /email/commitments?person_id=<uuid>
PATCH /email/commitments/<id>  # {"status": "done"} or {"status": "dismissed"}

# Subscription trackers (memberships, renewals, billing)
GET /email/subscriptions?person_id=<uuid>
PATCH /email/subscriptions/<id>  # {"status": "done"} or {"status": "dismissed"}

# Dismiss an action item
POST /email/actions/dismiss  # {"message_id": "<id>"}
```

### Frontend

The **EmailDigestCard** on the Me page shows:
1. **Triage summary**: "3 emails need you · 12 FYI · 17 routine"
2. **Action items**: subject, sender, summary, deadline badge, expandable draft reply, dismiss button
3. **Your Commitments**: promises made to real people (done/dismiss buttons, stale indicator)
4. **Subscriptions & Renewals**: membership/billing trackers (done/dismiss buttons)
5. **FYI items**: one-line summaries (collapsible)
6. **Noise summary**: count + category breakdown (collapsible)
7. **Footer**: "X emails analyzed · Updated Xm ago" + Refresh button

### Database Table

#### email_digests

| Column | Type | Description |
|--------|------|-------------|
| person_id | UUID | User ID |
| digest_type | TEXT | 'daily' (default) |
| status | TEXT | pending, processing, completed, error |
| triage_counts | JSONB | {needs_action, fyi, noise} |
| action_items | JSONB | [{subject, sender, action_summary, deadline, priority, draft_reply}] |
| fyi_items | JSONB | [{subject, sender, one_line_summary}] |
| noise_summary | JSONB | {count, categories} |
| commitments | JSONB | [{commitment, deadline, subject, recipient}] |
| emails_analyzed | INT | Number of emails processed |
| period_start | TIMESTAMPTZ | Oldest email in digest |
| period_end | TIMESTAMPTZ | Newest email in digest |

### Cost

~$0.02 per digest via GPT-4o-mini (batches of 3 emails, 800 char truncation).

### Files

| File | Purpose |
|------|---------|
| `sakhi/apps/api/services/email/digest.py` | Core pipeline (select, fetch, analyze, store) |
| `sakhi/apps/api/services/email/digest_models.py` | Pydantic schemas for LLM output |
| `sakhi/apps/worker/tasks/email_digest_worker.py` | Background worker |
| `sakhi/infra/scripts/migrations/0005_email_digests.sql` | Database migration |
| `sakhi/infra/scripts/migrations/0006_email_commitments.sql` | Persistent commitments table |
| `sakhi/infra/scripts/migrations/0007_commitment_types_and_dismissed_actions.sql` | Commitment types + dismissed actions |
| `apps/web/app/api/email/digest/route.ts` | Next.js proxy route |
| `apps/web/app/api/email/commitments/route.ts` | Commitments proxy |
| `apps/web/app/api/email/subscriptions/route.ts` | Subscriptions proxy |
| `apps/web/app/api/email/actions/dismiss/route.ts` | Action dismiss proxy |
| `apps/web/app/experience/me/client.tsx` | EmailDigestCard component |

---

## Privacy Design

1. **Read-only scope**: Cannot send, modify, or delete emails
2. **Metadata only**: Email bodies are never stored — fetched transiently for LLM analysis, then discarded
3. **PII masking**: All email addresses replaced with `***@***` before LLM processing
4. **Encrypted tokens**: OAuth tokens encrypted at rest (Fernet)
5. **User control**: Disconnect deletes all email data
6. **RLS enforced**: Users can only access their own data

---

## Future Enhancements

- [ ] Outlook/Microsoft 365 adapter
- [ ] Email send capability (separate OAuth scope)
- [ ] Smart unsubscribe suggestions
- [ ] Email response time analysis
- [ ] Sender relationship mapping
- [x] LLM-powered email digest with triage and draft replies
- [x] Verification email + calendar invite filtering
- [x] Time-aware triage (past deadlines → noise)
- [x] Persistent commitment management (done/dismiss)
- [x] Membership/renewal → commitment tracking (no draft reply)
- [x] Separate subscriptions section (memberships/renewals vs people commitments)
- [x] Action item dismiss (persistent across digest regenerations)
- [x] Verification email exclusion from commitments

---

## Unified Messaging Architecture (Future)

> **When adding channel 2+ (WhatsApp, Telegram, SMS), do NOT duplicate this pipeline. Generalize.**

The email pipeline was built email-first, but 70%+ is channel-agnostic. When building the next messaging channel:

1. **Refactor** `email_events` → `message_events` with a `channel` column
2. **Extract adapter interface** — each channel implements `connect()`, `sync()`, `fetch_body()`
3. **Keep the triage pipeline unchanged** — LLM prompt, commitment extraction, dedup, and frontend card work across all channels
4. **Channel-specific only**: OAuth/connection flow, sync protocol, selection tier queries

What's reusable as-is:
- `analyze_batch()` — same LLM prompt for email, WhatsApp, SMS
- `_upsert_commitments()` — same commitment table and dedup
- Cross-batch dedup — same sender-based and fuzzy hash logic
- `EmailDigestCard` → `MessageDigestCard` — same UI, add channel badge
- Commitment management (done/dismiss) — channel-agnostic

What needs per-channel work:
- Adapter (Gmail API vs WhatsApp Business API vs Telegram Bot API)
- Sync flow (OAuth + polling vs webhooks)
- Selection queries (email threads vs WhatsApp conversations)
- Pre-filters (verification emails are email-only; group chat noise is WhatsApp-only)

See [BUILD_PLAN.md — Unified Messaging Pipeline](../BUILD_PLAN.md) for full architecture.
