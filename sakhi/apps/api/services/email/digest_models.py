"""
Email Digest LLM Output Models
-------------------------------
Pydantic schemas used as structured output targets for call_llm(schema=...).

These define what the LLM returns when analyzing email content.
All fields use defaults for resilience against LLM output variations.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class EmailTriageItem(BaseModel):
    """LLM output: triage classification for a single email."""
    message_id: str = Field("", description="The email message ID")
    subject: str = Field("", description="Email subject line")
    sender: str = Field("", description="Sender email address")
    sender_name: Optional[str] = Field(None, description="Sender display name")

    # Triage classification
    triage: str = Field(
        "noise",
        description="Classification: 'action' (needs reply/action), 'fyi' (worth knowing), 'noise' (skip)"
    )

    # For action items
    action_summary: Optional[str] = Field(None, description="What action is needed")
    deadline: Optional[str] = Field(None, description="Deadline if mentioned")
    priority: str = Field("medium", description="Priority: high/medium/low")
    draft_reply: Optional[str] = Field(None, description="Suggested brief reply")

    # For FYI items
    one_line_summary: Optional[str] = Field(None, description="One-line summary")


class EmailCommitment(BaseModel):
    """LLM output: a commitment the user made in a sent email."""
    commitment: str = Field("", description="What the user promised")
    deadline: Optional[str] = Field(None, description="When it's due")
    subject: str = Field("", description="Email subject")
    recipient: str = Field("", description="Who the user committed to")
    commitment_type: str = Field(
        "people",
        description="'people' for promises to real people, 'subscription' for membership/renewal/billing"
    )


class EmailBatchAnalysis(BaseModel):
    """LLM output: analysis of a batch of emails."""
    items: List[EmailTriageItem] = Field(
        default_factory=list,
        description="Triage result for each email in the batch"
    )
    commitments: List[EmailCommitment] = Field(
        default_factory=list,
        description="Commitments found in sent emails (only for outgoing messages)"
    )


__all__ = [
    "EmailTriageItem",
    "EmailCommitment",
    "EmailBatchAnalysis",
]
