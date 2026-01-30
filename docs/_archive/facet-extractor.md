# Facet Extractor Specification (v0.1)

Purpose: convert any user input (voice transcript, typed text, structured signals such as calendar drops or wearable summaries) into **Person** and **Activity** facets that downstream systems consume via the contracts in `@sakhi/contracts`.

This spec stays language‑agnostic. It defines inputs, outputs, detection rules, confidence contracts, and evaluation criteria so we can plug in rules, LLM prompts, or ML models without rewriting the plumbing.

---

## 1. Input Contract

Ingested events arrive as `Message` (see contracts package). The extractor receives:

```ts
type FacetExtractorInput = {
  message: Message;
  transcript?: {
    raw: string;
    asr_confidence?: number;
  };
  metadata?: Record<string, unknown>;
};
```

* `message.content.text` is always present (ASR output for voice).
* `transcript.raw` retains un-normalized words (pauses, fillers). Use if prosody or filler detection matters.
* `metadata` can include channel‑specific hints (e.g., `calendar.event_id`, `wearable.reading`).

---

## 2. Output Contract

Return an array of `Facet` objects. Each facet must:

* include `message_id`
* set `confidence` (0–1)
* reference spans in the normalized text where possible
* add `extras` for future extension (namespaced keys)

```ts
type FacetExtractorOutput = {
  facets: Facet[];
  diagnostics?: {
    tokens_used?: number;
    latency_ms?: number;
    error?: string;
  };
};
```

---

## 3. Person Facet Dimensions

| Dimension | Description | Allowed Values / Ranges | Notes |
|-----------|-------------|-------------------------|-------|
| `valence` | Emotion polarity | −1 … +1 | negative = distress, positive = uplift |
| `arousal` | Activation/energy | 0 … 1 | >0.7 = high urgency |
| `need` | Current support need | `listen`, `plan`, `encourage`, `clarify`, `vent`, `unknown` | follows Awareness/Breath layer |
| `intention` | Interaction intention | `vent`, `plan`, `decide`, `reflect`, `report`, `unknown` | describes what user is trying to achieve |
| `emotion` | Text label for summary feeling | freeform string, prefer list (`overwhelmed`, `excited`, etc.) |
| `energy` | Self/implicit energy level | `low`, `neutral`, `high` | use cues (“drained”, “wired”, etc.) |

**Extraction guidance**
* `need` resolves from keywords + syntax + history. Example mapping:
  * "I just need to let this out" → `vent`
  * "Can you help me plan tomorrow?" → `plan`
* `intention` may default to `unknown` if not explicit.
* Use `extras.hypotheses` to store multiple plausible needs with weights if model uncertain.

---

## 4. Activity Facet Dimensions

| Dimension | Description | Values |
|-----------|-------------|--------|
| `action` | Verb phrase normalized (e.g., “finish deck”, “email Priya”) | text |
| `horizon` | When user expects action | `now`, `today`, `soon`, `later` |
| `effort` | Estimated depth | `light`, `medium`, `deep` |
| `importance` | Perceived importance | `low`, `medium`, `high`, `critical` |
| `duration_minutes` | Estimate if user mentions length | positive int |
| `context` | Additional descriptors (“with design team”, “before board”) | string |

**Detection heuristics**
1. Parse commands/requests/resolutions.
2. Each clause becomes one facet. Example: “Finish the deck today; tomorrow email Priya” → two facets.
3. Determine `horizon` via time expressions (“today”, “next week”, “ASAP”).
4. `effort` heuristics:
   * keywords like “prep, brainstorm” → `deep`
   * “send reminder”, “text” → `light`
   * else `medium`
5. `importance` combines modifiers (“critical, must, urgent”) + domain knowledge (health > high).

---

## 5. Extraction Pipeline

1. **Normalize text** (case folding, punctuation) but keep span map to original.
2. **Segment** into clauses/sentences.
3. **Detect decision intent** (Wardrobe/Travel/Gift, etc.) to feed Decision Engine.
4. **Run detectors**:
   * Person cues (feelings, needs, energy).
   * Activity cues (verb-object pairs, time expressions).
5. **Assemble facets** with spans + confidences.
6. **Post-process**:
   * Merge duplicates.
   * Cap number of facets per message (configurable default: 5 Person, 10 Activity).
7. Emit `facet.extracted` via Event Bus.

---

## 6. Confidence Rules

* Start at model confidence (LLM logprob or classifier output).
* Penalize if:
  * span not found → −0.1
  * relies on assumption (no explicit cue) → −0.2
* Promote if:
  * user explicitly states (“I feel …”) → +0.1 (max 1.0)
* Minimum: 0.05; drop facets below threshold to avoid noise.

---

## 7. Diagnostics & Logging

Emit `diagnostics` object when:
* extractor fallback triggered (e.g., exceeded token budget)
* low confidence overall (<0.3 average)
* detection of decision template intent

Log payloads with:
```jsonc
{
  "message_id": "...",
  "facets_count": 3,
  "avg_confidence": 0.67,
  "decision_intent": "wear?"
}
```

---

## 8. Evaluation Checklist

| KPI | Target |
|-----|--------|
| Person facet precision | ≥ 0.85 |
| Person facet recall | ≥ 0.7 (vent/listen detection more lenient) |
| Activity accuracy on action text | ≥ 0.9 exact/partial match |
| Horizon classification accuracy | ≥ 0.8 |
| Extraction latency | < 600 ms per message (LLM prompt budgets separate) |

*Use curated test suites covering emotion-only, mixed, command-heavy, and decision flows.*

---

## 9. Extensibility

* Add new dimensions via `extras.namespace_key`.
* Support streaming ASR by emitting interim facets with `extras.interim=true`.
* Provide adapter interface so multiple extractors (LLM, rule-based) can register with weighting or fallback.

---

## 10. Next Steps

1. Build unit tests with synthetic messages covering the example turn walkthroughs (Emotion-only, Mixed, Activity-first).
2. Draft LLM prompt template referencing this schema.
3. Integrate with Event Bus: after extraction, publish `facet.extracted`.
4. Monitor metrics and feed failures into Learning Engine for calibration.

