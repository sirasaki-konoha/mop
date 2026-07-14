"""MCP tool: decompose_task.

This module is owned by Agent A (Kimi K2.7 Code). It structures the LLM's
decomposition output into a concrete :class:`Task` hierarchy.
"""

import logging
import re
import uuid
from typing import List, Optional, Protocol

from ..models.task import Task

logger = logging.getLogger(__name__)


class _TaskStore(Protocol):
    """Minimal task-store interface required by :class:`DecomposeTool`."""

    def create_task(self, task: Task) -> Task: ...
    def update_task(self, task: Task) -> Task: ...


class DecomposeTool:
    """Tool for decomposing a user request into a hierarchy of tasks."""

    def __init__(self, task_store: _TaskStore) -> None:
        self.task_store = task_store

    async def decompose_task(self, request: str) -> Task:
        """Decompose a user request into a root task and subtasks.

        Args:
            request: The user request to decompose.

        Returns:
            The root task, with ``subtasks`` populated by child task IDs.

        Raises:
            ValueError: If ``request`` is empty or contains only whitespace.
        """
        logger.info("Tool decompose_task invoked for request: %s", request)

        if not request or not request.strip():
            logger.error("decompose_task received an empty request")
            raise ValueError("Request cannot be empty")

        root = self._create_root_task(request)
        subtask_descriptions = self._generate_subtasks(request)
        for description in subtask_descriptions:
            self._create_subtask(description, root)

        self.task_store.update_task(root)
        logger.info(
            "Tool decompose_task completed for task %s with %d subtasks",
            root.id,
            len(root.subtasks),
        )
        return root

    def _create_root_task(self, description: str) -> Task:
        """Create and persist the root task for a request."""
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        task = Task(id=task_id, description=description)
        self.task_store.create_task(task)
        logger.debug("Created root task %s", task_id)
        return task

    def _create_subtask(self, description: str, parent: Task) -> Task:
        """Create a subtask, persist it, and link it to its parent."""
        subtask_id = f"sub-{uuid.uuid4().hex[:8]}"
        subtask = Task(
            id=subtask_id,
            description=description,
            parent_task_id=parent.id,
        )
        self.task_store.create_task(subtask)
        parent.subtasks.append(subtask_id)
        logger.debug("Created subtask %s under %s", subtask_id, parent.id)
        return subtask

    def _generate_subtasks(self, request: str) -> List[str]:
        """Generate candidate subtask descriptions from a request.

        This is intentionally lightweight: it first attempts to split on common
        delimiters, and falls back to a generic software-development template.
        """
        parts = [p.strip() for p in re.split(r"[,;\n]+", request) if p.strip()]
        if len(parts) > 1:
            return parts

        return [
            f"Design specification for: {request}",
            f"Implement core logic for: {request}",
            f"Write tests for: {request}",
            f"Review and finalize: {request}",
        ]


# Global function used by the MCP server registration in ``server.py``.
_default_decompose_tool: Optional[DecomposeTool] = None


async def decompose_task(request: str) -> Task:
    """Decompose a user request into a root task and subtasks.

    This convenience wrapper uses the global task store so that the MCP server
    can register a plain async function as a tool.
    """
    from ..storage.task_store import get_task_store

    global _default_decompose_tool
    if _default_decompose_tool is None:
        _default_decompose_tool = DecomposeTool(get_task_store())
    return await _default_decompose_tool.decompose_task(request)
