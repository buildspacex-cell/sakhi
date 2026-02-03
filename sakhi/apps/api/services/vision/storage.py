"""
Media Storage Service
---------------------
Store and retrieve media files (images, documents).
"""

from __future__ import annotations

import logging
import os
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec

LOGGER = logging.getLogger(__name__)

# Storage configuration
STORAGE_ROOT = os.getenv("MEDIA_STORAGE_PATH", "/tmp/sakhi/media")
STORAGE_PROVIDER = os.getenv("MEDIA_STORAGE_PROVIDER", "local")


class MediaRecord(BaseModel):
    """Database record for media."""
    id: str
    person_id: str
    media_type: str
    mime_type: str
    filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    storage_provider: str
    storage_path: str
    thumbnail_path: Optional[str] = None
    extracted_text: Optional[str] = None
    description: Optional[str] = None
    analysis: Dict[str, Any] = {}
    source: Optional[str] = None
    context: Optional[str] = None
    status: str = "pending"
    width: Optional[int] = None
    height: Optional[int] = None


def _get_storage_path(person_id: str, media_id: str, extension: str) -> str:
    """Generate storage path for a media file."""
    # Organize by person_id and date
    date_prefix = datetime.now().strftime("%Y/%m")
    return f"{person_id}/{date_prefix}/{media_id}{extension}"


def _ensure_directory(path: str) -> None:
    """Ensure directory exists."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _get_extension(mime_type: str) -> str:
    """Get file extension from MIME type."""
    extensions = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
        "text/plain": ".txt",
    }
    return extensions.get(mime_type, ".bin")


async def store_media(
    person_id: str,
    media_bytes: bytes,
    mime_type: str,
    media_type: str = "image",
    filename: Optional[str] = None,
    source: str = "upload",
    context: Optional[str] = None,
) -> MediaRecord:
    """
    Store a media file and create database record.

    Args:
        person_id: Owner of the media
        media_bytes: Raw file bytes
        mime_type: MIME type (image/png, etc.)
        media_type: Category (image, document, screenshot)
        filename: Original filename
        source: How it was received (upload, camera, screenshot, share)
        context: User's note about what this is

    Returns:
        MediaRecord with storage info
    """
    import json

    media_id = str(uuid.uuid4())
    extension = _get_extension(mime_type)
    storage_path = _get_storage_path(person_id, media_id, extension)

    # Store file locally
    if STORAGE_PROVIDER == "local":
        full_path = os.path.join(STORAGE_ROOT, storage_path)
        _ensure_directory(full_path)

        with open(full_path, "wb") as f:
            f.write(media_bytes)

        LOGGER.info("[storage] Stored media locally: %s", storage_path)

    # TODO: Add S3/GCS support
    # elif STORAGE_PROVIDER == "s3":
    #     ...

    # Get image dimensions if applicable
    width, height = None, None
    if mime_type.startswith("image/"):
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(media_bytes))
            width, height = img.size
        except Exception:
            pass

    # Create database record
    row = await dbfetch(
        """
        INSERT INTO media_attachments (
            id, person_id, media_type, mime_type, filename,
            file_size_bytes, storage_provider, storage_path,
            source, context, status, width, height
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'pending', $11, $12)
        RETURNING *
        """,
        media_id,
        person_id,
        media_type,
        mime_type,
        filename,
        len(media_bytes),
        STORAGE_PROVIDER,
        storage_path,
        source,
        context,
        width,
        height,
        one=True,
    )

    LOGGER.info("[storage] Created media record: %s for person %s", media_id, person_id)

    return MediaRecord(
        id=str(row["id"]),
        person_id=row["person_id"],
        media_type=row["media_type"],
        mime_type=row["mime_type"],
        filename=row.get("filename"),
        file_size_bytes=row.get("file_size_bytes"),
        storage_provider=row["storage_provider"],
        storage_path=row["storage_path"],
        source=row.get("source"),
        context=row.get("context"),
        status=row["status"],
        width=row.get("width"),
        height=row.get("height"),
    )


async def get_media(media_id: str) -> Optional[MediaRecord]:
    """Get media record by ID."""
    row = await dbfetch(
        "SELECT * FROM media_attachments WHERE id = $1",
        media_id,
        one=True,
    )

    if not row:
        return None

    return MediaRecord(
        id=str(row["id"]),
        person_id=row["person_id"],
        media_type=row["media_type"],
        mime_type=row["mime_type"],
        filename=row.get("filename"),
        file_size_bytes=row.get("file_size_bytes"),
        storage_provider=row["storage_provider"],
        storage_path=row["storage_path"],
        thumbnail_path=row.get("thumbnail_path"),
        extracted_text=row.get("extracted_text"),
        description=row.get("description"),
        analysis=row.get("analysis") or {},
        source=row.get("source"),
        context=row.get("context"),
        status=row["status"],
        width=row.get("width"),
        height=row.get("height"),
    )


async def get_media_bytes(media_id: str) -> Optional[bytes]:
    """Get raw media file bytes."""
    record = await get_media(media_id)
    if not record:
        return None

    if record.storage_provider == "local":
        full_path = os.path.join(STORAGE_ROOT, record.storage_path)
        if os.path.exists(full_path):
            with open(full_path, "rb") as f:
                return f.read()

    return None


def get_media_url(media_record: MediaRecord, base_url: Optional[str] = None) -> str:
    """
    Get URL to access media.

    For local storage, returns a path that should be served by the API.
    For cloud storage, returns a signed URL or public URL.
    """
    if media_record.storage_provider == "local":
        base = base_url or "/api/v1/vision/media"
        return f"{base}/{media_record.id}"

    # TODO: Generate signed URLs for S3/GCS
    return f"/api/v1/vision/media/{media_record.id}"


async def delete_media(media_id: str) -> bool:
    """Delete media file and record."""
    record = await get_media(media_id)
    if not record:
        return False

    # Delete file
    if record.storage_provider == "local":
        full_path = os.path.join(STORAGE_ROOT, record.storage_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            LOGGER.info("[storage] Deleted media file: %s", full_path)

    # Delete record
    await dbexec(
        "DELETE FROM media_attachments WHERE id = $1",
        media_id,
    )

    LOGGER.info("[storage] Deleted media record: %s", media_id)
    return True


async def update_media_analysis(
    media_id: str,
    description: Optional[str] = None,
    extracted_text: Optional[str] = None,
    analysis: Optional[Dict[str, Any]] = None,
) -> bool:
    """Update media with analysis results."""
    import json

    updates = ["status = 'ready'", "processed_at = NOW()"]
    params = []
    param_idx = 1

    if description is not None:
        updates.append(f"description = ${param_idx}")
        params.append(description)
        param_idx += 1

    if extracted_text is not None:
        updates.append(f"extracted_text = ${param_idx}")
        params.append(extracted_text)
        param_idx += 1

    if analysis is not None:
        updates.append(f"analysis = ${param_idx}::jsonb")
        params.append(json.dumps(analysis))
        param_idx += 1

    params.append(media_id)

    query = f"""
        UPDATE media_attachments
        SET {', '.join(updates)}
        WHERE id = ${param_idx}
    """

    await dbexec(query, *params)
    return True


async def get_recent_media(
    person_id: str,
    limit: int = 10,
    media_type: Optional[str] = None,
) -> list[MediaRecord]:
    """Get recent media for a person."""
    query = """
        SELECT * FROM media_attachments
        WHERE person_id = $1 AND status = 'ready'
    """
    params = [person_id]

    if media_type:
        query += " AND media_type = $2"
        params.append(media_type)

    query += f" ORDER BY created_at DESC LIMIT {limit}"

    rows = await dbfetch(query, *params)

    return [
        MediaRecord(
            id=str(row["id"]),
            person_id=row["person_id"],
            media_type=row["media_type"],
            mime_type=row["mime_type"],
            filename=row.get("filename"),
            file_size_bytes=row.get("file_size_bytes"),
            storage_provider=row["storage_provider"],
            storage_path=row["storage_path"],
            description=row.get("description"),
            analysis=row.get("analysis") or {},
            status=row["status"],
        )
        for row in (rows or [])
    ]


async def link_media_to_entry(
    media_id: str,
    entry_id: str,
    person_id: str,
    relationship: str = "attachment",
    caption: Optional[str] = None,
) -> bool:
    """
    Link a media file to a journal entry.

    Args:
        media_id: Media attachment ID
        entry_id: Journal entry ID
        person_id: User ID
        relationship: How media relates ('attachment', 'context', 'evidence', 'memory_trigger')
        caption: User's description for this context
    """
    # Get media record for searchable text
    record = await get_media(media_id)
    if not record:
        return False

    searchable_text = " ".join(filter(None, [
        record.description,
        record.extracted_text,
        caption,
    ]))

    await dbexec(
        """
        INSERT INTO journal_entry_media (
            entry_id, media_id, person_id, relationship, caption, searchable_text
        )
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT DO NOTHING
        """,
        entry_id,
        media_id,
        person_id,
        relationship,
        caption,
        searchable_text,
    )

    LOGGER.info("[storage] Linked media %s to entry %s", media_id, entry_id)
    return True


async def get_entry_media(entry_id: str) -> List[Dict[str, Any]]:
    """Get all media attached to a journal entry."""
    rows = await dbfetch(
        """
        SELECT
            m.id as media_id,
            m.media_type,
            m.mime_type,
            m.description,
            m.extracted_text,
            m.analysis,
            jem.caption,
            jem.relationship,
            jem.relevance_score
        FROM media_attachments m
        JOIN journal_entry_media jem ON jem.media_id = m.id
        WHERE jem.entry_id = $1
        ORDER BY jem.created_at
        """,
        entry_id,
    )

    return [
        {
            "media_id": str(row["media_id"]),
            "media_type": row["media_type"],
            "mime_type": row["mime_type"],
            "description": row.get("description"),
            "extracted_text": row.get("extracted_text"),
            "analysis": row.get("analysis") or {},
            "caption": row.get("caption"),
            "relationship": row.get("relationship"),
            "relevance_score": row.get("relevance_score", 1.0),
        }
        for row in (rows or [])
    ]


async def link_media_to_memory(
    media_id: str,
    memory_id: str,
    memory_layer: str = "short_term",
    visual_summary: Optional[str] = None,
    key_objects: Optional[List[str]] = None,
) -> bool:
    """Link a media file to a memory record."""
    import json

    await dbexec(
        """
        INSERT INTO memory_media_links (
            memory_id, media_id, memory_layer, visual_summary, key_objects
        )
        VALUES ($1, $2, $3, $4, $5::jsonb)
        ON CONFLICT DO NOTHING
        """,
        memory_id,
        media_id,
        memory_layer,
        visual_summary,
        json.dumps(key_objects or []),
    )

    return True


async def search_media_by_content(
    person_id: str,
    query: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Search media by description, extracted text, or analysis."""
    rows = await dbfetch(
        """
        SELECT
            id as media_id,
            media_type,
            description,
            extracted_text,
            analysis,
            created_at,
            CASE
                WHEN description ILIKE $2 THEN 'description'
                WHEN extracted_text ILIKE $2 THEN 'extracted_text'
                ELSE 'analysis'
            END as match_source
        FROM media_attachments
        WHERE person_id = $1
          AND status = 'ready'
          AND (
            description ILIKE $2
            OR extracted_text ILIKE $2
            OR analysis::text ILIKE $2
          )
        ORDER BY created_at DESC
        LIMIT $3
        """,
        person_id,
        f"%{query}%",
        limit,
    )

    return [
        {
            "media_id": str(row["media_id"]),
            "media_type": row["media_type"],
            "description": row.get("description"),
            "extracted_text": row.get("extracted_text"),
            "analysis": row.get("analysis") or {},
            "match_source": row.get("match_source"),
            "created_at": str(row["created_at"]),
        }
        for row in (rows or [])
    ]


__all__ = [
    "MediaRecord",
    "store_media",
    "get_media",
    "get_media_bytes",
    "get_media_url",
    "delete_media",
    "update_media_analysis",
    "get_recent_media",
    "link_media_to_entry",
    "get_entry_media",
    "link_media_to_memory",
    "search_media_by_content",
]
