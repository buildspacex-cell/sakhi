"""
Document Parser
---------------
Parse and extract structured data from documents.
"""

from __future__ import annotations

import base64
import logging
import json
from typing import Any, Dict, List, Optional
from pathlib import Path

from pydantic import BaseModel

LOGGER = logging.getLogger(__name__)


class DocumentPage(BaseModel):
    """Content from a single page."""
    page_number: int
    text: str
    tables: List[Dict[str, Any]] = []
    has_images: bool = False


class ParsedDocument(BaseModel):
    """Result of document parsing."""
    title: Optional[str] = None
    document_type: Optional[str] = None  # 'receipt', 'invoice', 'contract', 'note', etc.
    full_text: str = ""
    pages: List[DocumentPage] = []
    extracted_data: Dict[str, Any] = {}
    summary: Optional[str] = None
    confidence: float = 0.8


class ReceiptData(BaseModel):
    """Structured receipt data."""
    vendor: Optional[str] = None
    date: Optional[str] = None
    items: List[Dict[str, Any]] = []
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    payment_method: Optional[str] = None
    currency: str = "USD"
    raw_text: Optional[str] = None


async def parse_document(
    document_source: str | bytes,
    mime_type: str = "application/pdf",
    extract_tables: bool = True,
) -> ParsedDocument:
    """
    Parse a document and extract content.

    Supports:
    - PDF (as images)
    - Images of documents
    - Screenshots of documents
    """
    from sakhi.apps.api.core.llm import get_router

    # For PDFs, we'd need to convert to images first
    # For now, handle image-based documents

    if isinstance(document_source, str):
        path = Path(document_source)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            # PDF handling - would need pdf2image or similar
            LOGGER.warning("[documents] PDF support requires pdf2image library")
            return ParsedDocument(
                full_text="PDF parsing not yet implemented",
                confidence=0.0,
            )

        # Image-based document
        media_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
        }
        media_type = media_type_map.get(suffix, "image/png")

        with open(document_source, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    else:
        image_data = base64.standard_b64encode(document_source).decode("utf-8")
        media_type = mime_type

    prompt = """Analyze this document image and extract all information.

Return a JSON object with:
{
    "title": "Document title if visible",
    "document_type": "receipt/invoice/contract/letter/form/note/other",
    "full_text": "Complete text from the document",
    "tables": [
        {"headers": [...], "rows": [[...], [...]]}
    ],
    "extracted_data": {
        // Structured data based on document type
        // For receipts: vendor, date, items, total
        // For invoices: invoice_number, due_date, line_items, amount_due
        // For contracts: parties, effective_date, key_terms
    },
    "summary": "Brief summary of document purpose"
}

Return ONLY valid JSON."""

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
            max_tokens=3000,
        )

        content = response.content[0].text if response.content else "{}"

        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

            # Build pages from response
            pages = []
            if data.get("full_text"):
                pages.append(DocumentPage(
                    page_number=1,
                    text=data["full_text"],
                    tables=data.get("tables", []),
                ))

            return ParsedDocument(
                title=data.get("title"),
                document_type=data.get("document_type"),
                full_text=data.get("full_text", ""),
                pages=pages,
                extracted_data=data.get("extracted_data", {}),
                summary=data.get("summary"),
            )

        except json.JSONDecodeError:
            return ParsedDocument(
                full_text=content[:2000],
                confidence=0.5,
            )

    except Exception as e:
        LOGGER.error("[documents] Document parsing failed: %s", e)
        return ParsedDocument(confidence=0.0)


async def extract_receipt_data(
    image_source: str | bytes,
    mime_type: str = "image/png",
) -> ReceiptData:
    """
    Extract structured data from a receipt image.
    """
    from sakhi.apps.api.core.llm import get_router

    if isinstance(image_source, str):
        path = Path(image_source)
        suffix = path.suffix.lower()
        media_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
        }.get(suffix, "image/png")

        with open(image_source, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    else:
        image_data = base64.standard_b64encode(image_source).decode("utf-8")
        media_type = mime_type

    prompt = """Extract receipt information from this image.

Return a JSON object with:
{
    "vendor": "Store/restaurant name",
    "date": "YYYY-MM-DD format if visible",
    "items": [
        {"name": "Item description", "quantity": 1, "price": 10.99}
    ],
    "subtotal": 10.99,
    "tax": 0.88,
    "total": 11.87,
    "payment_method": "Visa ****1234" or "Cash" etc,
    "currency": "USD",
    "raw_text": "Full text from receipt"
}

Return ONLY valid JSON. Use null for fields not visible."""

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

        content = response.content[0].text if response.content else "{}"

        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())
            return ReceiptData(**data)

        except json.JSONDecodeError:
            return ReceiptData(raw_text=content[:1000])

    except Exception as e:
        LOGGER.error("[documents] Receipt extraction failed: %s", e)
        return ReceiptData()


async def extract_document_structure(
    document_source: str | bytes,
    mime_type: str = "image/png",
) -> Dict[str, Any]:
    """
    Extract high-level document structure.

    Returns:
        Dict with sections, headings, key points
    """
    from sakhi.apps.api.core.llm import get_router

    if isinstance(document_source, str):
        path = Path(document_source)
        media_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
        }.get(path.suffix.lower(), "image/png")

        with open(document_source, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    else:
        image_data = base64.standard_b64encode(document_source).decode("utf-8")
        media_type = mime_type

    prompt = """Analyze the structure of this document.

Return a JSON object with:
{
    "type": "letter/report/form/article/other",
    "sections": [
        {"heading": "Section name", "summary": "Brief content summary"}
    ],
    "key_points": ["Main point 1", "Main point 2"],
    "action_items": ["Any todos or action items mentioned"],
    "dates_mentioned": ["YYYY-MM-DD"],
    "people_mentioned": ["Name 1", "Name 2"],
    "organizations_mentioned": ["Org 1", "Org 2"]
}

Return ONLY valid JSON."""

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
            max_tokens=1500,
        )

        content = response.content[0].text if response.content else "{}"

        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())

        except json.JSONDecodeError:
            return {"error": "Failed to parse structure", "raw": content[:500]}

    except Exception as e:
        LOGGER.error("[documents] Structure extraction failed: %s", e)
        return {"error": str(e)}


__all__ = [
    "DocumentPage",
    "ParsedDocument",
    "ReceiptData",
    "parse_document",
    "extract_receipt_data",
    "extract_document_structure",
]
