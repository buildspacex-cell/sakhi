"""Hierarchical dialogue-state management utilities."""

from __future__ import annotations

import asyncio
import logging
import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sakhi.libs.schemas.db import get_async_pool

logger = logging.getLogger(__name__)


@dataclass
class DialogFrame:
    """Represents an individual conversational frame on the stack."""

    name: str
    status: str = "active"  # active | paused | completed
    slots: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()


@dataclass
class ConversationState:
    """Serializable state container wrapping a frame stack."""

    conversation_id: str
    user_id: Optional[str]
    frames: List[DialogFrame] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    last_user_message: Optional[str] = None
    last_assistant_message: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def peek(self) -> Optional[DialogFrame]:
        if not self.frames:
            return None
        return self.frames[-1]

    def push(self, frame: DialogFrame) -> DialogFrame:
        existing_top = self.peek()
        if existing_top and existing_top is not frame:
            existing_top.status = "paused"
            existing_top.touch()
        self.frames.append(frame)
        frame.status = "active"
        frame.touch()
        self.touch()
        return frame

    def ensure_active(self, name: str, *, slots: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None) -> DialogFrame:
        top = self.peek()
        if top and top.name == name and top.status == "active":
            if slots:
                top.slots.update(slots)
            if metadata:
                top.metadata.update(metadata)
            top.touch()
            self.touch()
            return top

        # Resume a paused frame if it matches by name, otherwise create new.
        for frame in reversed(self.frames):
            if frame.name == name:
                frame.status = "active"
                if slots:
                    frame.slots.update(slots)
                if metadata:
                    frame.metadata.update(metadata)
                frame.touch()
                existing_top = self.peek()
                if existing_top is not frame and existing_top:
                    existing_top.status = "paused"
                    existing_top.touch()
                self.frames.append(self.frames.pop(self.frames.index(frame)))
                self.touch()
                return frame

        new_frame = DialogFrame(name=name, slots=slots or {}, metadata=metadata or {})
        return self.push(new_frame)

    def complete_active(self, name: str) -> None:
        top = self.peek()
        if top and top.name == name:
            top.status = "completed"
            top.touch()
            self.touch()

    def pop_until(self, name: str) -> None:
        while self.frames and self.frames[-1].name != name:
            self.frames.pop()
        self.touch()

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def as_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "frames": [
                {
                    "name": frame.name,
                    "status": frame.status,
                    "slots": frame.slots,
                    "metadata": frame.metadata,
                    "created_at": frame.created_at,
                    "updated_at": frame.updated_at,
                }
                for frame in self.frames
            ],
            "context": self.context,
            "last_user_message": self.last_user_message,
            "last_assistant_message": self.last_assistant_message,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ConversationState":
        frames = []
        for raw in payload.get("frames", []):
            frames.append(
                DialogFrame(
                    name=raw.get("name", "unknown"),
                    status=raw.get("status", "active"),
                    slots=dict(raw.get("slots") or {}),
                    metadata=dict(raw.get("metadata") or {}),
                    created_at=raw.get("created_at") or datetime.now(timezone.utc).isoformat(),
                    updated_at=raw.get("updated_at") or datetime.now(timezone.utc).isoformat(),
                )
            )
        return cls(
            conversation_id=payload.get("conversation_id", ""),
            user_id=payload.get("user_id"),
            frames=frames,
            context=dict(payload.get("context") or {}),
            last_user_message=payload.get("last_user_message"),
            last_assistant_message=payload.get("last_assistant_message"),
            updated_at=payload.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        )


class ConversationStateStore:
    """Persistence helper backed by Postgres."""

    @staticmethod
    async def load(conversation_id: str, *, user_id: Optional[str] = None) -> ConversationState:
        try:
            pool = await get_async_pool()
            async with pool.acquire() as connection:
                row = await connection.fetchrow(
                    "SELECT state FROM dialog_states WHERE conversation_id = $1",
                    conversation_id,
                )
        except Exception as exc:  # pragma: no cover - table may be missing during rollout
            logger.debug("dialog_states load failed: conversation_id=%s error=%s", conversation_id, exc)
            return ConversationState(conversation_id=conversation_id, user_id=user_id)

        if row and row.get("state"):
            state_payload = dict(row["state"])
            if user_id:
                state_payload.setdefault("user_id", user_id)
            return ConversationState.from_dict(state_payload)
        return ConversationState(conversation_id=conversation_id, user_id=user_id)

    @staticmethod
    async def save(state: ConversationState) -> None:
        payload = state.as_dict()
        try:
            pool = await get_async_pool()
            async with pool.acquire() as connection:
                await connection.execute(
                    """
                    INSERT INTO dialog_states (conversation_id, user_id, state, updated_at)
                    VALUES ($1, $2, $3::jsonb, now())
                    ON CONFLICT (conversation_id)
                    DO UPDATE SET user_id = EXCLUDED.user_id,
                                  state = EXCLUDED.state,
                                  updated_at = now()
                    """,
                    state.conversation_id,
                    state.user_id,
                    payload,
                )
        except Exception as exc:  # pragma: no cover - tolerate store downtime during rollout
            logger.debug(
                "dialog_states save skipped: conversation_id=%s error=%s", state.conversation_id, exc
            )


class ConversationStateManager:
    """Facade for integrating dialogue-state tracking into request flow."""

    def __init__(self, conversation_id: str, *, user_id: Optional[str]) -> None:
        self._conversation_id = conversation_id
        self._user_id = user_id
        self._state: Optional[ConversationState] = None
        self._lock = asyncio.Lock()

    async def load(self) -> ConversationState:
        async with self._lock:
            if self._state is None:
                self._state = await ConversationStateStore.load(
                    self._conversation_id,
                    user_id=self._user_id,
                )
            return self._state

    async def ensure_frame(
        self,
        name: str,
        *,
        slots: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DialogFrame:
        state = await self.load()
        frame = state.ensure_active(name, slots=slots, metadata=metadata)
        await ConversationStateStore.save(state)
        return frame

    async def record_turn(
        self,
        *,
        user_message: Optional[str],
        assistant_message: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        state = await self.load()
        if user_message is not None:
            state.last_user_message = user_message
        if assistant_message is not None:
            state.last_assistant_message = assistant_message
        if metadata:
            state.context.setdefault("turns", []).append(metadata)
        state.touch()
        await ConversationStateStore.save(state)


async def mirror_outer_conversation_state(
    *,
    user_id: Optional[str],
    source_conversation_id: str,
    target_conversation_id: str,
    slots: Dict[str, Any],
    metadata: Dict[str, Any],
    user_message: Optional[str],
    assistant_message: Optional[str],
) -> None:
    """Replicate outer-intent frame and turn history to another conversation id."""

    if not user_id:
        return
    if not target_conversation_id or target_conversation_id == source_conversation_id:
        return

    target_manager = ConversationStateManager(target_conversation_id, user_id=user_id)
    await target_manager.ensure_frame(
        "outer_intent",
        slots=copy.deepcopy(slots),
        metadata=copy.deepcopy(metadata),
    )
    await target_manager.record_turn(
        user_message=user_message,
        assistant_message=assistant_message,
        metadata=copy.deepcopy(metadata),
    )
