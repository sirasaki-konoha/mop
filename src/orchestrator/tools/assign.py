"""MCP tool: assign_agent.

This module is owned by Agent A (Kimi K2.7 Code). It assigns a task to a
specific agent and updates the task status accordingly.
"""

import logging
from typing import Optional, Protocol

from ..models.agent import Agent
from ..models.task import Task, TaskStatus

logger = logging.getLogger(__name__)


class _TaskStore(Protocol):
    """Minimal task-store interface required by :class:`AssignTool`."""

    def get_task(self, task_id: str) -> Optional[Task]: ...
    def update_task(self, task: Task) -> Task: ...


class _AgentStore(Protocol):
    """Minimal agent-store interface required by :class:`AssignTool`."""

    def get_agent(self, agent_id: str) -> Optional[Agent]: ...


class AssignTool:
    """Tool for assigning tasks to agents."""

    def __init__(self, task_store: _TaskStore, agent_store: _AgentStore) -> None:
        self.task_store = task_store
        self.agent_store = agent_store

    async def assign_agent(self, task_id: str, agent_id: str) -> Task:
        """Assign a task to an agent.

        Args:
            task_id: The task to assign.
            agent_id: The agent that will own the task.

        Returns:
            The updated task.

        Raises:
            ValueError: If the task does not exist.
            ValueError: If the task is already assigned.
            ValueError: If the agent does not exist.
        """
        logger.info(
            "Tool assign_agent invoked: task_id=%s, agent_id=%s",
            task_id,
            agent_id,
        )

        task = self.task_store.get_task(task_id)
        if task is None:
            logger.error("Task not found: %s", task_id)
            raise ValueError("Task not found")

        if task.assigned_agent is not None:
            logger.error(
                "Task %s is already assigned to %s",
                task_id,
                task.assigned_agent,
            )
            raise ValueError("Task already assigned")

        agent = self.agent_store.get_agent(agent_id)
        if agent is None:
            logger.error("Agent not found: %s", agent_id)
            raise ValueError("Agent not found")

        task.assigned_agent = agent_id
        task.status = TaskStatus.IN_PROGRESS
        task.touch()
        updated = self.task_store.update_task(task)

        logger.info("Tool assign_agent completed for task %s", updated.id)
        return updated


# Global function used by the MCP server registration in ``server.py``.
_default_assign_tool: Optional[AssignTool] = None


async def assign_agent(task_id: str, agent_id: str) -> Task:
    """Assign a task to an agent using the global stores.

    This convenience wrapper uses the global task store and the global
    orchestrator (as the agent store) so that the MCP server can register a
    plain async function as a tool.
    """
    from ..orchestrator import get_orchestrator
    from ..storage.task_store import get_task_store

    global _default_assign_tool
    if _default_assign_tool is None:
        _default_assign_tool = AssignTool(get_task_store(), get_orchestrator())
    return await _default_assign_tool.assign_agent(task_id, agent_id)
