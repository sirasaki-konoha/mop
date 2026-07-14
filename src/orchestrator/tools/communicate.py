from __future__ import annotations

import dataclasses
import logging
from typing import Optional

from orchestrator.models.agent import Message, MessageType

logger = logging.getLogger(__name__)

VALID_MESSAGE_TYPES = ("request", "response", "review", "question")


class MessageStore:
    def __init__(self) -> None:
        self._messages: list[Message] = []

    def add(self, message: Message) -> Message:
        self._messages.append(message)
        logger.info(
            "Message stored: %s from=%s to=%s type=%s",
            message.id, message.from_agent, message.to_agent, message.message_type,
        )
        return message

    def get_inbox(self, agent_id: str) -> list[Message]:
        return [m for m in self._messages if m.to_agent == agent_id]

    def get_sent(self, agent_id: str) -> list[Message]:
        return [m for m in self._messages if m.from_agent == agent_id]

    def get_by_task(self, task_id: str) -> list[Message]:
        return [m for m in self._messages if m.task_id == task_id]

    def list_all(self) -> list[Message]:
        return list(self._messages)


_message_store: Optional[MessageStore] = None


def get_message_store() -> MessageStore:
    global _message_store
    if _message_store is None:
        _message_store = MessageStore()
        logger.info("MessageStore initialized")
    return _message_store


def _message_to_dict(message: Message) -> dict:
    return {
        "id": message.id,
        "from_agent": message.from_agent,
        "to_agent": message.to_agent,
        "message_type": message.message_type.value
            if isinstance(message.message_type, MessageType)
            else message.message_type,
        "content": message.content,
        "task_id": message.task_id,
        "created_at": message.created_at.isoformat(),
    }


async def agent_communicate(
    from_agent: str,
    to_agent: str,
    message_type: str,
    content: str,
    task_id: Optional[str] = None,
) -> dict:
    if not from_agent or not from_agent.strip():
        raise ValueError("from_agent must not be empty")
    if not to_agent or not to_agent.strip():
        raise ValueError("to_agent must not be empty")
    if message_type not in VALID_MESSAGE_TYPES:
        raise ValueError(
            f"Invalid message_type: {message_type!r}. Must be one of {VALID_MESSAGE_TYPES}"
        )
    if not content or not content.strip():
        raise ValueError("content must not be empty")

    import uuid
    from datetime import datetime, timezone

    message = Message(
        id=str(uuid.uuid4()),
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=MessageType(message_type),
        content=content,
        task_id=task_id,
        created_at=datetime.now(timezone.utc),
    )

    store = get_message_store()
    store.add(message)

    logger.info(
        "Message sent: %s -> %s [%s] (task=%s)",
        from_agent, to_agent, message_type, task_id,
    )

    return _message_to_dict(message)
