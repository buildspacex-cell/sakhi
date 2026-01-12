import hashlib
from typing import Any, Dict, List, Optional


# Style guardrails for recognition prose
RECOGNITION_STYLE_RULES = {
    "tense": "present_or_present-perfect",
    "voice": "observational, calm, descriptive",
    "forbidden_phrases": [
        "this means",
        "this suggests you should",
        "appearing consistently rather than occasionally",
        "becoming a settled pattern",
        "therefore",
        "as a result",
        "you should",
        "try ",
        "consider",
        "recommend",
    ],
    "required_traits": [
        "variation in sentence structure",
        "no repeated certainty clauses",
        "no numeric confidence claims in prose",
        "no future projection",
    ],
    "paragraph_length": "1–2 sentences",
    "tone": "recognition, not explanation",
}

# Template pools per recognition type (1–2 sentences each, calm and observational)
RHYTHM_TEMPLATES = [
    "Over time, your energy and attention tend to gather later in the day.",
    "As days unfold, engagement often strengthens in the latter part of the day.",
    "Across days, the later hours hold more focus and momentum.",
]

IDENTITY_TEMPLATES = [
    "Your sense of direction has stayed steady, without sudden changes.",
    "Direction has held to a steady course, moving gradually rather than abruptly.",
    "The throughline of direction has remained intact, even as details shift.",
]

CONTINUITY_TEMPLATES = [
    "Recent patterns feel familiar rather than disruptive.",
    "Experiences keep a similar shape, repeating with variation but without instability.",
    "What is showing up now echoes prior stretches, more continuity than disruption.",
]

ABSENCE_TEMPLATES = [
    "No signs of crisis, conflict escalation, or internal overload appeared in this period.",
    "This stretch did not show signals of crisis, escalation, or suppression.",
    "Notably absent were destabilizing signals such as crisis or conflict escalation.",
]

EMOTION_TEMPLATES = [
    "Emotional intensity has stayed contained, without sharp swings.",
    "Feelings have remained steady, showing containment rather than volatility.",
    "Emotional tone has held steady, avoiding sudden spikes.",
]

# Additional guardrail phrases
FORBIDDEN_PHRASES = RECOGNITION_STYLE_RULES["forbidden_phrases"]


def _pick_template(templates: List[str], seed: str) -> str:
    """
    Deterministically pick a template based on the seed to avoid repetition.
    """
    if not templates:
        return ""
    # Use a stable hash to avoid randomness while varying across recognitions
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    idx = int(digest, 16) % len(templates)
    return templates[idx]


def _render_recognition_prose(rec: Dict[str, Any]) -> Optional[str]:
    domain = rec.get("domain")
    label = rec.get("label") or rec.get("signal") or ""
    if not domain or not label:
        return None

    seed = f"{domain}:{label}"
    if domain == "rhythm":
        return _pick_template(RHYTHM_TEMPLATES, seed)
    if domain == "emotion":
        return _pick_template(EMOTION_TEMPLATES, seed)
    if domain == "identity":
        return _pick_template(IDENTITY_TEMPLATES, seed)
    if domain == "familiarity":
        return _pick_template(CONTINUITY_TEMPLATES, seed)
    if domain == "absence" and rec.get("absence_flag"):
        return _pick_template(ABSENCE_TEMPLATES, seed)
    return None


def _validate_phrase(text: str) -> None:
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in text.lower():
            raise ValueError(f"Forbidden phrase detected in output: '{phrase}'")


def render_personal_intelligence(snapshot: Dict[str, Any]) -> List[str]:
    """
    Render recognitions into human-friendly, calm observations (bullet-style).
    """
    recognitions = snapshot.get("recognitions") or []
    bullets: List[str] = []

    for rec in recognitions:
        prose = _render_recognition_prose(rec)
        if not prose:
            continue
        _validate_phrase(prose)
        bullets.append(prose)

    return bullets


def render_personal_intelligence_narrative(snapshot: Dict[str, Any]) -> List[str]:
    """
    Render recognitions into short narrative paragraphs (1–2 sentences each).
    Order: Rhythm → Emotion → Identity → Familiarity → Absence.
    """
    recognitions = snapshot.get("recognitions") or []
    domain_order = ["rhythm", "emotion", "identity", "familiarity", "absence"]

    def get_domain_priority(rec: Dict[str, Any]) -> int:
        domain = rec.get("domain", "")
        try:
            return domain_order.index(domain)
        except ValueError:
            return 999

    paragraphs: List[str] = []
    for rec in sorted(recognitions, key=get_domain_priority):
        prose = _render_recognition_prose(rec)
        if not prose:
            continue
        _validate_phrase(prose)
        paragraphs.append(prose)

    return paragraphs
