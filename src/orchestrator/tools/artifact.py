from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from orchestrator.models.artifact import Artifact
from orchestrator.storage.artifact_store import ArtifactStore

logger = logging.getLogger(__name__)

VALID_ARTIFACT_TYPES = ("code", "test", "doc", "review")


def create_submit_artifact(
    artifact_store: ArtifactStore,
    orchestrator: Any,
) -> Callable:
    async def submit_artifact(
        task_id: str,
        agent_id: str,
        file_path: str,
        content: str,
        type: str,
    ) -> dict:
        if not task_id or not task_id.strip():
            raise ValueError("task_id must not be empty")
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id must not be empty")
        if not file_path or not file_path.strip():
            raise ValueError("file_path must not be empty")
        if not content:
            raise ValueError("content must not be empty")
        if type not in VALID_ARTIFACT_TYPES:
            raise ValueError(
                f"Invalid artifact type: {type!r}. Must be one of {VALID_ARTIFACT_TYPES}"
            )

        existing = artifact_store.get_latest_version(task_id, agent_id, file_path)
        version = (existing.version + 1) if existing else 1

        artifact = Artifact(
            task_id=task_id,
            agent_id=agent_id,
            file_path=file_path,
            content=content,
            type=type,
            version=version,
        )
        artifact_store.save(artifact)

        try:
            orchestrator.add_artifact_to_task(task_id, artifact.id)
        except Exception:
            logger.warning(
                "Failed to link artifact %s to task %s via orchestrator",
                artifact.id, task_id, exc_info=True,
            )

        logger.info(
            "Artifact submitted: %s (task=%s, agent=%s, file=%s, v%d)",
            artifact.id, task_id, agent_id, file_path, version,
        )

        return artifact.model_dump(mode="json")

    return submit_artifact
