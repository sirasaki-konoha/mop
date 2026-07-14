"""
Tests for merge_results tool.

This module contains tests for the merge_results tool implementation.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.orchestrator.tools.merge import MergeTool
from src.orchestrator.models.task import Task, TaskStatus
from src.orchestrator.models.artifact import Artifact


@pytest.fixture
def mock_task_store():
    """Create a mock task store."""
    store = MagicMock()
    store.get_task = MagicMock()
    store.update_task = MagicMock()
    return store


@pytest.fixture
def mock_artifact_store():
    """Create a mock artifact store."""
    store = MagicMock()
    store.get_artifacts_by_task = MagicMock()
    return store


@pytest.fixture
def merge_tool(mock_task_store, mock_artifact_store):
    """Create a merge tool instance with mock stores."""
    return MergeTool(task_store=mock_task_store, artifact_store=mock_artifact_store)


@pytest.fixture
def sample_task_with_subtasks():
    """Create a sample task with subtasks for testing."""
    return Task(
        id="parent-task",
        description="Implement user management system",
        status=TaskStatus.IN_PROGRESS,
        assigned_agent="agent-a",
        parent_task_id=None,
        subtasks=["subtask-1", "subtask-2", "subtask-3"],
        artifacts=[],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def sample_subtasks():
    """Create sample subtasks for testing."""
    return [
        Task(
            id="subtask-1",
            description="Design database schema",
            status=TaskStatus.COMPLETED,
            assigned_agent="agent-b",
            parent_task_id="parent-task",
            subtasks=[],
            artifacts=["artifact-1"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        Task(
            id="subtask-2",
            description="Implement API endpoints",
            status=TaskStatus.COMPLETED,
            assigned_agent="agent-b",
            parent_task_id="parent-task",
            subtasks=[],
            artifacts=["artifact-2"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        Task(
            id="subtask-3",
            description="Write tests",
            status=TaskStatus.COMPLETED,
            assigned_agent="agent-c",
            parent_task_id="parent-task",
            subtasks=[],
            artifacts=["artifact-3"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    ]


@pytest.fixture
def sample_artifacts():
    """Create sample artifacts for testing."""
    return [
        Artifact(
            id="artifact-1",
            task_id="subtask-1",
            agent_id="agent-b",
            file_path="src/models/user.py",
            content="class User: ...",
            type="code",
            version=1
        ),
        Artifact(
            id="artifact-2",
            task_id="subtask-2",
            agent_id="agent-b",
            file_path="src/routes/users.py",
            content="@app.get('/users') ...",
            type="code",
            version=1
        ),
        Artifact(
            id="artifact-3",
            task_id="subtask-3",
            agent_id="agent-c",
            file_path="tests/test_users.py",
            content="def test_get_users(): ...",
            type="test",
            version=1
        )
    ]


@pytest.mark.asyncio
async def test_merge_results_success(merge_tool, mock_task_store, mock_artifact_store,
                                    sample_task_with_subtasks, sample_subtasks, sample_artifacts):
    """Test successful merging of subtask results."""
    # Arrange
    mock_task_store.get_task.side_effect = lambda task_id: {
        "parent-task": sample_task_with_subtasks,
        "subtask-1": sample_subtasks[0],
        "subtask-2": sample_subtasks[1],
        "subtask-3": sample_subtasks[2]
    }.get(task_id)
    
    mock_artifact_store.get_artifacts_by_task.side_effect = lambda task_id: {
        "subtask-1": [sample_artifacts[0]],
        "subtask-2": [sample_artifacts[1]],
        "subtask-3": [sample_artifacts[2]]
    }.get(task_id, [])
    
    mock_task_store.update_task.return_value = sample_task_with_subtasks
    
    # Act
    result = await merge_tool.merge_results("parent-task")
    
    # Assert
    assert result is not None
    assert result.status == TaskStatus.COMPLETED
    assert len(result.artifacts) == 3
    mock_task_store.update_task.assert_called_once()


@pytest.mark.asyncio
async def test_merge_results_task_not_found(merge_tool, mock_task_store):
    """Test merge when task is not found."""
    # Arrange
    mock_task_store.get_task.return_value = None
    
    # Act & Assert
    with pytest.raises(ValueError, match="Task not found"):
        await merge_tool.merge_results("nonexistent-task")


@pytest.mark.asyncio
async def test_merge_results_with_incomplete_subtasks(merge_tool, mock_task_store,
                                                      sample_task_with_subtasks, sample_subtasks):
    """Test merge when some subtasks are not completed."""
    # Arrange
    sample_subtasks[1].status = TaskStatus.IN_PROGRESS  # One subtask not completed
    mock_task_store.get_task.side_effect = lambda task_id: {
        "parent-task": sample_task_with_subtasks,
        "subtask-1": sample_subtasks[0],
        "subtask-2": sample_subtasks[1],
        "subtask-3": sample_subtasks[2]
    }.get(task_id)
    
    # Act & Assert
    with pytest.raises(ValueError, match="Not all subtasks completed"):
        await merge_tool.merge_results("parent-task")


@pytest.mark.asyncio
async def test_merge_results_with_failed_subtasks(merge_tool, mock_task_store,
                                                   sample_task_with_subtasks, sample_subtasks):
    """Test merge when some subtasks have failed."""
    # Arrange
    sample_subtasks[2].status = TaskStatus.FAILED
    mock_task_store.get_task.side_effect = lambda task_id: {
        "parent-task": sample_task_with_subtasks,
        "subtask-1": sample_subtasks[0],
        "subtask-2": sample_subtasks[1],
        "subtask-3": sample_subtasks[2]
    }.get(task_id)
    
    # Act & Assert
    with pytest.raises(ValueError, match="Some subtasks failed"):
        await merge_tool.merge_results("parent-task")


@pytest.mark.asyncio
async def test_merge_results_combines_artifacts(merge_tool, mock_task_store, mock_artifact_store,
                                                sample_task_with_subtasks, sample_subtasks, sample_artifacts):
    """Test that merge correctly combines artifacts from all subtasks."""
    # Arrange
    mock_task_store.get_task.side_effect = lambda task_id: {
        "parent-task": sample_task_with_subtasks,
        "subtask-1": sample_subtasks[0],
        "subtask-2": sample_subtasks[1],
        "subtask-3": sample_subtasks[2]
    }.get(task_id)
    
    mock_artifact_store.get_artifacts_by_task.side_effect = lambda task_id: {
        "subtask-1": [sample_artifacts[0]],
        "subtask-2": [sample_artifacts[1]],
        "subtask-3": [sample_artifacts[2]]
    }.get(task_id, [])
    
    mock_task_store.update_task.return_value = sample_task_with_subtasks
    
    # Act
    result = await merge_tool.merge_results("parent-task")
    
    # Assert
    assert len(result.artifacts) == 3
    assert "artifact-1" in result.artifacts
    assert "artifact-2" in result.artifacts
    assert "artifact-3" in result.artifacts


@pytest.mark.asyncio
async def test_merge_results_updates_parent_task_status(merge_tool, mock_task_store, mock_artifact_store,
                                                        sample_task_with_subtasks, sample_subtasks, sample_artifacts):
    """Test that merge updates parent task status to COMPLETED."""
    # Arrange
    mock_task_store.get_task.side_effect = lambda task_id: {
        "parent-task": sample_task_with_subtasks,
        "subtask-1": sample_subtasks[0],
        "subtask-2": sample_subtasks[1],
        "subtask-3": sample_subtasks[2]
    }.get(task_id)
    
    mock_artifact_store.get_artifacts_by_task.side_effect = lambda task_id: {
        "subtask-1": [sample_artifacts[0]],
        "subtask-2": [sample_artifacts[1]],
        "subtask-3": [sample_artifacts[2]]
    }.get(task_id, [])
    
    mock_task_store.update_task.return_value = sample_task_with_subtasks
    
    # Act
    result = await merge_tool.merge_results("parent-task")
    
    # Assert
    assert result.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_merge_results_with_no_artifacts(merge_tool, mock_task_store, mock_artifact_store,
                                                sample_task_with_subtasks, sample_subtasks):
    """Test merge when subtasks have no artifacts."""
    # Arrange
    mock_task_store.get_task.side_effect = lambda task_id: {
        "parent-task": sample_task_with_subtasks,
        "subtask-1": sample_subtasks[0],
        "subtask-2": sample_subtasks[1],
        "subtask-3": sample_subtasks[2]
    }.get(task_id)
    
    mock_artifact_store.get_artifacts_by_task.return_value = []
    mock_task_store.update_task.return_value = sample_task_with_subtasks
    
    # Act
    result = await merge_tool.merge_results("parent-task")
    
    # Assert
    assert result.status == TaskStatus.COMPLETED
    assert len(result.artifacts) == 0