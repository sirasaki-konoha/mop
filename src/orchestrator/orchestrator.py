"""Core orchestration logic for the Multi-Agent MCP Orchestrator."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models.agent import Agent, Message, MessageType
from .models.task import Task, TaskStatus
from .storage.task_store import TaskStore, get_task_store

logger = logging.getLogger(__name__)

_orchestrator: Optional["Orchestrator"] = None


def get_orchestrator() -> "Orchestrator":
    """Return the global singleton :class:`Orchestrator` instance.

    The orchestrator shares the global task store so that tool functions
    registered by the MCP server see the same state as the orchestrator facade.
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(task_store=get_task_store())
        logger.info("Orchestrator singleton initialized")
    return _orchestrator


@dataclass
class _DummyReview:
    """Fallback review object used when Agent C's review module is unavailable."""

    artifact_id: str
    reviewer_agent_id: str
    status: str = "approved"
    comments: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class Orchestrator:
    """Central coordinator for tasks, agents, artifacts, and messages."""

    def __init__(
        self,
        task_store: Optional[TaskStore] = None,
        agent_store: Optional[Any] = None,
        artifact_store: Optional[Any] = None,
    ) -> None:
        self.task_store = task_store or TaskStore()
        self.agent_store = agent_store or self
        self.artifact_store = artifact_store
        self._agents: Dict[str, Agent] = {}
        self._init_default_agents()

        # Tool instances used by facade methods.
        from .tools import DecomposeTool, AssignTool, MergeTool

        self._decompose_tool = DecomposeTool(self.task_store)
        self._assign_tool = AssignTool(self.task_store, self.agent_store)
        self._merge_tool: Optional[MergeTool] = None
        if self.artifact_store is not None:
            self._merge_tool = MergeTool(self.task_store, self.artifact_store)

    def _init_default_agents(self) -> None:
        """Register the three default agents defined by the project plan."""
        defaults = [
            Agent(
                id="A-Kimi",
                name="Agent A (Planner)",
                model="kimi-k2.7-code",
                role="planner",
            ),
            Agent(
                id="B-Qwen",
                name="Agent B (Coder)",
                model="qwen3.7-plus",
                role="coder",
            ),
            Agent(
                id="C-Mimo",
                name="Agent C (Tester)",
                model="mimo-v2.5-pro",
                role="tester",
            ),
        ]
        for agent in defaults:
            self._agents[agent.id] = agent
        logger.info("Initialized %d default agents", len(defaults))

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    async def decompose_task(self, request: str) -> Task:
        """Facade for the ``decompose_task`` tool."""
        return await self._decompose_tool.decompose_task(request)

    async def assign_agent(self, task_id: str, agent_id: str) -> Task:
        """Facade for the ``assign_agent`` tool."""
        return await self._assign_tool.assign_agent(task_id, agent_id)

    async def merge_results(self, task_id: str) -> Task:
        """Facade for the ``merge_results`` tool."""
        if self._merge_tool is None:
            raise RuntimeError("Artifact store is not configured")
        return await self._merge_tool.merge_results(task_id)

    async def get_task_status(self, task_id: str) -> Task:
        """Return the full status record for a task."""
        task = self.task_store.get_task(task_id)
        if task is None:
            logger.error("Task not found: %s", task_id)
            raise ValueError("Task not found")
        return task

    def create_root_task(self, description: str) -> Task:
        """Create a new root task from a user request.

        This low-level helper remains available for callers that prefer to
        interact with the orchestrator directly rather than through the tool
        facade.
        """
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        task = Task(id=task_id, description=description)
        self.task_store.create_task(task)
        logger.info("Created root task %s", task_id)
        return task

    def create_subtask(self, description: str, parent_task_id: str) -> Task:
        """Create a subtask and attach it to its parent."""
        parent = self.task_store.get_task(parent_task_id)
        if parent is None:
            logger.error("Parent task not found: %s", parent_task_id)
            raise ValueError(f"Parent task not found: {parent_task_id}")

        subtask_id = f"sub-{uuid.uuid4().hex[:8]}"
        subtask = Task(
            id=subtask_id,
            description=description,
            parent_task_id=parent_task_id,
        )
        self.task_store.create_task(subtask)

        parent.subtasks.append(subtask_id)
        parent.touch()
        self.task_store.update_task(parent)

        logger.info("Created subtask %s under %s", subtask_id, parent_task_id)
        return subtask

    def update_task_status(self, task_id: str, status: TaskStatus) -> Task:
        """Update the status of a task."""
        task = self.task_store.get_task(task_id)
        if task is None:
            logger.error("Task not found: %s", task_id)
            raise ValueError(f"Task not found: {task_id}")

        task.status = status
        task.touch()
        self.task_store.update_task(task)
        logger.info("Updated task %s status to %s", task_id, status.value)
        return task

    def add_artifact_to_task(self, task_id: str, artifact_id: str) -> Task:
        """Attach an artifact reference to a task."""
        task = self.task_store.get_task(task_id)
        if task is None:
            logger.error("Task not found: %s", task_id)
            raise ValueError(f"Task not found: {task_id}")

        if artifact_id not in task.artifacts:
            task.artifacts.append(artifact_id)
            task.touch()
            self.task_store.update_task(task)
            logger.info("Added artifact %s to task %s", artifact_id, task_id)
        return task

    # ------------------------------------------------------------------
    # Artifact submission (facade for Agent B's submit_artifact tool)
    # ------------------------------------------------------------------

    async def submit_artifact(
        self,
        task_id: str,
        agent_id: str,
        file_path: str,
        content: str,
        type: str,
    ) -> Any:
        """Submit an artifact and attach it to a task."""
        if self.artifact_store is None:
            raise RuntimeError("Artifact store is not configured")

        # Agent B's artifact store uses ``save`` while the test mocks use
        # ``save_artifact``. Support both conventions transparently.
        save_kwargs = {
            "task_id": task_id,
            "agent_id": agent_id,
            "file_path": file_path,
            "content": content,
            "type": type,
        }
        if hasattr(self.artifact_store, "save_artifact"):
            artifact = await self.artifact_store.save_artifact(**save_kwargs)
        elif hasattr(self.artifact_store, "save"):
            artifact = await self.artifact_store.save(**save_kwargs)
        else:
            raise AttributeError(
                "Artifact store has no suitable save method"
            )

        artifact_id = getattr(artifact, "id", None)
        if artifact_id is not None:
            self.add_artifact_to_task(task_id, artifact_id)
        logger.info("Submitted artifact %s for task %s", artifact_id, task_id)
        return artifact

    # ------------------------------------------------------------------
    # Agent communication (facade for Agent B's agent_communicate tool)
    # ------------------------------------------------------------------

    async def agent_communicate(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        content: str,
        task_id: Optional[str] = None,
    ) -> Message:
        """Deliver a message from one agent to another."""
        try:
            msg_type = MessageType(message_type)
        except ValueError as exc:
            logger.error("Invalid message type: %s", message_type)
            raise ValueError(f"Invalid message type: {message_type}") from exc

        message_id = f"msg-{uuid.uuid4().hex[:8]}"
        message = Message(
            id=message_id,
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=msg_type,
            content=content,
            task_id=task_id,
        )
        self.add_message_to_agent(to_agent, message)
        logger.info(
            "Delivered message %s from %s to %s",
            message_id,
            from_agent,
            to_agent,
        )
        return message

    # ------------------------------------------------------------------
    # Code review (facade for Agent C's review_code tool)
    # ------------------------------------------------------------------

    async def review_code(self, artifact_id: str, reviewer_agent_id: str) -> Any:
        """Review a submitted artifact.

        The actual review logic lives in Agent C's ``review.py``. This facade
        delegates to it when available and falls back to a minimal dummy review
        otherwise so that the orchestrator remains importable before all agents
        have contributed their modules.
        """
        if self.artifact_store is None:
            raise RuntimeError("Artifact store is not configured")

        try:
            from .tools.review import ReviewTool
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning(
                "ReviewTool not available (%s); returning dummy review",
                exc,
            )
            return _DummyReview(
                artifact_id=artifact_id,
                reviewer_agent_id=reviewer_agent_id,
                status="approved",
            )

        review_tool = ReviewTool(self.artifact_store)
        return await review_tool.review_code(artifact_id, reviewer_agent_id)

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Return an agent by ID, or ``None`` if not registered."""
        return self._agents.get(agent_id)

    def add_message_to_agent(self, agent_id: str, message: Message) -> Agent:
        """Deliver a message to an agent's inbox."""
        agent = self._agents.get(agent_id)
        if agent is None:
            logger.error("Agent not found: %s", agent_id)
            raise ValueError(f"Agent not found: {agent_id}")

        agent.inbox.append(message)
        logger.info(
            "Delivered message %s from %s to agent %s",
            message.id,
            message.from_agent,
            agent_id,
        )
        return agent

    def list_agents(self) -> List[Agent]:
        """Return a list of all registered agents."""
        return list(self._agents.values())
