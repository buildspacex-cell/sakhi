"""
Vision API Routes
-----------------
Endpoints for image/document upload and analysis.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

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
    ParsedDocument,
    ReceiptData,
)
from sakhi.apps.api.services.vision.storage import (
    store_media,
    get_media,
    get_media_bytes,
    delete_media,
    update_media_analysis,
    get_recent_media,
    MediaRecord,
)
from sakhi.apps.api.services.vision.context import (
    add_to_visual_context,
    get_visual_context,
    get_session_media,
    get_relevant_media_for_context,
)
from sakhi.apps.api.services.vision.memory import (
    learn_from_image,
    recall_visual_memory,
    search_visual_memory,
    get_visual_memory_summary,
)

router = APIRouter(prefix="/api/v1/vision", tags=["vision"])
LOGGER = logging.getLogger(__name__)


# =============================================================================
# Request/Response Models
# =============================================================================

class UploadResponse(BaseModel):
    """Response from media upload."""
    media_id: str
    status: str
    message: str


class AnalyzeResponse(BaseModel):
    """Response from image analysis."""
    media_id: str
    analysis: Dict[str, Any]
    description: str
    extracted_text: Optional[str] = None


class ContextResponse(BaseModel):
    """Visual context response."""
    session_id: str
    active_media: List[Dict[str, Any]]
    visual_summary: Optional[str] = None


class MemoryResponse(BaseModel):
    """Visual memory response."""
    memories: List[Dict[str, Any]]
    total: int


# =============================================================================
# Upload & Storage Endpoints
# =============================================================================

@router.post("/upload", response_model=UploadResponse)
async def upload_media(
    file: UploadFile = File(...),
    person_id: str = Form(...),
    media_type: str = Form("image"),
    source: str = Form("upload"),
    context: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    analyze: bool = Form(True),
):
    """
    Upload an image or document.

    Args:
        file: The file to upload
        person_id: User ID
        media_type: 'image', 'document', 'screenshot'
        source: 'upload', 'camera', 'screenshot', 'share'
        context: User's note about what this is
        session_id: Conversation session to add to
        analyze: Whether to analyze immediately
    """
    # Validate file type
    if not file.content_type:
        raise HTTPException(400, "Missing content type")

    allowed_types = [
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "application/pdf",
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    # Read file
    file_bytes = await file.read()

    # Store media
    record = await store_media(
        person_id=person_id,
        media_bytes=file_bytes,
        mime_type=file.content_type,
        media_type=media_type,
        filename=file.filename,
        source=source,
        context=context,
    )

    # Analyze if requested
    if analyze:
        try:
            if media_type == "screenshot":
                analysis_result = await analyze_screenshot(
                    file_bytes,
                    mime_type=file.content_type,
                )
                analysis_dict = analysis_result.model_dump()
            else:
                analysis_result = await process_image(
                    file_bytes,
                    mime_type=file.content_type,
                    context=context,
                )
                analysis_dict = analysis_result.model_dump()

            # Update record with analysis
            await update_media_analysis(
                media_id=record.id,
                description=analysis_dict.get("description", ""),
                extracted_text=analysis_dict.get("extracted_text"),
                analysis=analysis_dict,
            )

            # Learn from the image
            await learn_from_image(
                person_id=person_id,
                media_id=record.id,
                analysis=analysis_dict,
                description=analysis_dict.get("description", ""),
            )

        except Exception as e:
            LOGGER.error("[vision] Analysis failed: %s", e)

    # Add to session context if provided
    if session_id:
        await add_to_visual_context(
            person_id=person_id,
            session_id=session_id,
            media_id=record.id,
            description=context or "Uploaded image",
        )

    LOGGER.info(
        "[vision] Uploaded media %s for person %s (type=%s)",
        record.id,
        person_id,
        media_type,
    )

    return UploadResponse(
        media_id=record.id,
        status="processing" if analyze else "stored",
        message="Media uploaded successfully",
    )


@router.get("/media/{media_id}")
async def get_media_file(media_id: str):
    """Get raw media file by ID."""
    media_bytes = await get_media_bytes(media_id)
    if not media_bytes:
        raise HTTPException(404, "Media not found")

    record = await get_media(media_id)
    if not record:
        raise HTTPException(404, "Media record not found")

    return Response(
        content=media_bytes,
        media_type=record.mime_type,
    )


@router.get("/media/{media_id}/info")
async def get_media_info(media_id: str):
    """Get media metadata and analysis."""
    record = await get_media(media_id)
    if not record:
        raise HTTPException(404, "Media not found")

    return record.model_dump()


@router.delete("/media/{media_id}")
async def delete_media_endpoint(media_id: str, person_id: str):
    """Delete a media file."""
    record = await get_media(media_id)
    if not record:
        raise HTTPException(404, "Media not found")

    if record.person_id != person_id:
        raise HTTPException(403, "Not authorized")

    await delete_media(media_id)
    return {"status": "deleted", "media_id": media_id}


@router.get("/recent")
async def get_recent_media_endpoint(
    person_id: str,
    limit: int = Query(10, le=50),
    media_type: Optional[str] = None,
):
    """Get recent media for a person."""
    media = await get_recent_media(
        person_id=person_id,
        limit=limit,
        media_type=media_type,
    )
    return {"media": [m.model_dump() for m in media]}


# =============================================================================
# Analysis Endpoints
# =============================================================================

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_media(
    file: UploadFile = File(...),
    person_id: str = Form(...),
    context: Optional[str] = Form(None),
):
    """
    Analyze an image without storing it.

    Returns analysis results immediately.
    """
    file_bytes = await file.read()

    analysis = await process_image(
        file_bytes,
        mime_type=file.content_type or "image/png",
        context=context,
    )

    return AnalyzeResponse(
        media_id="transient",
        analysis=analysis.model_dump(),
        description=analysis.description,
        extracted_text=analysis.extracted_text,
    )


@router.post("/analyze/screenshot")
async def analyze_screenshot_endpoint(
    file: UploadFile = File(...),
    question: Optional[str] = Form(None),
):
    """Analyze a screenshot."""
    file_bytes = await file.read()

    analysis = await analyze_screenshot(
        file_bytes,
        mime_type=file.content_type or "image/png",
        user_question=question,
    )

    return analysis.model_dump()


@router.post("/analyze/receipt")
async def analyze_receipt(
    file: UploadFile = File(...),
):
    """Extract structured data from a receipt."""
    file_bytes = await file.read()

    receipt = await extract_receipt_data(
        file_bytes,
        mime_type=file.content_type or "image/png",
    )

    return receipt.model_dump()


@router.post("/analyze/document")
async def analyze_document(
    file: UploadFile = File(...),
):
    """Parse and analyze a document."""
    file_bytes = await file.read()

    doc = await parse_document(
        file_bytes,
        mime_type=file.content_type or "image/png",
    )

    return doc.model_dump()


@router.post("/describe")
async def describe_image_endpoint(
    file: UploadFile = File(...),
    style: str = Form("concise"),
):
    """Get natural language description of an image."""
    file_bytes = await file.read()

    description = await describe_image(
        file_bytes,
        mime_type=file.content_type or "image/png",
        style=style,
    )

    return {"description": description}


@router.post("/extract-text")
async def extract_text_endpoint(
    file: UploadFile = File(...),
):
    """Extract text from an image (OCR)."""
    file_bytes = await file.read()

    text = await extract_text_from_image(
        file_bytes,
        mime_type=file.content_type or "image/png",
    )

    return {"text": text}


# =============================================================================
# Context Endpoints
# =============================================================================

@router.get("/context/{session_id}")
async def get_context(
    session_id: str,
    person_id: str,
):
    """Get visual context for a conversation session."""
    context = await get_visual_context(person_id, session_id)
    if not context:
        return ContextResponse(
            session_id=session_id,
            active_media=[],
        )

    return ContextResponse(
        session_id=session_id,
        active_media=[m.model_dump() for m in context.active_media],
        visual_summary=context.visual_summary,
    )


@router.get("/context/{session_id}/media")
async def get_session_media_endpoint(session_id: str):
    """Get all media shared in a session."""
    media = await get_session_media(session_id)
    return {"media": media}


@router.get("/context/{session_id}/relevant")
async def get_relevant_context(
    session_id: str,
    person_id: str,
    max_items: int = Query(3, le=10),
):
    """Get most relevant media for LLM context."""
    media = await get_relevant_media_for_context(
        person_id=person_id,
        session_id=session_id,
        max_items=max_items,
    )
    return {"media": media}


# =============================================================================
# Memory Endpoints
# =============================================================================

@router.get("/memory", response_model=MemoryResponse)
async def get_visual_memories(
    person_id: str,
    memory_type: Optional[str] = None,
    subject: Optional[str] = None,
    min_confidence: float = Query(0.3, ge=0, le=1),
    limit: int = Query(20, le=100),
):
    """Recall visual memories."""
    memories = await recall_visual_memory(
        person_id=person_id,
        memory_type=memory_type,
        subject=subject,
        min_confidence=min_confidence,
        limit=limit,
    )

    return MemoryResponse(
        memories=[m.model_dump() for m in memories],
        total=len(memories),
    )


@router.get("/memory/search")
async def search_memories(
    person_id: str,
    q: str,
    limit: int = Query(10, le=50),
):
    """Search visual memories."""
    results = await search_visual_memory(
        person_id=person_id,
        query=q,
        limit=limit,
    )
    return {"results": results}


@router.get("/memory/summary")
async def get_memory_summary(person_id: str):
    """Get summary of visual memories."""
    summary = await get_visual_memory_summary(person_id)
    return summary


__all__ = ["router"]
