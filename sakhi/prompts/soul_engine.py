SOUL_EXTRACTION_PROMPT = """
Extract the deep "soul layer" signals from the user's text.

Return JSON with fields:
{
  "core_values": [],
  "longing": [],
  "aversions": [],
  "identity_themes": [],
  "commitments": [],
  "shadow_patterns": [],
  "light_patterns": [],
  "confidence": float
}

Rules:
- Extract only traits strongly implied by the text.
- Confidence ∈ [0,1].
- Keep lists short & precise.
- No philosophical abstractions — describe actual user traits.
"""

__all__ = ["SOUL_EXTRACTION_PROMPT"]
