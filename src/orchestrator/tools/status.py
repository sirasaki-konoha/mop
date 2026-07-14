from __future__ import annotations

import dataclasses
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def create_get_task_status(task_store: Any) -> Callable:
    async def get_task_status(task_id: str) -> dict:
        if not task_id or not task_id.strip():
            raise ValueError("task_id must not be empty")

        task = task_store.get(task_id)

        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        logger.info("Task status retrieved: %s (status=%s)", task_id, task.status)

        if dataclasses.is_dataclass(task):
            result = dataclasses.asdict(task)
            for key, value in result.items():
                if hasattr(value, "isoformat"):
                    result[key] = value.isoformat()
                elif hasattr(value, "value"):
                    result[key] = value.value
            return result
        if hasattr(task, "model_dump"):
            return task.model_dump(mode="json")
        raise TypeError(f"Unsupported task type: {type(task)}")

    return get_task_status
