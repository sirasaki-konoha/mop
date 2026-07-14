"""MCP tool: merge_results.

This module is owned by Agent A (Kimi K2.7 Code). It merges the artifacts
produced by subtasks into the parent task and finalizes the task.
"""

import logging
from typing import Any, List, Optional, Protocol

from ..models.task import Task, TaskStatus

logger = logging.getLogger(__name__)


class _TaskStore(Protocol):
    """Minimal task-store interface required by :class:`MergeTool`."""

    def get_task(self, task_id: str) -> Optional[Task]: ...
    def update_task(self, task: Task) -> Task: ...


class _ArtifactStore(Protocol):
    """Minimal artifact-store interface required by :class:`MergeTool`."""

    def get_artifacts_by_task(self, task_id: str) -> List[Any]: ...
    def get_by_task(self, task_id: str) -> List[Any]: ...


class MergeTool:
    """Tool for merging subtask artifacts into a parent task."""

    def __init__(self, task_store: _TaskStore, artifact_store: _ArtifactStore) -> None:
        self.task_store = task_store
        self.artifact_store = artifact_store

    async def merge_results(self, task_id: str) -> Task:
        """Merge the results of a task's subtasks into the parent task.

        Args:
            task_id: The root task whose subtasks should be merged.

        Returns:
            The updated root task, including the merged artifact references.

        Raises:
            ValueError: If the task does not exist.
            ValueError: If any subtask has failed.
            ValueError: If not all subtasks are completed.
        """
        logger.info("Tool merge_results invoked for task %s", task_id)

        task = self.task_store.get_task(task_id)
        if task is None:
            logger.error("Task not found: %s", task_id)
            raise ValueError("Task not found")

        subtasks = self._load_subtasks(task)

        if any(subtask.status == TaskStatus.FAILED for subtask in subtasks):
            logger.error("Task %s has failed subtasks; cannot merge", task_id)
            raise ValueError("Some subtasks failed")

        if any(subtask.status != TaskStatus.COMPLETED for subtask in subtasks):
            logger.error("Task %s has incomplete subtasks; cannot merge", task_id)
            raise ValueError("Not all subtasks completed")

        merged_artifact_ids: List[str] = []
        for subtask in subtasks:
            artifacts = self._get_artifacts_by_task(subtask.id)
            for artifact in artifacts:
                artifact_id = getattr(artifact, "id", None)
                if artifact_id is not None and artifact_id not in merged_artifact_ids:
                    merged_artifact_ids.append(artifact_id)

        task.artifacts = merged_artifact_ids
        task.status = TaskStatus.COMPLETED
        task.touch()
        updated = self.task_store.update_task(task)

        logger.info(
            "Tool merge_results completed for task %s with %d artifacts",
            updated.id,
            len(updated.artifacts),
        )
        return updated

    def _get_artifacts_by_task(self, task_id: str) -> List[Any]:
        """Retrieve artifacts for a task, supporting both store conventions."""
        if hasattr(self.artifact_store, "get_artifacts_by_task"):
            return self.artifact_store.get_artifacts_by_task(task_id)
        if hasattr(self.artifact_store, "get_by_task"):
            return self.artifact_store.get_by_task(task_id)
        raise AttributeError(
            "Artifact store has no method to retrieve artifacts by task"
        )

    def _load_subtasks(self, task: Task) -> List[Task]:
        """Load and validate all subtasks for the given parent task."""
        subtasks: List[Task] = []
        for subtask_id in task.subtasks:
            subtask = self.task_store.get_task(subtask_id)
            if subtask is None:
                logger.error("Subtask not found: %s", subtask_id)
                raise ValueError(f"Subtask not found: {subtask_id}")
            subtasks.append(subtask)
        return subtasks


# Global function used by the MCP server registration in ``server.py``.
_default_merge_tool: Optional[MergeTool] = None


async def merge_results(task_id: str) -> Task:
    """Merge the results of a task's subtasks using the global stores.

    This convenience wrapper uses the global task store and artifact store so
    that the MCP server can register a plain async function as a tool.
    """
    from ..storage.artifact_store import get_artifact_store
    from ..storage.task_store import get_task_store

    global _default_merge_tool
    if _default_merge_tool is None:
        _default_merge_tool = MergeTool(get_task_store(), get_artifact_store())
    return await _default_merge_tool.merge_results(task_id)
