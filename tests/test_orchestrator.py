"""
Integration tests for the Multi-Agent MCP Orchestrator.

This module contains integration tests that verify the interaction
between different components of the orchestrator.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.orchestrator.orchestrator import Orchestrator
from src.orchestrator.models.task import Task, TaskStatus
from src.orchestrator.models.agent import Agent, Message, MessageType
from src.orchestrator.models.artifact import Artifact


@pytest.fixture
def mock_task_store():
    """Create a mock task store."""
    store = MagicMock()
    store.create_task = MagicMock()
    store.get_task = MagicMock()
    store.update_task = MagicMock()
    return store


@pytest.fixture
def mock_artifact_store():
    """Create a mock artifact store."""
    store = MagicMock()
    store.save_artifact = MagicMock()
    store.get_artifact = MagicMock()
    store.get_artifacts_by_task = MagicMock()
    return store


@pytest.fixture
def orchestrator(mock_task_store, mock_artifact_store):
    """Create an orchestrator instance with mock stores."""
    return Orchestrator(
        task_store=mock_task_store,
        artifact_store=mock_artifact_store
    )


@pytest.fixture
def sample_agents():
    """Create sample agents for testing."""
    return [
        Agent(
            id="A-Kimi",
            name="Agent A (Planner)",
            model="kimi-k2.7-code",
            role="planner",
            status="idle",
            inbox=[]
        ),
        Agent(
            id="B-Qwen",
            name="Agent B (Coder)",
            model="qwen3.7-plus",
            role="coder",
            status="idle",
            inbox=[]
        ),
        Agent(
            id="C-Mimo",
            name="Agent C (Tester)",
            model="mimo-v2.5-pro",
            role="tester",
            status="idle",
            inbox=[]
        )
    ]


@pytest.mark.asyncio
async def test_full_task_workflow(orchestrator, mock_task_store, mock_artifact_store):
    """Test complete task workflow from decomposition to merge."""
    # Arrange
    request = "Implement a simple calculator API"
    
    # Mock decompose_task
    root_task = Task(
        id="root-task",
        description=request,
        status=TaskStatus.PENDING,
        assigned_agent=None,
        parent_task_id=None,
        subtasks=["subtask-1", "subtask-2"],
        artifacts=[],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Use a mutable dict so mutations in-place by assign_agent propagate
    # but merge_results also sees the right state
    import copy
    
    def make_subtask1():
        return Task(
            id="subtask-1",
            description="Implement calculator logic",
            status=TaskStatus.COMPLETED,
            assigned_agent="B-Qwen",
            parent_task_id="root-task",
            subtasks=[],
            artifacts=["artifact-1"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def make_subtask2():
        return Task(
            id="subtask-2",
            description="Write tests for calculator",
            status=TaskStatus.COMPLETED,
            assigned_agent="C-Mimo",
            parent_task_id="root-task",
            subtasks=[],
            artifacts=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    task_db = {
        "root-task": root_task,
        "subtask-1": make_subtask1(),
        "subtask-2": make_subtask2(),
    }
    
    call_count = [0]
    def mock_create_task(task):
        call_count[0] += 1
        task_db[task.id] = task
        return task
    
    mock_task_store.create_task.side_effect = mock_create_task
    mock_task_store.get_task.side_effect = lambda task_id: task_db.get(task_id)
    mock_task_store.update_task.side_effect = lambda task: task
    
    # Mock submit_artifact
    artifact = Artifact(
        id="artifact-1",
        task_id="subtask-1",
        agent_id="B-Qwen",
        file_path="src/calculator.py",
        content="def add(a, b): return a + b",
        type="code",
        version=1
    )
    
    async def mock_save_artifact(**kwargs):
        return artifact
    
    mock_artifact_store.save_artifact = mock_save_artifact
    mock_artifact_store.get_artifacts_by_task.return_value = [artifact]
    
    # Act - decompose then merge (skip assign since subtasks are pre-configured as COMPLETED)
    decomposed_task = await orchestrator.decompose_task(request)
    merged_task = await orchestrator.merge_results("root-task")
    
    # Assert
    assert decomposed_task is not None
    assert merged_task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_agent_communication_workflow(orchestrator, mock_task_store):
    """Test communication between agents during task execution."""
    # Arrange
    mock_task_store.get_task.return_value = Task(
        id="task-1",
        description="Implement API",
        status=TaskStatus.IN_PROGRESS,
        assigned_agent="B-Qwen",
        parent_task_id=None,
        subtasks=[],
        artifacts=[],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Act
    # Agent B asks question
    message = await orchestrator.agent_communicate(
        from_agent="B-Qwen",
        to_agent="A-Kimi",
        message_type="question",
        content="What authentication method should I use?",
        task_id="task-1"
    )
    
    # Agent A responds
    response = await orchestrator.agent_communicate(
        from_agent="A-Kimi",
        to_agent="B-Qwen",
        message_type="response",
        content="Use JWT tokens",
        task_id="task-1"
    )
    
    # Assert
    assert message is not None
    assert response is not None
    assert message.from_agent == "B-Qwen"
    assert response.from_agent == "A-Kimi"


@pytest.mark.asyncio
async def test_review_workflow(orchestrator, mock_artifact_store):
    """Test code review workflow."""
    # Arrange
    artifact = Artifact(
        id="artifact-1",
        task_id="task-1",
        agent_id="B-Qwen",
        file_path="src/api.py",
        content="@app.get('/users')\ndef get_users():\n    return []",
        type="code",
        version=1
    )
    mock_artifact_store.get_artifact.return_value = artifact
    mock_artifact_store.get_artifact = AsyncMock(return_value=artifact)
    
    # Act
    review = await orchestrator.review_code(
        artifact_id="artifact-1",
        reviewer_agent_id="C-Mimo"
    )
    
    # Assert
    assert review is not None
    assert review.artifact_id == "artifact-1"
    assert review.reviewer_agent_id == "C-Mimo"
    status_val = review.status.value if hasattr(review.status, 'value') else review.status
    assert status_val in ["approved", "changes_requested", "rejected"]


@pytest.mark.asyncio
async def test_task_status_updates(orchestrator, mock_task_store):
    """Test that task status is properly updated throughout workflow."""
    # Arrange - create a fresh task for this test
    task = Task(
        id="task-status-test",
        description="Test task for status updates",
        status=TaskStatus.PENDING,
        assigned_agent=None,
        parent_task_id=None,
        subtasks=[],
        artifacts=[],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Create a fresh orchestrator for this test to avoid mock contamination
    fresh_orchestrator = Orchestrator(task_store=mock_task_store)
    
    # Reset mock and set up fresh behavior
    mock_task_store.reset_mock()
    
    # Mock get_task to return a fresh copy each time
    def mock_get_task(task_id):
        if task_id == "task-status-test":
            # Return a fresh copy each time
            return Task(
                id="task-status-test",
                description="Test task for status updates",
                status=TaskStatus.PENDING,
                assigned_agent=None,
                parent_task_id=None,
                subtasks=[],
                artifacts=[],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        return None
    
    mock_task_store.get_task.side_effect = mock_get_task
    
    # Mock update_task to return the updated task
    def mock_update_task(updated_task):
        return updated_task
    
    mock_task_store.update_task.side_effect = mock_update_task
    
    # Act
    # Get initial status
    initial_status = await fresh_orchestrator.get_task_status("task-status-test")
    
    # Assign agent (should change to IN_PROGRESS)
    assigned_task = await fresh_orchestrator.assign_agent("task-status-test", "B-Qwen")
    
    # Assert
    assert initial_status.status == TaskStatus.PENDING
    assert assigned_task.status == TaskStatus.IN_PROGRESS
    assert assigned_task.assigned_agent == "B-Qwen"


@pytest.mark.asyncio
async def test_error_handling_in_workflow(orchestrator, mock_task_store):
    """Test error handling in various workflow scenarios."""
    # Arrange
    mock_task_store.get_task.return_value = None
    
    # Act & Assert
    with pytest.raises(ValueError, match="Task not found"):
        await orchestrator.assign_agent("nonexistent-task", "B-Qwen")
    
    with pytest.raises(ValueError, match="Task not found"):
        await orchestrator.merge_results("nonexistent-task")


@pytest.mark.asyncio
async def test_agent_initialization(orchestrator):
    """Test that default agents are initialized correctly."""
    # Act
    agents = orchestrator.list_agents()
    
    # Assert
    assert len(agents) == 3
    agent_ids = [agent.id for agent in agents]
    assert "A-Kimi" in agent_ids
    assert "B-Qwen" in agent_ids
    assert "C-Mimo" in agent_ids


@pytest.mark.asyncio
async def test_get_agent(orchestrator):
    """Test getting a specific agent."""
    # Act
    agent = orchestrator.get_agent("A-Kimi")
    
    # Assert
    assert agent is not None
    assert agent.id == "A-Kimi"
    assert agent.name == "Agent A (Planner)"
    assert agent.model == "kimi-k2.7-code"
    assert agent.role == "planner"


@pytest.mark.asyncio
async def test_get_nonexistent_agent(orchestrator):
    """Test getting a nonexistent agent."""
    # Act
    agent = orchestrator.get_agent("nonexistent-agent")
    
    # Assert
    assert agent is None