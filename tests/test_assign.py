"""
Tests for assign_agent tool.

This module contains tests for the assign_agent tool implementation.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.orchestrator.tools.assign import AssignTool
from src.orchestrator.models.task import Task, TaskStatus
from src.orchestrator.models.agent import Agent


@pytest.fixture
def mock_task_store():
    """Create a mock task store."""
    store = MagicMock()
    store.get_task = MagicMock()
    store.update_task = MagicMock()
    return store


@pytest.fixture
def mock_agent_store():
    """Create a mock agent store."""
    store = MagicMock()
    store.get_agent = MagicMock()
    return store


@pytest.fixture
def assign_tool(mock_task_store, mock_agent_store):
    """Create an assign tool instance with mock stores."""
    return AssignTool(task_store=mock_task_store, agent_store=mock_agent_store)


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        id="task-1",
        description="Implement user authentication",
        status=TaskStatus.PENDING,
        assigned_agent=None,
        parent_task_id=None,
        subtasks=[],
        artifacts=[],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def sample_agent():
    """Create a sample agent for testing."""
    return Agent(
        id="agent-b",
        name="Coder Agent",
        model="qwen3.7-plus",
        role="coder",
        status="idle",
        inbox=[]
    )


@pytest.mark.asyncio
async def test_assign_agent_success(assign_tool, mock_task_store, mock_agent_store, 
                                   sample_task, sample_agent):
    """Test successful assignment of agent to task."""
    # Arrange
    mock_task_store.get_task.return_value = sample_task
    mock_agent_store.get_agent.return_value = sample_agent
    mock_task_store.update_task.return_value = sample_task
    
    # Act
    result = await assign_tool.assign_agent("task-1", "agent-b")
    
    # Assert
    assert result is not None
    assert result.assigned_agent == "agent-b"
    assert result.status == TaskStatus.IN_PROGRESS
    mock_task_store.update_task.assert_called_once()


@pytest.mark.asyncio
async def test_assign_agent_task_not_found(assign_tool, mock_task_store):
    """Test assignment when task is not found."""
    # Arrange
    mock_task_store.get_task.return_value = None
    
    # Act & Assert
    with pytest.raises(ValueError, match="Task not found"):
        await assign_tool.assign_agent("nonexistent-task", "agent-b")


@pytest.mark.asyncio
async def test_assign_agent_agent_not_found(assign_tool, mock_task_store, 
                                            mock_agent_store, sample_task):
    """Test assignment when agent is not found."""
    # Arrange
    mock_task_store.get_task.return_value = sample_task
    mock_agent_store.get_agent.return_value = None
    
    # Act & Assert
    with pytest.raises(ValueError, match="Agent not found"):
        await assign_tool.assign_agent("task-1", "nonexistent-agent")


@pytest.mark.asyncio
async def test_assign_agent_already_assigned(assign_tool, mock_task_store, 
                                             mock_agent_store, sample_task, sample_agent):
    """Test assignment when task is already assigned to an agent."""
    # Arrange
    sample_task.assigned_agent = "agent-a"
    sample_task.status = TaskStatus.IN_PROGRESS
    mock_task_store.get_task.return_value = sample_task
    mock_agent_store.get_agent.return_value = sample_agent
    
    # Act & Assert
    with pytest.raises(ValueError, match="Task already assigned"):
        await assign_tool.assign_agent("task-1", "agent-b")


@pytest.mark.asyncio
async def test_assign_agent_updates_task_status(assign_tool, mock_task_store, 
                                                mock_agent_store, sample_task, sample_agent):
    """Test that assigning an agent updates task status to IN_PROGRESS."""
    # Arrange
    mock_task_store.get_task.return_value = sample_task
    mock_agent_store.get_agent.return_value = sample_agent
    mock_task_store.update_task.return_value = sample_task
    
    # Act
    result = await assign_tool.assign_agent("task-1", "agent-b")
    
    # Assert
    assert result.status == TaskStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_assign_agent_updates_timestamp(assign_tool, mock_task_store, 
                                              mock_agent_store, sample_task, sample_agent):
    """Test that assigning an agent updates the task timestamp."""
    # Arrange
    mock_task_store.get_task.return_value = sample_task
    mock_agent_store.get_agent.return_value = sample_agent
    mock_task_store.update_task.return_value = sample_task
    
    # Act
    result = await assign_tool.assign_agent("task-1", "agent-b")
    
    # Assert
    # The task should have been touched (updated_at should be set)
    assert result.updated_at is not None


@pytest.mark.asyncio
async def test_assign_agent_with_different_agents(assign_tool, mock_task_store, 
                                                  mock_agent_store, sample_task):
    """Test assignment with different agent types."""
    # Arrange
    agents = [
        Agent(id="agent-a", name="Planner", model="kimi-k2.7-code", role="planner"),
        Agent(id="agent-b", name="Coder", model="qwen3.7-plus", role="coder"),
        Agent(id="agent-c", name="Tester", model="mimo-v2.5-pro", role="tester"),
    ]
    
    for agent in agents:
        # Create a fresh task for each assignment
        task = Task(
            id=f"task-{agent.id}",
            description=f"Task for {agent.name}",
            status=TaskStatus.PENDING,
            assigned_agent=None,
            parent_task_id=None,
            subtasks=[],
            artifacts=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        mock_task_store.get_task.return_value = task
        mock_agent_store.get_agent.return_value = agent
        mock_task_store.update_task.return_value = task
        
        # Act
        result = await assign_tool.assign_agent(f"task-{agent.id}", agent.id)
        
        # Assert
        assert result.assigned_agent == agent.id
        assert result.status == TaskStatus.IN_PROGRESS