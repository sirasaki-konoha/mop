"""Agent and Message data models for the Multi-Agent MCP Orchestrator."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class MessageType(Enum):
    """Enumeration of supported agent message types."""

    REQUEST = "request"
    RESPONSE = "response"
    REVIEW = "review"
    QUESTION = "question"


@dataclass
class Message:
    """A single message exchanged between agents."""

    id: str
    from_agent: str
    to_agent: str
    message_type: MessageType
    content: str
    task_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Agent:
    """Represents an AI agent participating in the orchestration."""

    id: str
    name: str
    model: str
    role: str
    status: str = "idle"
    inbox: list[Message] = field(default_factory=list)
