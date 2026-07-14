from __future__ import annotations

import asyncio
import logging
from typing import Optional

from orchestrator.models.agent import Message, MessageType

logger = logging.getLogger(__name__)

VALID_MESSAGE_TYPES = ("request", "response", "review", "question")


class MessageStore:
    def __init__(self) -> None:
        self._messages: list[Message] = []
        self._new_message = asyncio.Condition()

    def add(self, message: Message) -> Message:
        self._messages.append(message)
        logger.info(
            "Message stored: %s from=%s to=%s type=%s",
            message.id,
            message.from_agent,
            message.to_agent,
            message.message_type,
        )
        return message

    def get_inbox(self, agent_id: str) -> list[Message]:
        return [m for m in self._messages if m.to_agent == agent_id]

    def get_inbox_after(
        self,
        agent_id: str,
        after_message_id: Optional[str] = None,
    ) -> list[Message]:
        inbox = self.get_inbox(agent_id)
        if after_message_id is None:
            return inbox

        for index, message in enumerate(inbox):
            if message.id == after_message_id:
                return inbox[index + 1 :]
        raise ValueError(
            f"Message {after_message_id!r} was not found in {agent_id!r}'s inbox"
        )

    async def notify(self) -> None:
        async with self._new_message:
            self._new_message.notify_all()

    async def wait_for_inbox(
        self,
        agent_id: str,
        after_message_id: Optional[str],
        timeout_seconds: float,
    ) -> Optional[Message]:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds

        async with self._new_message:
            while True:
                messages = self.get_inbox_after(agent_id, after_message_id)
                if messages:
                    return messages[0]

                remaining = deadline - loop.time()
                if remaining <= 0:
                    return None

                try:
                    await asyncio.wait_for(self._new_message.wait(), remaining)
                except TimeoutError:
                    return None

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
        "message_type": (
            message.message_type.value
            if isinstance(message.message_type, MessageType)
            else message.message_type
        ),
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
            f"Invalid message_type: {message_type!r}. "
            f"Must be one of {VALID_MESSAGE_TYPES}"
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
    await store.notify()

    logger.info(
        "Message sent: %s -> %s [%s] (task=%s)",
        from_agent,
        to_agent,
        message_type,
        task_id,
    )

    return _message_to_dict(message)


async def get_agent_inbox(
    agent_id: str,
    after_message_id: Optional[str] = None,
    limit: int = 100,
) -> dict:
    """Return messages delivered to an agent, optionally after a cursor."""
    if not agent_id or not agent_id.strip():
        raise ValueError("agent_id must not be empty")
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")

    messages = get_message_store().get_inbox_after(agent_id, after_message_id)
    selected = messages[:limit]
    return {
        "agent_id": agent_id,
        "messages": [_message_to_dict(message) for message in selected],
        "count": len(selected),
        "has_more": len(messages) > len(selected),
        "latest_message_id": (selected[-1].id if selected else after_message_id),
    }


async def wait_for_agent_message(
    agent_id: str,
    after_message_id: Optional[str] = None,
    timeout_seconds: float = 30.0,
) -> dict:
    """Wait until an agent receives a message or the timeout expires."""
    if not agent_id or not agent_id.strip():
        raise ValueError("agent_id must not be empty")
    if timeout_seconds < 0 or timeout_seconds > 300:
        raise ValueError("timeout_seconds must be between 0 and 300")

    message = await get_message_store().wait_for_inbox(
        agent_id=agent_id,
        after_message_id=after_message_id,
        timeout_seconds=timeout_seconds,
    )
    return {
        "agent_id": agent_id,
        "message": _message_to_dict(message) if message is not None else None,
        "timed_out": message is None,
    }
