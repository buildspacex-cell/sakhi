"""
Screen Analyzer Service
-----------------------
Analyzes screenshots using Claude Vision to understand screen state.

This service is the "eyes" of Sakhi's vision loop:
- Takes a screenshot
- Sends it to Claude Vision (via OpenRouter)
- Returns structured understanding of what's visible

The analysis includes:
- Description of the current screen/page
- Detected UI elements and their positions
- Any visible text (OCR-like extraction)
- Current app and URL context
- Actionable elements that can be clicked/interacted with
"""

from __future__ import annotations

import base64
import io
import logging
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

LOGGER = logging.getLogger(__name__)

# Vision model - Claude 3.5 Sonnet via OpenRouter for multimodal
# This model excels at visual understanding and UI element detection
DEFAULT_VISION_MODEL = "anthropic/claude-3-5-sonnet"

# Maximum image dimension for compression (reduces token cost)
MAX_IMAGE_DIMENSION = 1568  # Claude's recommended max for good quality/cost balance


# =============================================================================
# Screen Analysis
# =============================================================================

async def analyze_screen(
    screenshot_path: str,
    width: int,
    height: int,
    *,
    task_context: Optional[str] = None,
    previous_actions: Optional[List[Dict[str, Any]]] = None,
    focus_area: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Analyze a screenshot using Claude Vision.

    Args:
        screenshot_path: Path to the screenshot file
        width: Screenshot width in pixels
        height: Screenshot height in pixels
        task_context: What the user is trying to accomplish
        previous_actions: Recent actions taken for context
        focus_area: Optional region to focus on {x, y, width, height}

    Returns:
        Structured analysis of the screen state
    """
    from sakhi.apps.api.core.llm import get_router

    # Load and optionally compress image
    image_data, media_type = await _load_and_compress_image(screenshot_path)
    if not image_data:
        LOGGER.error("[screen_analyzer] Failed to load image: %s", screenshot_path)
        return _empty_analysis()

    # Build the prompt
    prompt = _build_analysis_prompt(
        task_context=task_context,
        previous_actions=previous_actions,
        width=width,
        height=height,
    )

    try:
        router = get_router()
        # Use dedicated vision model (Claude 3.5 Sonnet via OpenRouter)
        target_model = os.getenv("MODEL_VISION") or DEFAULT_VISION_MODEL

        # Build image URL in OpenAI format (which OpenRouter expects)
        image_url = f"data:{media_type};base64,{image_data}"

        # Call LLM with vision using OpenAI-style multimodal format
        response = await router.chat(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
            model=target_model,
            max_tokens=2000,
        )

        # Parse response
        content = response.content[0].text if response.content else ""
        analysis = _parse_analysis_response(content)

        LOGGER.info(
            "[screen_analyzer] Analyzed screen: %s (found %d elements)",
            analysis.get("description", "")[:50],
            len(analysis.get("elements", [])),
        )

        return analysis

    except Exception as e:
        LOGGER.exception("[screen_analyzer] Analysis failed: %s", e)
        return _empty_analysis(error=str(e))


async def analyze_screen_for_element(
    screenshot_path: str,
    element_description: str,
    width: int,
    height: int,
) -> Optional[Dict[str, Any]]:
    """
    Find a specific element on screen.

    Returns the element's coordinates if found, None otherwise.

    Args:
        screenshot_path: Path to the screenshot
        element_description: What to look for (e.g., "search button", "login link")
        width: Screenshot width
        height: Screenshot height

    Returns:
        Element info with coordinates, or None if not found
    """
    from sakhi.apps.api.core.llm import get_router

    image_data, media_type = await _load_and_compress_image(screenshot_path)
    if not image_data:
        return None

    prompt = f"""Look at this screenshot ({width}x{height} pixels) and find the following element:

"{element_description}"

If you find it, respond with a JSON object:
{{
    "found": true,
    "element": {{
        "description": "what you found",
        "type": "button|link|input|text|image|other",
        "x": center_x_coordinate,
        "y": center_y_coordinate,
        "width": approximate_width,
        "height": approximate_height,
        "text": "visible text if any"
    }},
    "confidence": 0.0-1.0
}}

If you cannot find it, respond with:
{{
    "found": false,
    "reason": "why it wasn't found"
}}

Return ONLY the JSON, no other text."""

    try:
        router = get_router()
        target_model = os.getenv("MODEL_VISION") or DEFAULT_VISION_MODEL
        image_url = f"data:{media_type};base64,{image_data}"

        response = await router.chat(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
            model=target_model,
            max_tokens=500,
        )

        content = response.content[0].text if response.content else "{}"
        result = _parse_json_response(content)

        if result.get("found"):
            return result.get("element")
        return None

    except Exception as e:
        LOGGER.exception("[screen_analyzer] Element search failed: %s", e)
        return None


async def extract_text_from_screen(
    screenshot_path: str,
    region: Optional[Dict[str, int]] = None,
) -> str:
    """
    Extract visible text from a screenshot.

    Args:
        screenshot_path: Path to the screenshot
        region: Optional region to focus on {x, y, width, height}

    Returns:
        Extracted text content
    """
    from sakhi.apps.api.core.llm import get_router

    image_data, media_type = await _load_and_compress_image(screenshot_path)
    if not image_data:
        return ""

    prompt = """Extract all readable text from this screenshot.

Return the text in reading order (top to bottom, left to right).
Preserve paragraph breaks with blank lines.
Include text from buttons, labels, menus, and body content.

Return ONLY the extracted text, no other commentary."""

    try:
        router = get_router()
        target_model = os.getenv("MODEL_VISION") or DEFAULT_VISION_MODEL
        image_url = f"data:{media_type};base64,{image_data}"

        response = await router.chat(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
            model=target_model,
            max_tokens=4000,
        )

        return response.content[0].text if response.content else ""

    except Exception as e:
        LOGGER.exception("[screen_analyzer] Text extraction failed: %s", e)
        return ""


async def detect_page_type(
    screenshot_path: str,
) -> Dict[str, Any]:
    """
    Detect what type of page/screen this is.

    Returns:
        Page type classification with confidence
    """
    from sakhi.apps.api.core.llm import get_router

    image_data, media_type = await _load_and_compress_image(screenshot_path)
    if not image_data:
        return {"type": "unknown", "confidence": 0.0}

    prompt = """Classify this screenshot into one of these page types:

- search_results: A search engine results page
- restaurant_listing: A page showing multiple restaurants (Yelp, Google Maps, etc.)
- restaurant_detail: A single restaurant's detail page
- menu: A restaurant menu
- reservation: A booking/reservation page
- login: A login or sign-up page
- map: A map view
- form: Any form to fill out
- article: An article or content page
- home: A website's home page
- product: A product detail page
- checkout: A shopping checkout page
- error: An error page (404, etc.)
- other: Anything else

Respond with JSON:
{{
    "type": "the_type",
    "subtype": "optional more specific type",
    "app": "detected app name if visible",
    "url": "URL if visible in address bar",
    "confidence": 0.0-1.0
}}

Return ONLY the JSON."""

    try:
        router = get_router()
        target_model = os.getenv("MODEL_VISION") or DEFAULT_VISION_MODEL
        image_url = f"data:{media_type};base64,{image_data}"

        response = await router.chat(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
            model=target_model,
            max_tokens=300,
        )

        content = response.content[0].text if response.content else "{}"
        return _parse_json_response(content)

    except Exception as e:
        LOGGER.exception("[screen_analyzer] Page type detection failed: %s", e)
        return {"type": "unknown", "confidence": 0.0, "error": str(e)}


# =============================================================================
# Helper Functions
# =============================================================================

async def _load_and_compress_image(
    path: str,
    max_dimension: int = MAX_IMAGE_DIMENSION,
) -> tuple[Optional[str], str]:
    """
    Load an image file, optionally compress it, and convert to base64.

    Returns:
        Tuple of (base64_data, media_type) or (None, "") on error.
    """
    try:
        file_path = Path(path)
        if not file_path.exists():
            LOGGER.error("[screen_analyzer] Image not found: %s", path)
            return None, ""

        media_type = _get_media_type(path)

        # Try to compress with PIL if available
        try:
            from PIL import Image

            with Image.open(file_path) as img:
                original_size = img.size
                # Check if compression needed
                if img.width > max_dimension or img.height > max_dimension:
                    # Calculate new size maintaining aspect ratio
                    ratio = min(max_dimension / img.width, max_dimension / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                    LOGGER.info(
                        "[screen_analyzer] Compressed image %s -> %s",
                        original_size, new_size,
                    )

                # Convert to bytes
                buffer = io.BytesIO()
                # Use JPEG for better compression (unless PNG has transparency)
                if img.mode == "RGBA":
                    img.save(buffer, format="PNG", optimize=True)
                    media_type = "image/png"
                else:
                    # Convert to RGB if needed for JPEG
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    img.save(buffer, format="JPEG", quality=85, optimize=True)
                    media_type = "image/jpeg"

                buffer.seek(0)
                return base64.b64encode(buffer.read()).decode("utf-8"), media_type

        except ImportError:
            # PIL not available, load raw file
            LOGGER.debug("[screen_analyzer] PIL not available, loading raw image")
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8"), media_type

    except Exception as e:
        LOGGER.exception("[screen_analyzer] Failed to load image: %s", e)
        return None, ""


async def _load_image_base64(path: str) -> Optional[str]:
    """Load an image file and convert to base64 (legacy, use _load_and_compress_image)."""
    data, _ = await _load_and_compress_image(path)
    return data


def _get_media_type(path: str) -> str:
    """Get media type from file extension."""
    ext = Path(path).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "image/png")


def _build_analysis_prompt(
    task_context: Optional[str],
    previous_actions: Optional[List[Dict[str, Any]]],
    width: int,
    height: int,
) -> str:
    """Build the screen analysis prompt."""
    prompt = f"""Analyze this screenshot ({width}x{height} pixels) and provide a structured understanding of what's visible.

"""
    if task_context:
        prompt += f"""The user is trying to: {task_context}

"""

    if previous_actions:
        prompt += "Recent actions taken:\n"
        for action in previous_actions[-3:]:
            prompt += f"  - {action.get('type', '?')}: {action.get('reasoning', '')}\n"
        prompt += "\n"

    prompt += """Provide your analysis as JSON:
{
    "description": "Brief description of what's on screen",
    "page_type": "search_results|restaurant_listing|restaurant_detail|menu|form|map|article|other",
    "app": "Name of the application if identifiable",
    "url": "URL if visible in address bar",
    "text": "Key text content visible (summarized if long)",
    "elements": [
        {
            "type": "button|link|input|text|image|menu|other",
            "text": "visible label or text",
            "x": center_x,
            "y": center_y,
            "width": approximate_width,
            "height": approximate_height,
            "actionable": true/false,
            "relevance": "high|medium|low based on task"
        }
    ],
    "task_relevant": {
        "found_target": true/false,
        "next_suggested_action": "what to do next",
        "blockers": ["any issues preventing progress"]
    },
    "confidence": 0.0-1.0
}

Focus on elements relevant to the task. For actionable elements, provide accurate coordinates for clicking.
Return ONLY the JSON, no other text."""

    return prompt


def _parse_analysis_response(content: str) -> Dict[str, Any]:
    """Parse Claude's analysis response."""
    return _parse_json_response(content)


def _parse_json_response(content: str) -> Dict[str, Any]:
    """Parse a JSON response, handling markdown code blocks."""
    try:
        # Strip markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return json.loads(content.strip())
    except json.JSONDecodeError as e:
        LOGGER.warning("[screen_analyzer] JSON parse error: %s", e)
        return {"error": "Failed to parse response", "raw": content[:500]}


def _empty_analysis(error: Optional[str] = None) -> Dict[str, Any]:
    """Return an empty analysis result."""
    result = {
        "description": "",
        "page_type": "unknown",
        "elements": [],
        "text": "",
        "confidence": 0.0,
    }
    if error:
        result["error"] = error
    return result


__all__ = [
    "analyze_screen",
    "analyze_screen_for_element",
    "extract_text_from_screen",
    "detect_page_type",
]
