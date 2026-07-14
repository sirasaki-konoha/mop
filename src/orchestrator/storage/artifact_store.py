from __future__ import annotations

import logging
from typing import Optional

from orchestrator.models.artifact import Artifact

logger = logging.getLogger(__name__)


class ArtifactStore:
    def __init__(self) -> None:
        self._artifacts: dict[str, Artifact] = {}

    def save(self, artifact: Artifact) -> Artifact:
        self._artifacts[artifact.id] = artifact
        logger.info(
            "Artifact saved: %s (task=%s, agent=%s, v%d)",
            artifact.id, artifact.task_id, artifact.agent_id, artifact.version,
        )
        return artifact

    def get(self, artifact_id: str) -> Optional[Artifact]:
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            logger.warning("Artifact not found: %s", artifact_id)
        return artifact

    async def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        return self.get(artifact_id)

    def get_by_task(self, task_id: str) -> list[Artifact]:
        return [a for a in self._artifacts.values() if a.task_id == task_id]

    get_artifacts_by_task = get_by_task

    def get_by_agent(self, agent_id: str) -> list[Artifact]:
        return [a for a in self._artifacts.values() if a.agent_id == agent_id]

    def get_latest_version(
        self, task_id: str, agent_id: str, file_path: str,
    ) -> Optional[Artifact]:
        versions = [
            a for a in self._artifacts.values()
            if a.task_id == task_id and a.agent_id == agent_id and a.file_path == file_path
        ]
        if not versions:
            return None
        return max(versions, key=lambda a: a.version)

    def delete(self, artifact_id: str) -> bool:
        if artifact_id in self._artifacts:
            del self._artifacts[artifact_id]
            logger.info("Artifact deleted: %s", artifact_id)
            return True
        logger.warning("Artifact not found for deletion: %s", artifact_id)
        return False

    def list_all(self) -> list[Artifact]:
        return list(self._artifacts.values())


_artifact_store: Optional[ArtifactStore] = None


def get_artifact_store() -> ArtifactStore:
    global _artifact_store
    if _artifact_store is None:
        _artifact_store = ArtifactStore()
        logger.info("ArtifactStore initialized")
    return _artifact_store
