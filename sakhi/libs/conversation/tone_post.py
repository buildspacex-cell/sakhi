import re


def polish(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"\?\s*\?", "?", text)
    text = re.sub(r"(^|\.\s)(Do|Try)\s", r"\1You could ", text)
    parts = text.split("\n- ")
    if len(parts) > 2:
        return "\n- ".join(parts[:2])
    return text
