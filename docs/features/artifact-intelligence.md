# Artifact Intelligence — Implementation Plan

> **Status**: Planning — Architecture review applied
> **Last Updated**: 2026-03-10
> **Scope**: Generic attachment system with longitudinal intelligence — simulation first, then mobile

---

## What We're Building

A system where anything a user shares — a document, photo, PDF, screenshot, receipt, lab report, contract — becomes a **typed contribution to their personal model**, not just a file in a folder. Artifacts are extracted, classified, embedded, stored as moments in the thread system, and made available for longitudinal synthesis through Kala's continuity layer.

The chat box is the entry point. Everything else is the intelligence layer.

---

## Core Mental Model

```
Artifact (any file)
    ↓
Classify (what kind of thing is this?)
    ↓
Extract (what does it contain? — type-aware)
    ↓
Structure (key entities, values, dates → JSONB)
    ↓
Embed (semantic search index)
    ↓
Moment (typed moment in the relevant thread)
    ↓
Kala event (governance ledger entry)
    ↓
Surface (in-chat response + timeline + synthesis)
```

---

## Must-Fix Architecture Decisions

These were identified in review and must be resolved before any code is written.

### 1. `artifact_collections` — No Array Storage
**Anti-pattern:** `artifact_ids UUID[]` stores membership as an array column.
**Fix:** Normalized join table `artifact_collection_members(collection_id, artifact_id)`. Counts and listings are derived via JOIN query, never from an array. The collections table holds only metadata.

### 2. Auth Binding — No `person_id` in Request Body or Query Params
**Problem:** Routes that accept `person_id` from the client allow any authenticated user to read/write another user's data.
**Fix:** Every artifact route extracts `person_id` from the auth principal (JWT/session), not from the request. If a caller passes a `person_id` that doesn't match the principal, return 403. Same policy as all other routes in this codebase.

```python
# In every artifact route:
principal_id = request.state.person_id   # set by auth middleware
if body.person_id and body.person_id != principal_id:
    raise HTTPException(403, "person_id does not match auth principal")
person_id = principal_id  # always use the principal, never the caller's claim
```

### 3. Storage Key, Not URL
**Problem:** Storing a `storage_url` bakes a potentially expiring or environment-specific URL into the database.
**Fix:** Store `storage_key TEXT` — the path within Supabase Storage (e.g. `artifacts/{person_id}/{artifact_id}/filename.pdf`). Generate short-lived signed URLs at serve time only. Never persist or log signed URLs.

```python
# At serve time:
signed = supabase.storage.from_("artifacts").create_signed_url(
    artifact.storage_key, expires_in=300  # 5 min
)
return signed["signedURL"]
```

### 4. Encryption and Redaction Requirements
`raw_text` and `structured_data` can contain PHI (health records) and PII (names, financials, legal terms). Requirements before these fields are written or read:

- **At rest:** Supabase column-level encryption for `artifact_extractions.raw_text` and `artifact_extractions.structured_data`. Use `pgcrypto` symmetric encryption keyed per-person, or rely on full-disk encryption + RLS — decision to be made per compliance requirements.
- **In logs:** Never log `raw_text`, `structured_data`, or `fact_value` fields. Log only `artifact_id`, `artifact_type`, `extraction_status`. The existing `_scrub_message` pattern in `call_llm` must be extended to artifact content.
- **In telemetry/Sentry:** Strip artifact content fields before sending to external sinks. Add `artifact_extractions` to the scrub list in the monitoring service.
- **In LLM prompts:** The existing PII masking in `call_llm` applies. Extraction prompts that include `raw_text` must route through the same scrubbing layer.

### 5. Generic Fact Ledger as Primary Model
**Problem:** `health_markers` is useful but domain-specific. Storing structured data only in `artifact_extractions.structured_data JSONB` is opaque and unsearchable. There is no generic queryable fact model.
**Fix:** Introduce `artifact_facts` as the **authoritative** structured fact store. `health_markers` becomes a domain-convenience view populated by the health domain adapter — it reads from `artifact_facts`, not the other way around.

```
artifact → artifact_extractions (raw_text, summary, embedding)
         → artifact_facts (one row per extracted fact, typed, with provenance)
              → health_markers (domain adapter materializes lab result facts here)
              → [future: financial_entries, legal_terms, etc.]
```

Every story claim in continuity synthesis must cite `artifact_id + fact_id` as provenance. No synthesized claim without a grounding source.

### 6. Worker Idempotency and Retry Contract
**Problem:** No retry strategy means a transient failure (LLM timeout, storage blip) leaves `extraction_status = 'processing'` forever with no recovery path.
**Fix:** Explicit idempotency and retry contract on every worker job.

```python
# Job payload (required fields):
{
    "artifact_id": str,
    "idempotency_key": f"extract-{artifact_id}-v1",  # bump version on schema changes
    "attempt": int,       # 1-indexed
    "max_attempts": 3,
}

# At job start:
# 1. Check artifact.extraction_status — if 'done', return immediately (idempotent)
# 2. Set extraction_status = 'processing', record job_id + attempt
# At job failure:
# 3. If attempt < max_attempts: re-enqueue with attempt+1, exponential backoff
# 4. If attempt == max_attempts: set extraction_status = 'failed', store error_message
# At job success:
# 5. Set extraction_status = 'extracted' (or 'needs_review' if confidence < threshold)
```

---

## Implementation Phases

| Phase | What | Goal |
|-------|------|------|
| **0** | Backend API + Python services | Core extraction pipeline |
| **1** | Simulation page (web) | Harden the API before mobile touches it |
| **2** | Mobile: chat input + bubbles | Upload in conversation, response grounded in artifact |
| **3** | Mobile: soul/timeline.tsx | Personal library view |
| **4** | Kala integration | Artifact-grounded objectives, constraints, arcs |

---

## Phase 0: Backend API

### New Database Tables

**Migration:** `sakhi/infra/scripts/migrations/0XXX_artifact_intelligence.sql`

```sql
-- ─────────────────────────────────────────────────────────────────────────────
-- CORE TABLES
-- ─────────────────────────────────────────────────────────────────────────────

-- Raw artifact metadata.
-- storage_key is the Supabase Storage path only — signed URLs are generated
-- at serve time and never persisted.
-- extraction_status: pending | processing | extracted | needs_review | failed
CREATE TABLE IF NOT EXISTS artifacts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id           TEXT NOT NULL,
    message_id          UUID,                      -- nullable: can exist outside a conversation
    storage_key         TEXT NOT NULL,             -- path in Supabase Storage, e.g. artifacts/{person_id}/{id}/file.pdf
    filename            TEXT NOT NULL,
    mime_type           TEXT NOT NULL,
    file_size_bytes     INTEGER,
    artifact_type       TEXT NOT NULL,             -- health_doc | financial | photo | article | legal | receipt | audio | other
    classification      TEXT,                      -- LLM subcategory: "blood_report", "tax_return", "receipt", etc.
    document_date       DATE,                      -- date OF the document, not the upload date
    extraction_status   TEXT DEFAULT 'pending',    -- pending | processing | extracted | needs_review | failed
    extraction_error    TEXT,                      -- populated on failure
    worker_job_id       TEXT,                      -- idempotency: last worker job that processed this
    worker_attempt      INTEGER DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- Extracted intelligence — created by async worker.
-- raw_text and structured_data may contain PHI/PII.
-- Apply column-level encryption per compliance requirements.
-- NEVER log or include these fields in telemetry/Sentry payloads.
CREATE TABLE IF NOT EXISTS artifact_extractions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id         UUID NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    raw_text            TEXT,                      -- full OCR / parsed text — ENCRYPTED AT REST
    summary             TEXT,                      -- LLM 2-3 sentence summary (no raw PII)
    tags                TEXT[] DEFAULT '{}',       -- auto-generated topics and entities
    embedding           vector(1536),              -- OpenAI text-embedding-3-small on summary+tags
    extraction_model    TEXT,
    overall_confidence  FLOAT DEFAULT 1.0,         -- 0-1; < 0.7 triggers needs_review
    extracted_at        TIMESTAMPTZ DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- GENERIC FACT LEDGER (authoritative structured data store)
-- Domain adapters (health, financial, legal) write facts here first,
-- then populate their convenience tables from these rows.
-- fact_value is always stored as text; fact_value_numeric is populated
-- for numeric facts to enable range queries and trend calculations.
-- provenance_span is the character offset range in raw_text that sourced
-- the fact — enables highlighting and audit.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS artifact_facts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id         UUID NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    extraction_id       UUID REFERENCES artifact_extractions(id) ON DELETE SET NULL,
    person_id           TEXT NOT NULL,
    fact_type           TEXT NOT NULL,             -- "lab_result" | "financial_amount" | "key_term" | "event_date" | "entity"
    fact_key            TEXT NOT NULL,             -- "HbA1c" | "total_income" | "contract_party" | "merchant"
    fact_value          TEXT NOT NULL,             -- always text — ENCRYPTED AT REST for health/legal/financial
    fact_value_numeric  NUMERIC,                   -- populated for numeric facts; NULL otherwise
    fact_unit           TEXT,                      -- "%" | "USD" | "ng/mL" | NULL
    confidence          FLOAT DEFAULT 1.0,         -- 0-1 LLM confidence for this specific fact
    provenance_span     TEXT,                      -- "char:142-158" — source location in raw_text
    observed_at         DATE,                      -- date the fact was true (from document_date)
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- COLLECTIONS — metadata only; membership is in the join table below.
-- artifact_ids UUID[] would be an anti-pattern — use artifact_collection_members.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS artifact_collections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id       TEXT NOT NULL,
    label           TEXT NOT NULL,             -- "Blood Reports", "Financial Docs", etc.
    artifact_type   TEXT NOT NULL,
    classification  TEXT,
    last_updated    TIMESTAMPTZ DEFAULT now(),
    UNIQUE(person_id, classification)
);

-- Normalized join table — never use UUID[] arrays for set membership.
CREATE TABLE IF NOT EXISTS artifact_collection_members (
    collection_id   UUID NOT NULL REFERENCES artifact_collections(id) ON DELETE CASCADE,
    artifact_id     UUID NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    added_at        TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (collection_id, artifact_id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- HEALTH MARKERS — domain convenience table.
-- Populated by the health domain adapter from artifact_facts.
-- artifact_facts is authoritative; this table is derived.
-- fact_id is the provenance link back to the source fact.
-- Cascade delete from artifacts propagates via artifact_facts → here.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS health_markers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id       TEXT NOT NULL,
    artifact_id     UUID NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    fact_id         UUID NOT NULL REFERENCES artifact_facts(id) ON DELETE CASCADE,
    marker_name     TEXT NOT NULL,             -- "HbA1c", "cholesterol_LDL", "ferritin"
    value           NUMERIC,
    unit            TEXT,
    reference_range TEXT,                      -- "4.0-5.6%" as string
    is_flagged      BOOLEAN DEFAULT false,     -- outside reference range
    document_date   DATE NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS artifacts_person_id_idx
    ON artifacts(person_id);
CREATE INDEX IF NOT EXISTS artifacts_person_status_idx
    ON artifacts(person_id, extraction_status);
CREATE INDEX IF NOT EXISTS artifact_extractions_artifact_id_idx
    ON artifact_extractions(artifact_id);
CREATE INDEX IF NOT EXISTS artifact_facts_artifact_id_idx
    ON artifact_facts(artifact_id);
CREATE INDEX IF NOT EXISTS artifact_facts_person_type_idx
    ON artifact_facts(person_id, fact_type);
CREATE INDEX IF NOT EXISTS artifact_facts_person_key_idx
    ON artifact_facts(person_id, fact_key);
CREATE INDEX IF NOT EXISTS artifact_collection_members_collection_idx
    ON artifact_collection_members(collection_id);
CREATE INDEX IF NOT EXISTS artifact_collection_members_artifact_idx
    ON artifact_collection_members(artifact_id);
CREATE INDEX IF NOT EXISTS health_markers_person_date_idx
    ON health_markers(person_id, document_date);
CREATE INDEX IF NOT EXISTS health_markers_person_marker_idx
    ON health_markers(person_id, marker_name, document_date);
```

---

### New Python Services

**`sakhi/apps/api/services/artifacts/`**

```
services/artifacts/
├── __init__.py
├── ingestion.py        # Upload handling, storage, metadata write
├── classification.py   # LLM: what type of document is this?
├── extraction.py       # Type-aware extraction router
├── extractors/
│   ├── __init__.py
│   ├── pdf.py          # PDF parse → text → LLM structured extraction
│   ├── image.py        # Vision model → description + OCR
│   ├── document.py     # Generic text doc extraction
│   └── health.py       # Health-specific: markers, values, units, dates
├── embedding.py        # Generate + store vector embeddings
├── collections.py      # Auto-group artifacts into collections
├── synthesis.py        # Cross-artifact LLM synthesis
└── search.py           # Semantic + structured search over artifacts
```

**Key service contracts:**

```python
# ingestion.py
async def upload_artifact(
    principal_id: str,        # always from auth middleware — never from caller
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    message_id: Optional[str] = None,
) -> dict:
    """
    1. Upload raw file to Supabase Storage at artifacts/{principal_id}/{artifact_id}/filename
       Store storage_key only — never store signed URLs
    2. Write artifacts row (extraction_status='pending', person_id=principal_id)
    3. Enqueue extraction worker job with idempotency_key
    4. Return { artifact_id, filename, extraction_status: 'pending' }
       — no storage_url in response; serve via signed URL endpoint only
    """

# classification.py
async def classify_artifact(
    filename: str,
    mime_type: str,
    raw_text_sample: str,  # first 500 chars — scrubbed of PII before LLM call
) -> tuple[str, str]:
    """
    Returns (artifact_type, classification)
    e.g. ("health_doc", "blood_report")
         ("financial", "tax_return")
         ("photo", "food")
         ("legal", "contract")
    """

# extraction.py
async def run_extraction(artifact_id: str, idempotency_key: str, attempt: int) -> None:
    """
    Idempotent full async pipeline:
    0. If artifact.extraction_status == 'extracted': return immediately (already done)
    1. Set extraction_status = 'processing', worker_job_id = idempotency_key, worker_attempt = attempt
    2. Download file from storage using storage_key (generate short-lived signed URL internally)
    3. Extract raw text (PDF/OCR/vision based on mime_type)
    4. Classify (artifact_type + classification)
    5. Run type-specific structured extractor → write artifact_facts rows
    6. Run domain adapters (health → health_markers, etc.) from artifact_facts
    7. Generate summary (no raw PII)
    8. Generate embedding on summary + tags
    9. Write artifact_extractions row
    10. Update artifacts: extraction_status = 'extracted' (or 'needs_review' if confidence < 0.7)
    11. Upsert artifact_collection_members via collections service
    12. Log Kala event: artifact_ingested (no raw content in event payload)
    13. Trigger continuity pattern check
    On failure:
    - If attempt < max_attempts: re-enqueue with attempt+1, exponential backoff (30s, 2m, 10m)
    - If attempt == max_attempts: set extraction_status = 'failed', store extraction_error
    """

# synthesis.py
async def synthesize_collection(
    principal_id: str,         # from auth — used to verify collection ownership
    collection_id: str,
    mode: str = "narrative",   # "narrative" | "comparison" | "trend"
) -> dict:
    """
    1. Verify collection.person_id == principal_id (403 otherwise)
    2. Fetch all artifact_facts for collection members (not raw_text)
    3. Run LLM synthesis grounded in structured facts only
    4. Return {
         synthesis_text: str,
         artifact_count: int,
         date_range: { from, to },
         source_citations: [{ artifact_id, fact_id, fact_key, fact_value, observed_at }]
       }
    Note: synthesis is grounded in artifact_facts, not raw_text or structured_data blob.
    Every claim in synthesis_text must have a corresponding source_citation.
    """
```

---

### New API Routes

**`sakhi/apps/api/routes/artifacts.py`**

```python
# All routes: person_id is NEVER accepted from the caller.
# person_id is always extracted from the authenticated session/JWT by middleware.
# Passing a person_id that doesn't match the auth principal → 403.

POST   /v1/artifacts/upload
       Auth: Required
       Body: multipart form (file, message_id?)      ← no person_id
       Returns: { artifact_id, filename, extraction_status: "pending" }
       Note: no storage_url in response; file served via /v1/artifacts/{id}/url only

GET    /v1/artifacts/{artifact_id}
       Auth: Required — 403 if artifact.person_id != principal
       Returns: artifact metadata + extraction summary + fact count
                (no raw_text or fact_value in list response)

GET    /v1/artifacts/{artifact_id}/url
       Auth: Required — 403 if artifact.person_id != principal
       Returns: { signed_url: str, expires_at: str }  ← 5-min TTL signed URL

GET    /v1/artifacts
       Auth: Required
       Query: type?, classification?, limit?, offset?  ← no person_id
       Returns: paginated artifact list for the auth principal

GET    /v1/artifacts/collections
       Auth: Required
       Returns: collections for the auth principal with member counts (via JOIN, not array)

POST   /v1/artifacts/synthesize
       Auth: Required
       Body: { collection_id, mode }                  ← no person_id
       Returns: {
         synthesis_text, artifact_count, date_range,
         source_citations: [{ artifact_id, fact_id, fact_key, fact_value, observed_at }]
       }

GET    /v1/artifacts/search
       Auth: Required
       Query: q (semantic query), type?, limit?       ← no person_id
       Returns: ranked artifacts for the auth principal with matched snippets

GET    /v1/artifacts/timeline
       Auth: Required
       Query: limit?, before_date?                    ← no person_id
       Returns: reverse-chronological artifacts for the auth principal

GET    /v1/artifacts/health-markers
       Auth: Required
       Query: marker_name?, from_date?, to_date?      ← no person_id
       Returns: time-series health marker values for the auth principal
```

---

### New Worker

**`sakhi/apps/worker/artifact_extraction_worker.py`**

```python
"""
Queue: artifact_extraction
Job payload: {
    "artifact_id": str,
    "idempotency_key": str,  # "extract-{artifact_id}-v1" — bump v on schema changes
    "attempt": int,          # 1-indexed
    "max_attempts": int,     # default 3
}

Idempotency guard (always first):
    if artifact.extraction_status == 'extracted':
        return  # already done — safe to re-enqueue

Retry contract:
    attempt 1 → failure → re-enqueue after 30s
    attempt 2 → failure → re-enqueue after 2 min
    attempt 3 → failure → set status='failed', store extraction_error, stop

Pipeline (run_extraction):
1.  Fetch artifact row, verify person_id matches (defense in depth)
2.  Set extraction_status = 'processing', worker_job_id, worker_attempt
3.  Download file from storage via internal signed URL (5-min TTL)
4.  Extract raw text (pdf → pdfminer, image → GPT-4o vision, audio → Whisper)
5.  Classify (artifact_type + classification) — uses scrubbed text sample
6.  Run type-specific structured LLM extractor
7.  Write artifact_facts rows (one per extracted fact, with provenance_span)
8.  Run domain adapters:
      health_doc → health_markers (from artifact_facts WHERE fact_type='lab_result')
      [future: financial → financial_entries, legal → legal_terms]
9.  Generate summary (no raw PII — derived from facts, not raw_text)
10. Generate embedding on (summary + tags)
11. Write artifact_extractions row
12. Set overall_confidence; if < 0.7 → extraction_status = 'needs_review'
    else extraction_status = 'extracted'
13. Upsert artifact_collection_members
14. Log Kala event: artifact_ingested (artifact_id, type, classification, fact_count only)
15. Trigger continuity pattern check
"""
```

---

### Extraction Strategies by Type

| MIME type | Raw extraction | Structured extraction |
|-----------|---------------|----------------------|
| `application/pdf` | pdfminer / pypdf | LLM with type-specific prompt |
| `image/jpeg`, `image/png` | GPT-4o vision → description + OCR | LLM parse from vision output |
| `image/heic` | Convert → vision | Same |
| `text/plain`, `text/csv` | Direct read | LLM parse |
| `application/vnd.openxmlformats-officedocument.*` | python-docx / openpyxl | LLM parse |
| `audio/mp4`, `audio/mpeg` | Whisper STT | LLM summary |

**Health doc structured output (example):**
```json
{
  "test_date": "2026-03-01",
  "lab_name": "LabCorp",
  "markers": [
    { "name": "HbA1c", "value": 5.9, "unit": "%", "reference": "4.0-5.6", "flagged": true },
    { "name": "Ferritin", "value": 12, "unit": "ng/mL", "reference": "12-150", "flagged": false }
  ]
}
```

**Financial doc structured output (example):**
```json
{
  "document_type": "tax_return",
  "tax_year": 2025,
  "total_income": 142000,
  "total_tax": 28400,
  "filing_status": "single"
}
```

**Receipt structured output (example):**
```json
{
  "merchant": "Whole Foods",
  "date": "2026-03-08",
  "total": 87.43,
  "currency": "USD",
  "category": "groceries",
  "items": [...]
}
```

---

## Phase 1: Simulation Page

### Goal
Harden the artifact intelligence API end-to-end before mobile touches it. Show the full pipeline running on real documents with real API calls.

### What the Simulation Demonstrates

```
┌──────────────────────────────────────────────────────────────────┐
│  ARTIFACT INTELLIGENCE — SIMULATION                              │
│  "Everything you share becomes part of your story."             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  STEP 1: UPLOAD          STEP 2: PIPELINE        STEP 3: STORY  │
│  ─────────────           ──────────────          ────────────── │
│  [Select artifact]       Classify ✓              Collections     │
│                          Extract  ✓              Synthesis       │
│  [Blood Report ▾]        Structure ✓             Timeline        │
│  [Tax Return   ▾]        Embed    ✓                              │
│  [Receipt      ▾]        Kala log ✓                              │
│  [Article      ▾]                                               │
│  [Upload own   ▾]                                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Preset Simulation Artifacts

**`apps/web/public/simulation/artifacts/`**

Five preset artifacts (real-looking synthetic data for Vidhya):

| File | Type | Classification | Purpose |
|------|------|---------------|---------|
| `bloodwork_march_2026.pdf` | health_doc | blood_report | Show health marker extraction + time-series |
| `bloodwork_december_2025.pdf` | health_doc | blood_report | Second blood report → enables trend synthesis |
| `rent_receipt_march.jpg` | financial | receipt | Show OCR + structured financial extraction |
| `sleep_article.pdf` | article | wellness_article | Show article summarization + topic tagging |
| `gym_membership_contract.pdf` | legal | contract | Show contract key term extraction |

### Simulation Scenario Config

**`apps/web/app/demo/artifact-simulation/scenarioConfigs.ts`**

```typescript
export type SimStep = "upload" | "classify" | "extract" | "structure" | "embed" | "kala" | "done";

export interface ArtifactScenario {
  id: string;
  label: string;
  description: string;
  presetFile: string;          // filename in /public/simulation/artifacts/
  expectedType: string;
  expectedClassification: string;
  expectedStructuredKeys: string[];  // keys we expect in structured_data
  expectedTags: string[];
  expectedKalaEventType: string;
  personId: string;
}

export const artifactScenarios: ArtifactScenario[] = [
  {
    id: "blood_report_march",
    label: "Blood Report — March 2026",
    description: "Latest quarterly bloodwork. Tests health marker extraction and time-series delta vs December.",
    presetFile: "bloodwork_march_2026.pdf",
    expectedType: "health_doc",
    expectedClassification: "blood_report",
    expectedStructuredKeys: ["test_date", "markers", "lab_name"],
    expectedTags: ["health", "blood_work", "HbA1c", "quarterly"],
    expectedKalaEventType: "health_document_ingested",
    personId: DEMO_USER_ID,
  },
  // ... other scenarios
];
```

### Simulation Page Layout

**`apps/web/app/demo/artifact-simulation/page.tsx`**

Three-panel layout (mirrors the governance simulation pattern):

```
┌──────────────────────────────────────────────────────────────────────┐
│  HEADER: "Artifact Intelligence" + persona pill (Vidhya)            │
├────────────────────────────────────┬─────────────────────────────────┤
│  LEFT PANEL: Artifact Selector     │  RIGHT PANEL: Intelligence      │
│  ──────────────────────────────    │  ────────────────────────────── │
│                                    │                                  │
│  [Blood Report — Mar 2026]  ← sel  │  PIPELINE STATUS                │
│  [Blood Report — Dec 2025]         │  ┌──────────────────────────┐   │
│  [Rent Receipt]                    │  │ ✓ Upload        0.1s     │   │
│  [Sleep Article]                   │  │ ✓ Classify      0.4s     │   │
│  [Gym Contract]                    │  │ ✓ Extract       1.2s     │   │
│  [+ Upload your own]               │  │ ✓ Structure     0.8s     │   │
│                                    │  │ ✓ Embed         0.3s     │   │
│  ─────────────────────────────     │  │ ✓ Kala event    0.1s     │   │
│  ARTIFACT PREVIEW                  │  └──────────────────────────┘   │
│  [PDF preview / image]             │                                  │
│                                    │  EXTRACTION RESULT               │
│  Type:     health_doc              │  ┌──────────────────────────┐   │
│  Class:    blood_report            │  │ Summary:                 │   │
│  Date:     2026-03-01              │  │ "Quarterly bloodwork     │   │
│  Tags:     health, HbA1c...        │  │  for March 2026. HbA1c  │   │
│                                    │  │  5.9% (↓ from 6.2)..."  │   │
│  [▶ Run Pipeline]                  │  ├──────────────────────────┤   │
│                                    │  │ STRUCTURED DATA          │   │
│                                    │  │ HbA1c:    5.9%  ↑ flag  │   │
│                                    │  │ Ferritin: 12    → ok    │   │
│                                    │  │ LDL:      118   → ok    │   │
│                                    │  └──────────────────────────┘   │
│                                    │                                  │
│                                    │  KALA EVENT                      │
│                                    │  ┌──────────────────────────┐   │
│                                    │  │ health_document_ingested  │   │
│                                    │  │ person: vidhya           │   │
│                                    │  │ markers: 3               │   │
│                                    │  │ flagged: HbA1c           │   │
│                                    │  └──────────────────────────┘   │
├────────────────────────────────────┴─────────────────────────────────┤
│  LONGITUDINAL SECTION (appears after ≥2 artifacts processed)        │
│  ─────────────────────────────────────────────────────────────────── │
│                                                                       │
│  COLLECTIONS              HEALTH TIMELINE         SYNTHESIS          │
│  ┌──────────────┐         ┌──────────────┐        ┌───────────────┐  │
│  │🩺 Blood  (2) │         │ HbA1c        │        │ [Synthesize ▶]│  │
│  │💰 Finance(1) │         │ Mar ██ 5.9%  │        │               │  │
│  │📄 Legal  (1) │         │ Dec ██ 6.2%  │        │ "Your HbA1c   │  │
│  │📰 Article(1) │         │ ↓ improving  │        │  has improved │  │
│  └──────────────┘         └──────────────┘        │  over 3 months│  │
│                                                    │  Ferritin has │  │
│                                                    │  stayed low..."│  │
│                                                    └───────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
```

### New Web API Proxy Routes

**`apps/web/app/api/artifacts/`**

```
apps/web/app/api/artifacts/
├── upload/route.ts              POST → /v1/artifacts/upload
├── [id]/route.ts                GET  → /v1/artifacts/{id}
├── list/route.ts                GET  → /v1/artifacts
├── collections/route.ts         GET  → /v1/artifacts/collections
├── synthesize/route.ts          POST → /v1/artifacts/synthesize
├── search/route.ts              GET  → /v1/artifacts/search
├── timeline/route.ts            GET  → /v1/artifacts/timeline
└── health-markers/route.ts      GET  → /v1/artifacts/health-markers
```

### Demo Seeder

**`sakhi/apps/api/services/demo/artifact_seeder.py`**

Seeds preset artifacts for Vidhya in the simulation:
- Uploads 5 preset documents to Supabase Storage (if not already there)
- Runs full extraction pipeline on each
- Creates collections
- Creates health_markers time-series rows

Idempotent — safe to re-run. All inserted rows keyed with `sim-artifact-*` prefix.

---

## Phase 2: Mobile — Chat Input + Bubbles

### Input Bar Changes

**`apps/mobile/app/experience/converse/index.tsx`**

Add attachment button to the left of the TextInput. When text is empty, show both attachment icon and voice icon. When text is being typed, show only send button (keep it clean).

```
No input:
[ 📎 ]  [ What's on your mind?... ]  [ 🎤 ]

Typing:
[ 📎 ]  [ Writing...              ]  [ ➚ ]

Attachment selected:
┌─────────────────────────────┐
│ 📄 bloodwork.pdf  ×         │  ← dismissible preview pill
└─────────────────────────────┘
[ 📎 ]  [ Add a note...        ]  [ ➚ ]
```

Tapping 📎 opens a bottom sheet (iOS ActionSheet):
- 📷 Take Photo
- 🖼️ Photo Library
- 📄 Browse Files

No forced caption/framing required. Sakhi interprets and responds. User can optionally add a note.

### Message Bubble: Artifact Rendering

New message type `artifact` renders differently from text messages:

```
Photo:
┌──────────────────────────────────┐
│  [████████ photo thumbnail ████] │
│  "Here's what I had for lunch"   │  ← optional caption
└──────────────────────────────────┘

PDF / Document:
┌──────────────────────────────────┐
│  📄  bloodwork_march.pdf         │
│      2 pages · blood_report      │
│  "Just got my results back"      │
└──────────────────────────────────┘
```

Tapping the artifact bubble opens it: native image viewer for photos, native PDF viewer for documents.

Sakhi's response bubble is rendered exactly as today — just grounded in extracted artifact content.

### Upload Flow (mobile)

```
1. User selects file
2. Artifact preview appears above input
3. User optionally adds caption, taps send
4. Optimistic: artifact bubble + caption appear in chat immediately
5. POST /v1/artifacts/upload (multipart) — returns artifact_id
6. POST /v2/turn with { text: caption, artifact_id } — Sakhi responds in-context
7. Background: worker runs full extraction
8. When extraction done: message status updates (shows extraction summary badge on bubble)
```

---

## Phase 3: Mobile — soul/timeline.tsx (Library View)

### Activate the Stub

The `soul/timeline.tsx` screen is currently a stub. This becomes the **Personal Library** — everything the user has ever shared, organized by month with collection groupings.

### Layout

```
TIMELINE / LIBRARY
─────────────────────────────────────

COLLECTIONS  (horizontal scroll)
┌──────────┐  ┌──────────┐  ┌──────────┐
│ 🩺       │  │ 💰       │  │ 📸       │
│ Blood    │  │ Financial│  │ Photos   │
│ Reports  │  │          │  │          │
│ 4 docs   │  │ 6 docs   │  │ 23 photos│
│ Synthesize  │ Synthesize  │ Browse   │
└──────────┘  └──────────┘  └──────────┘

ALL ARTIFACTS  (reverse chronological)
─────────────
March 2026
  📄 Blood Report      Mar 14  → health
  🖼️ Lunch photo       Mar 10  → nutrition
  📄 Q1 Tax Draft      Mar 3   → financial

February 2026
  📄 Blood Report      Dec 12  → health
  ...
```

Tapping a collection → opens collection detail with all artifacts + Synthesize button.
Tapping an artifact → opens artifact detail (preview + extraction summary + which thread it joined).
Tapping Synthesize → runs `/v1/artifacts/synthesize` → shows narrative synthesis.

### Navigation Entry Point

Add "Library" button to chat header alongside the existing "Profile" pill:

```
SAKHI
Good afternoon, Vidhya
[ ✦ Profile ]  [ 📚 Library ]
```

Or: Rename "Profile" to "Soul" and build a hub screen (`soul/index.tsx` — currently a stub) that lists:
- Reflection (→ topic-reflection)
- Library (→ timeline)
- Narrative (→ narrative stub)
- Values (→ values stub)

**Recommendation: build the hub screen.** It cleans up the header and gives future soul screens a home.

---

## Phase 4: Kala Integration

### Artifact Events in the Governance Ledger

Every artifact ingestion logs a Kala event:

```python
{
  "event_type": "artifact_ingested",
  "artifact_id": "...",
  "artifact_type": "health_doc",
  "classification": "blood_report",
  "person_id": "...",
  "flagged_markers": ["HbA1c"],   # for health docs
  "collection": "blood_reports",
  "document_date": "2026-03-01"
}
```

### Artifact-Grounded Objectives

When an objective exists in Kala (e.g., "improve HbA1c"), blood report uploads become **evidence events** for that objective. Kala's objective tracking becomes grounded in actual document data, not just conversation claims.

```python
# In extraction pipeline, after health_markers are written:
await update_objective_evidence(
    person_id=person_id,
    objective_tag="health_hba1c",
    evidence_type="lab_result",
    evidence_value=marker_value,
    evidence_date=document_date,
)
```

### Continuity Signals from Artifact Patterns

After each extraction, the continuity service checks for artifact patterns:

```python
# patterns to detect:
# - "blood_report_cadence": uploads every ~90 days → surface reminder if overdue
# - "financial_tracking": multiple receipts/statements → emerging financial thread
# - "article_cluster": multiple articles with same tags → surface as topic of preoccupation
# - "health_trend": marker improving/worsening over time → surface as continuity arc
```

---

## File Structure Summary

```
New Python backend:
sakhi/apps/api/
├── routes/artifacts.py                   # New route module
└── services/
    ├── artifacts/
    │   ├── __init__.py
    │   ├── ingestion.py
    │   ├── classification.py
    │   ├── extraction.py
    │   ├── extractors/
    │   │   ├── pdf.py
    │   │   ├── image.py
    │   │   ├── document.py
    │   │   └── health.py
    │   ├── embedding.py
    │   ├── collections.py
    │   ├── synthesis.py
    │   └── search.py
    └── demo/
        └── artifact_seeder.py            # Preset data for simulation

New worker:
sakhi/apps/worker/
└── artifact_extraction_worker.py

New migration:
sakhi/infra/scripts/migrations/
└── 0XXX_artifact_intelligence.sql

New web simulation:
apps/web/app/
├── demo/artifact-simulation/
│   ├── page.tsx
│   ├── scenarioConfigs.ts
│   ├── types.ts
│   └── components/
│       ├── ArtifactSelector.tsx
│       ├── PipelineStatus.tsx
│       ├── ExtractionResult.tsx
│       ├── CollectionsView.tsx
│       ├── HealthTimeline.tsx
│       └── SynthesisPanel.tsx
└── api/artifacts/
    ├── upload/route.ts
    ├── [id]/route.ts
    ├── list/route.ts
    ├── collections/route.ts
    ├── synthesize/route.ts
    ├── search/route.ts
    ├── timeline/route.ts
    └── health-markers/route.ts

New simulation assets:
apps/web/public/simulation/artifacts/
├── bloodwork_march_2026.pdf
├── bloodwork_december_2025.pdf
├── rent_receipt_march.jpg
├── sleep_article.pdf
└── gym_membership_contract.pdf

Mobile changes:
apps/mobile/app/
├── experience/converse/index.tsx         # Add attachment button + artifact bubble rendering
└── soul/
    ├── index.tsx                         # Activate as hub screen
    └── timeline.tsx                      # Activate as library view
```

---

## API Contract Summary

| Route | Method | Auth | Purpose |
|-------|--------|------|---------|
| `/v1/artifacts/upload` | POST | Required | Upload file, returns immediately |
| `/v1/artifacts/{id}` | GET | Required | Get artifact + extraction status |
| `/v1/artifacts` | GET | Required | List artifacts with filters |
| `/v1/artifacts/collections` | GET | Required | Auto-grouped collections |
| `/v1/artifacts/synthesize` | POST | Required | Cross-artifact LLM synthesis |
| `/v1/artifacts/search` | GET | Required | Semantic + structured search |
| `/v1/artifacts/timeline` | GET | Required | Reverse-chronological feed |
| `/v1/artifacts/health-markers` | GET | Required | Time-series health values |
| `/demo/seed/artifacts` | POST | Dev only | Seed preset artifacts for simulation |

---

## UX State Contract

Every artifact has a lifecycle state that maps to a visual treatment in the chat bubble and library view. The mobile UI must render each state distinctly — users need to know when Sakhi has fully processed something vs. is still working.

| Backend status | Bubble treatment | Library treatment |
|---------------|-----------------|-------------------|
| `pending` | Spinner on bubble | Gray row, "Queued..." |
| `processing` | Pulse animation on bubble | Gray row, "Processing..." |
| `extracted` | Clean bubble, no indicator | Full row with type badge + summary |
| `needs_review` | Amber badge "Low confidence" | Amber row, "Tap to review" |
| `failed` | Red badge "Could not read" | Red row, "Processing failed" |

**`needs_review`** means confidence < 0.7 on the overall extraction. The user should be able to tap the bubble and see what Sakhi extracted, confirm or dismiss uncertain facts. This is especially important for handwritten documents, blurry photos, or low-quality scans.

The bubble polls `GET /v1/artifacts/{id}` every 3s while status is `pending` or `processing`. Stop polling once any terminal state is reached (`extracted`, `needs_review`, `failed`).

---

## Privacy and Deletion — Definition of Done

Deleting an artifact is not just removing a row. It must be a complete and audited erasure of all derived data.

### Cascade Delete Contract

`DELETE /v1/artifacts/{artifact_id}` must:

1. Verify `artifact.person_id == auth_principal` (403 otherwise)
2. Delete raw file from Supabase Storage using `storage_key`
3. `DELETE FROM artifact_facts WHERE artifact_id = $1` (cascades to `health_markers` via fact_id FK)
4. `DELETE FROM artifact_extractions WHERE artifact_id = $1` (cascades embedding)
5. `DELETE FROM artifact_collection_members WHERE artifact_id = $1`
6. Re-evaluate any collections that had this artifact — recalculate if now empty
7. `DELETE FROM artifacts WHERE id = $1`
8. Scrub from vector index (delete embedding by artifact_id)
9. Log governance event: `artifact_deleted` — payload contains only `artifact_id`, `artifact_type`, `person_id`. **No content.**
10. Redact or tombstone any Kala event ledger entries that reference this artifact_id

No step may be skipped. Steps 2–9 should be wrapped in a transaction where possible; Storage deletion and vector deletion are best-effort with compensating cleanup job on failure.

### Account Deletion

When a person's account is deleted, all artifact data must be swept as part of the account deletion pipeline. The existing `POST /dev/reset-user-data` endpoint must include the artifact tables in its 30+ table wipe.

---

## Continuity Source Provenance

Every story claim that Sakhi makes in a synthesis or continuity reflection that is grounded in artifact data must carry explicit citations. This prevents hallucination, enables user verification, and satisfies auditability requirements.

### Synthesis Response Schema

```python
class SynthesisCitation(BaseModel):
    artifact_id: str
    fact_id: str
    fact_key: str
    fact_value: str          # display value — may be rounded/formatted for readability
    observed_at: date        # from the document, not the upload date

class SynthesisResult(BaseModel):
    synthesis_text: str
    artifact_count: int
    date_range: dict         # { from: date, to: date }
    source_citations: list[SynthesisCitation]
```

### Rule: No Claim Without Citation

In the LLM synthesis prompt, instruct the model to output claims only when the underlying fact exists in the provided fact list. Every sentence that makes a specific factual assertion (a value, a trend, a date, a name) must correspond to a `fact_id` in `source_citations`.

Example:
```
"Your HbA1c has improved from 6.2% to 5.9% over 3 months."
→ citations: [
    { fact_id: "abc", fact_key: "HbA1c", fact_value: "6.2%", observed_at: "2025-12-01" },
    { fact_id: "def", fact_key: "HbA1c", fact_value: "5.9%", observed_at: "2026-03-01" }
  ]
```

In the mobile UI, synthesis text can optionally show citation markers (tappable footnotes) linking back to the source artifact. This is Phase 3 polish — the data model must support it from day one.

---

## Definition of Done — Phase 1 (Simulation)

The simulation is ready to ship when:

**Pipeline**
- [ ] All 5 preset artifacts seed and extract successfully for Vidhya
- [ ] Pipeline status panel shows real timing from real API calls
- [ ] Structured data displayed is sourced from `artifact_facts` rows, not JSONB blob
- [ ] `health_markers` rows are populated from `artifact_facts` via domain adapter (not written directly)
- [ ] `artifact_collection_members` join table used — no `artifact_ids[]` arrays anywhere

**Intelligence**
- [ ] Two blood reports uploaded → health timeline shows delta (HbA1c 6.2 → 5.9)
- [ ] Collections auto-form correctly using JOIN query on `artifact_collection_members`
- [ ] Synthesis response includes `source_citations` array with `fact_id` references
- [ ] Kala event ledger shows `artifact_ingested` entries with no raw content in payload

**Auth + Security**
- [ ] All routes bind to auth principal — no `person_id` accepted from request body/query
- [ ] File served via signed URL endpoint only — no raw `storage_url` in any response
- [ ] `raw_text` and `fact_value` fields never appear in logs or error responses

**Resilience**
- [ ] Upload your own file works (PDF + image)
- [ ] All API routes return correct errors (not 500) when upstream fails
- [ ] Worker handles failure gracefully: attempt 1→2→3→`failed` with error stored
- [ ] Re-enqueueing an already-extracted artifact is a no-op (idempotent guard works)
- [ ] `needs_review` state correctly triggers when confidence < 0.7

---

## Definition of Done — Phase 2 (Mobile)

- [ ] Attachment button opens bottom sheet (camera / library / files)
- [ ] Selected file shows as preview pill above input
- [ ] Artifact bubble renders all 5 states: pending / processing / extracted / needs_review / failed
- [ ] Bubble polls extraction status every 3s until terminal state; stops cleanly on unmount
- [ ] Sakhi response is grounded in extracted artifact content
- [ ] Upload works on real device (iOS) with actual files
- [ ] Auth token attached to upload request; `person_id` never sent in request body
- [ ] Optimistic UI — bubble appears before server responds
- [ ] Signed URL fetched from `/v1/artifacts/{id}/url` at tap time, not stored on client
- [ ] Delete artifact → confirm dialog → calls delete endpoint → bubble removed, facts gone

---

## Notes

- **Extraction is always async.** The chat response comes from a fast LLM pass on the raw file (vision or first-page text). The full structured extraction happens in the worker. Update the bubble's status badge when extraction completes.
- **Document date is first-class.** Always extract the date the document was created, not the upload date. This keeps the timeline historically accurate.
- **No folder structure exposed to users.** Collections are auto-formed by classification. Users never see "upload to folder" — they just share things with Sakhi.
- **`artifact_facts` is authoritative.** Domain convenience tables (`health_markers`, future others) are derived from facts by adapters. If you need to reprocess, replay from `artifact_facts` — don't re-extract the document.
- **Health markers are never inferred from conversation.** They only come from document extraction via `artifact_facts`. This keeps Kala's objective tracking grounded.
- **Signed URLs are ephemeral.** Storage keys are permanent. Never cache, store, or send signed URLs beyond the immediate response. Generate fresh at each user request.
- **`raw_text` never leaves the extraction layer.** Synthesis, search, and continuity all operate on `artifact_facts` and `summary`. `raw_text` is available only for reprocessing and must never appear in API responses, logs, or LLM prompts that go to external sinks.
- **Start with PDF + image.** These cover 90% of real-world use cases. Audio and spreadsheet extraction come later.
