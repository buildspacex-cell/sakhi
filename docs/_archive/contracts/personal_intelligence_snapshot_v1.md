# Personal Intelligence Snapshot v1 — Contract

**Status**: LOCKED (v1)
**Created**: 2026-01-11
**Owner**: Sakhi Core Team

## What This Is

The Personal Intelligence Snapshot v1 is a **deterministic recognition system** that observes stable patterns in a person's longitudinal data. It is explicitly NOT:

- An advice system
- A recommendation engine
- An LLM inference layer
- A momentary state tracker

## Core Principles

### 1. Recognition, Not Insight

Personal Intelligence observes **what continues**, not what it means.

**Allowed**:
- "Over time, energy clusters later in the day."
- "Emotional intensity tends to remain contained."
- "Your sense of direction remains steady, without abrupt shifts."

**Forbidden**:
- "This means you should work in the evening."
- "Therefore, you are emotionally stable."
- "You need to maintain this pattern."

### 2. Deterministic Sources Only

Personal Intelligence reads from **pre-computed state fields** in the `personal_model` table:

- `rhythm_state` — Energy clustering patterns
- `emotion_state` — Emotional volatility patterns
- `identity_momentum_state` — Sense of direction patterns
- `emotion_soul_rhythm_state` — Cross-domain patterns
- `longitudinal_state` — Long-term continuity patterns

**No LLM inference** is allowed in assembling recognitions. Only deterministic pattern recognition from existing state fields.

### 3. Longitudinal Confidence Required

Personal Intelligence requires **weeks+ of data** to form recognitions. Single-day or single-week observations are not sufficient.

- **Minimum confidence window**: `weeks+`
- **Preferred confidence window**: `months+` or `years+`

### 4. Absence is a Signal

The absence of crisis, conflict escalation, or suppression events is **as meaningful** as their presence.

Example recognition:
- "Over time, no crisis, conflict escalation, or suppression events detected. This absence has remained appearing consistently rather than occasionally, a meaningful signal of continuity."

### 5. No Advice, No Recommendations

Personal Intelligence **never suggests what to do**. It only observes what has continued.

**Forbidden phrases** (enforced programmatically):
- "means"
- "therefore"
- "this suggests you should"
- "you need to"
- "this will help"
- "optimal"
- "optimize"

## Output Format

### Narrative Paragraphs (v1)

Each recognition is rendered as a **2-3 sentence descriptive paragraph**:

**Template**:
```
Over time, {signal}. This pattern has appeared {stability_language}, becoming {settled_vs_emerging}.
```

**Example**:
```
Over time, energy clusters later in the day. This pattern has appeared appearing consistently rather than occasionally, becoming a settled pattern.
```

### Ordering

Recognitions are ordered by domain priority:

1. **Rhythm** — Energy clustering patterns
2. **Emotion** — Emotional volatility patterns
3. **Identity** — Sense of direction patterns
4. **Familiarity** — Longitudinal continuity patterns
5. **Absence** — What didn't happen

### Capacity

Personal Intelligence Snapshot v1 returns **at most 5 recognitions** per snapshot.

## Recognition Object Structure

Each recognition is a structured object with the following fields:

```python
{
    "domain": str,              # rhythm | emotion | identity | familiarity | absence
    "signal": str,              # The observed pattern (lowercase, no period)
    "label": str,               # Human-readable label (capitalized, optional period)
    "stability": str,           # consistent | stable | emerging
    "confidence_window": str,   # weeks+ | months+ | years+
    "absence_flag": bool,       # True if this is an absence recognition
    "metadata": dict            # Domain-specific metadata
}
```

## UI Presentation

### Framing Sentence

```
These are stable patterns Sakhi has learned to recognize about you over time. They reflect continuity rather than momentary states.
```

### Anchor Window Display

For long-term anchors (365+ days):
```
Anchor: long-term, rolling (spanning multiple years)
These patterns are not based on a single week.
```

For shorter anchors:
```
Anchor: {N} days (rolling)
```

### Restraint Signal

```
This is recognition, not advice. You can ask questions or request suggestions if you want.
```

### Technical Details

The debug section is renamed to: **"How this recognition was formed"**

This includes:
- `raw_recognitions`: Structured Recognition objects
- `states_used`: Which state fields were used
- `anchor_window`: Time window description

## Implementation Files

### Core Services

- **Assembler**: `/sakhi/apps/api/services/personal_intelligence/assembler.py`
  - `assemble_personal_intelligence_snapshot()` — Reads state fields, constructs Recognition objects
  - `_rhythm_recognition()` — Rhythm domain recognition
  - `_emotion_recognition()` — Emotion domain recognition
  - `_identity_recognition()` — Identity domain recognition
  - `_continuity_recognition()` — Familiarity domain recognition

- **Renderer**: `/sakhi/apps/api/services/personal_intelligence/renderer.py`
  - `render_personal_intelligence_narrative()` — Converts Recognition objects to narrative paragraphs
  - `narrate_recognition()` — Single recognition to paragraph
  - `_humanize_label()` — Legacy bullet rendering (deprecated in v1)

### API Endpoints

- **Lab Endpoint**: `/lab/personal-intelligence`
  - GET query params: `person_id`, `anchor_days` (default: 1500, max: 1500)
  - Returns: `recognitions` (narrative paragraphs), `raw_recognitions`, `debug`, `timeframe`

### UI Components

- **Lab Page**: `/apps/web/app/lab/memory-details/page.tsx`
  - Displays Personal Intelligence Snapshot
  - Shows framing sentence, anchor window, recognitions, restraint signal
  - Collapsible debug section

## Constraints and Safeguards

### 1. Read-Only

Personal Intelligence Snapshot v1 is **read-only**. It does not write to any state fields or trigger any side effects.

### 2. Lab-Only (v1)

This system is currently **lab-only** (not production). It is available at:
- API: `/lab/personal-intelligence`
- UI: `/lab/memory-details`

### 3. Forbidden Phrase Detection

The renderer includes **programmatic checks** to prevent forbidden phrases from appearing in output. If a forbidden phrase is detected, a `ValueError` is raised.

### 4. No Writes to `personal_model`

The assembler queries `personal_model` but **never writes** to it. All state fields are pre-computed by separate workers.

## Future Considerations (Out of Scope for v1)

- **Multi-cycle intelligence**: Cross-cycle pattern recognition (requires multiple observation cycles)
- **Scaffolding layer**: Inference-based insights (requires LLM, not deterministic)
- **Action recommendations**: What to do based on recognitions (requires advice layer)
- **Real-time updates**: Streaming recognitions as new data arrives

## Version History

- **v1** (2026-01-11): Initial locked contract
  - Deterministic recognition only
  - Narrative paragraph rendering
  - 5-recognition capacity
  - Lab-only deployment

---

**End of Contract**

This document is LOCKED for v1. Any changes to the Personal Intelligence Snapshot system must be documented in a new version contract.
