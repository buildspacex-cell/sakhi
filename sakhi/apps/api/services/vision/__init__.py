"""
Sakhi Vision Service
--------------------
Multi-modal understanding for Sakhi.

Enables Sakhi to:
- Understand images and screenshots
- Parse documents (PDF, receipts, etc.)
- Learn from visual content
- Maintain visual context in conversations
- Link media to journal entries for recall
- Generate insights from visual patterns
"""

from sakhi.apps.api.services.vision.processor import (
    process_image,
    analyze_screenshot,
    describe_image,
    extract_text_from_image,
    ImageAnalysis,
    ScreenshotAnalysis,
)

from sakhi.apps.api.services.vision.documents import (
    parse_document,
    extract_receipt_data,
    extract_document_structure,
    ParsedDocument,
    ReceiptData,
)

from sakhi.apps.api.services.vision.storage import (
    store_media,
    get_media,
    get_media_bytes,
    delete_media,
    get_media_url,
    update_media_analysis,
    get_recent_media,
    link_media_to_entry,
    get_entry_media,
    link_media_to_memory,
    search_media_by_content,
    MediaRecord,
)

from sakhi.apps.api.services.vision.context import (
    add_to_visual_context,
    get_visual_context,
    update_visual_summary,
    clear_visual_context,
    get_session_media,
    get_relevant_media_for_context,
    VisualContext,
    VisualContextItem,
)

from sakhi.apps.api.services.vision.memory import (
    learn_from_image,
    recall_visual_memory,
    search_visual_memory,
    get_visual_memory_summary,
    generate_visual_insight,
    get_visual_insights,
    VisualMemory,
    LearnedFact,
)

__all__ = [
    # Processing
    "process_image",
    "analyze_screenshot",
    "describe_image",
    "extract_text_from_image",
    "ImageAnalysis",
    "ScreenshotAnalysis",
    # Documents
    "parse_document",
    "extract_receipt_data",
    "extract_document_structure",
    "ParsedDocument",
    "ReceiptData",
    # Storage
    "store_media",
    "get_media",
    "get_media_bytes",
    "delete_media",
    "get_media_url",
    "update_media_analysis",
    "get_recent_media",
    "link_media_to_entry",
    "get_entry_media",
    "link_media_to_memory",
    "search_media_by_content",
    "MediaRecord",
    # Context
    "add_to_visual_context",
    "get_visual_context",
    "update_visual_summary",
    "clear_visual_context",
    "get_session_media",
    "get_relevant_media_for_context",
    "VisualContext",
    "VisualContextItem",
    # Memory & Insights
    "learn_from_image",
    "recall_visual_memory",
    "search_visual_memory",
    "get_visual_memory_summary",
    "generate_visual_insight",
    "get_visual_insights",
    "VisualMemory",
    "LearnedFact",
]
