from __future__ import annotations

import re


def classify_inquiry_mode(question: str) -> str:
    """
    Classify inquiry mode based on the question text.

    - explain: asks why / how or evidence
    - meaning: asks what it means / is it a pattern (default)
    - advice: explicitly asks for suggestions or help
    """
    text = (question or "").lower()

    explain_patterns = [
        r"\bwhy\b",
        r"what made",
        r"how did",
        r"evidence",
        r"because",
    ]
    meaning_patterns = [
        r"what does this mean",
        r"\bpattern\b",
        r"\bongoing\b",
        r"\bis this\b",
        r"\bseem\b",
    ]
    advice_patterns = [
        r"\bsuggest\b",
        r"\badvice\b",
        r"what should i do",
        r"\bhelp\b",
        r"\brecommend\b",
    ]

    if any(re.search(p, text) for p in explain_patterns):
        return "explain"
    if any(re.search(p, text) for p in advice_patterns):
        return "advice"
    if any(re.search(p, text) for p in meaning_patterns):
        return "meaning"
    return "meaning"

