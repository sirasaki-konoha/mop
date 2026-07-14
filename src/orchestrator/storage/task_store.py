"""In-memory storage backend for :class:`Task` instances."""

import logging
from typing import Dict, List, Optional

from ..models.task import Task

logger = logging.getLogger(__name__)


_task_store: Optional["TaskStore"] = None


def get_task_store() -> "TaskStore":
    """Return the global singleton :class:`TaskStore` instance."""
    global _task_store
    if _task_store is None:
        _task_store = TaskStore()
        logger.info("TaskStore initialized")
    return _task_store


class TaskStore:
    """Simple in-memory store for tasks.

    This store is intentionally minimal; persistence can be swapped in later
    without changing the public interface.
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}

    def create(self, task: Task) -> Task:
        """Persist a new task.

        Args:
            task: The task to store.

        Returns:
            The stored task.

        Raises:
            ValueError: If a task with the same ID already exists.
        """
        if task.id in self._tasks:
            logger.error("Task already exists: %s", task.id)
            raise ValueError(f"Task already exists: {task.id}")
        self._tasks[task.id] = task
        logger.debug("Created task %s", task.id)
        return task

    # Aliases used by the MCP tool classes and the test suite.
    create_task = create

    def get(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID.

        Args:
            task_id: The task identifier.

        Returns:
            The matching task, or ``None`` if not found.
        """
        return self._tasks.get(task_id)

    # Alias used by the MCP tool classes and the test suite.
    get_task = get

    def update(self, task: Task) -> Task:
        """Update an existing task.

        Args:
            task: The task to update.

        Returns:
            The updated task.

        Raises:
            ValueError: If the task does not exist in the store.
        """
        if task.id not in self._tasks:
            logger.error("Task not found for update: %s", task.id)
            raise ValueError(f"Task not found: {task.id}")
        task.touch()
        self._tasks[task.id] = task
        logger.debug("Updated task %s", task.id)
        return task

    # Alias used by the MCP tool classes and the test suite.
    update_task = update

    def delete(self, task_id: str) -> bool:
        """Delete a task by ID.

        Args:
            task_id: The task identifier.

        Returns:
            ``True`` if the task was deleted, ``False`` if it did not exist.
        """
        if task_id in self._tasks:
            del self._tasks[task_id]
            logger.debug("Deleted task %s", task_id)
            return True
        return False

    def list_all(self) -> List[Task]:
        """Return a list of all stored tasks."""
        return list(self._tasks.values())
