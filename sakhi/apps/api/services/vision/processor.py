"""
Vision Processor
----------------
Core image understanding using Claude's vision capabilities.
"""

from __future__ import annotations

import base64
import logging
import json
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from pydantic import BaseModel

LOGGER = logging.getLogger(__name__)


class ImageAnalysis(BaseModel):
    """Result of image analysis."""
    description: str
    objects: List[str] = []
    text_detected: bool = False
    extracted_text: Optional[str] = None
    document_type: Optional[str] = None
    sentiment: Optional[str] = None
    key_information: Dict[str, Any] = {}
    tags: List[str] = []
    confidence: float = 0.8


class ScreenshotAnalysis(BaseModel):
    """Result of screenshot analysis."""
    description: str
    app_or_website: Optional[str] = None
    screen_type: Optional[str] = None  # 'error', 'form', 'dashboard', 'chat', etc.
    visible_text: Optional[str] = None
    ui_elements: List[str] = []
    suggested_actions: List[str] = []
    error_detected: bool = False
    error_message: Optional[str] = None


def _encode_image_to_base64(image_path: str) -> Tuple[str, str]:
    """Encode image file to base64 and determine media type."""
    path = Path(image_path)
    suffix = path.suffix.lower()

    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }

    media_type = media_type_map.get(suffix, "image/png")

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    return image_data, media_type


def _encode_bytes_to_base64(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """Encode image bytes to base64."""
    return base64.standard_b64encode(image_bytes).decode("utf-8")


async def process_image(
    image_source: str | bytes,
    mime_type: str = "image/png",
    context: Optional[str] = None,
) -> ImageAnalysis:
    """
    Process an image and extract understanding.

    Args:
        image_source: Path to image file or raw bytes
        mime_type: MIME type if bytes provided
        context: Optional context about what user wants to know

    Returns:
        ImageAnalysis with description, objects, text, etc.
    """
    from sakhi.apps.api.core.llm import get_router

    # Encode image
    if isinstance(image_source, str):
        image_data, media_type = _encode_image_to_base64(image_source)
    else:
        image_data = _encode_bytes_to_base64(image_source, mime_type)
        media_type = mime_type

    # Build prompt
    prompt = """Analyze this image and provide a structured analysis.

Return a JSON object with:
{
    "description": "Brief description of what's in the image",
    "objects": ["list", "of", "notable", "objects"],
    "text_detected": true/false,
    "extracted_text": "any text visible in the image" or null,
    "document_type": "receipt/invoice/note/screenshot/photo/etc" or null,
    "sentiment": "positive/negative/neutral" or null,
    "key_information": {
        // Any structured data extracted (dates, amounts, names, etc.)
    },
    "tags": ["relevant", "tags", "for", "categorization"]
}"""

    if context:
        prompt += f"\n\nUser context: {context}"

    prompt += "\n\nReturn ONLY valid JSON, no other text."

    try:
        router = get_router()
        response = await router.chat(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
        )

        # Parse response
        content = response.content[0].text if response.content else "{}"

        # Try to extract JSON
        try:
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())
            return ImageAnalysis(**data)
        except json.JSONDecodeError:
            LOGGER.warning("[vision] Failed to parse JSON, using raw description")
            return ImageAnalysis(
                description=content[:500],
                confidence=0.5,
            )

    except Exception as e:
        LOGGER.error("[vision] Image processing failed: %s", e)
        return ImageAnalysis(
            description="Failed to analyze image",
            confidence=0.0,
        )


async def analyze_screenshot(
    image_source: str | bytes,
    mime_type: str = "image/png",
    user_question: Optional[str] = None,
) -> ScreenshotAnalysis:
    """
    Analyze a screenshot specifically.

    Optimized for:
    - Error messages
    - UI/UX questions
    - App/website identification
    - Form filling assistance
    """
    from sakhi.apps.api.core.llm import get_router

    # Encode image
    if isinstance(image_source, str):
        image_data, media_type = _encode_image_to_base64(image_source)
    else:
        image_data = _encode_bytes_to_base64(image_source, mime_type)
        media_type = mime_type

    prompt = """Analyze this screenshot and provide structured information.

Return a JSON object with:
{
    "description": "What this screenshot shows",
    "app_or_website": "Name of the app or website if identifiable",
    "screen_type": "error/form/dashboard/chat/settings/document/other",
    "visible_text": "Key text visible on screen",
    "ui_elements": ["buttons", "forms", "menus", "etc"],
    "suggested_actions": ["What the user might want to do"],
    "error_detected": true/false,
    "error_message": "Error text if any" or null
}"""

    if user_question:
        prompt += f"\n\nUser is asking: {user_question}"

    prompt += "\n\nReturn ONLY valid JSON, no other text."

    try:
        router = get_router()
        response = await router.chat(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
        )

        content = response.content[0].text if response.content else "{}"

        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())
            return ScreenshotAnalysis(**data)
        except json.JSONDecodeError:
            return ScreenshotAnalysis(description=content[:500])

    except Exception as e:
        LOGGER.error("[vision] Screenshot analysis failed: %s", e)
        return ScreenshotAnalysis(description="Failed to analyze screenshot")


async def describe_image(
    image_source: str | bytes,
    mime_type: str = "image/png",
    style: str = "concise",
) -> str:
    """
    Get a natural language description of an image.

    Args:
        image_source: Path or bytes
        mime_type: MIME type
        style: 'concise', 'detailed', or 'poetic'

    Returns:
        Natural language description
    """
    from sakhi.apps.api.core.llm import get_router

    if isinstance(image_source, str):
        image_data, media_type = _encode_image_to_base64(image_source)
    else:
        image_data = _encode_bytes_to_base64(image_source, mime_type)
        media_type = mime_type

    style_prompts = {
        "concise": "Describe this image in 1-2 sentences.",
        "detailed": "Describe this image in detail, including objects, colors, composition, and mood.",
        "poetic": "Describe this image poetically, capturing its essence and feeling.",
    }

    prompt = style_prompts.get(style, style_prompts["concise"])

    try:
        router = get_router()
        response = await router.chat(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            model="claude-sonnet-4-20250514",
            max_tokens=500,
        )

        return response.content[0].text if response.content else "Unable to describe image"

    except Exception as e:
        LOGGER.error("[vision] Image description failed: %s", e)
        return "Unable to describe image"


async def extract_text_from_image(
    image_source: str | bytes,
    mime_type: str = "image/png",
) -> str:
    """
    Extract all visible text from an image (OCR-like).

    Returns:
        Extracted text or empty string
    """
    from sakhi.apps.api.core.llm import get_router

    if isinstance(image_source, str):
        image_data, media_type = _encode_image_to_base64(image_source)
    else:
        image_data = _encode_bytes_to_base64(image_source, mime_type)
        media_type = mime_type

    prompt = """Extract ALL text visible in this image.
Return ONLY the text, preserving layout where possible.
If no text is visible, return "NO_TEXT_FOUND"."""

    try:
        router = get_router()
        response = await router.chat(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
        )

        text = response.content[0].text if response.content else ""
        if text == "NO_TEXT_FOUND":
            return ""
        return text

    except Exception as e:
        LOGGER.error("[vision] Text extraction failed: %s", e)
        return ""


__all__ = [
    "ImageAnalysis",
    "ScreenshotAnalysis",
    "process_image",
    "analyze_screenshot",
    "describe_image",
    "extract_text_from_image",
]
