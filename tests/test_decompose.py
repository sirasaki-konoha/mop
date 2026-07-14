"""
Tests for decompose_task tool.

This module contains tests for the decompose_task tool implementation.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.orchestrator.tools.decompose import DecomposeTool
from src.orchestrator.models.task import Task, TaskStatus


@pytest.fixture
def mock_task_store():
    """Create a mock task store."""
    store = MagicMock()
    store.create_task = MagicMock()
    store.update_task = MagicMock()
    return store


@pytest.fixture
def decompose_tool(mock_task_store):
    """Create a decompose tool instance with mock store."""
    return DecomposeTool(task_store=mock_task_store)


@pytest.mark.asyncio
async def test_decompose_task_returns_root_task(decompose_tool, mock_task_store):
    """Test that decompose_task returns a root task with subtasks."""
    # Arrange
    request = "Implement a REST API for user management"
    
    # Act
    result = await decompose_tool.decompose_task(request)
    
    # Assert
    assert result is not None
    assert result.description == request
    assert result.status == TaskStatus.PENDING
    assert len(result.subtasks) > 0
    mock_task_store.create_task.assert_called()
    mock_task_store.update_task.assert_called_once()


@pytest.mark.asyncio
async def test_decompose_task_with_empty_request(decompose_tool):
    """Test that decompose_task raises error for empty request."""
    # Arrange
    request = ""
    
    # Act & Assert
    with pytest.raises(ValueError, match="Request cannot be empty"):
        await decompose_tool.decompose_task(request)


@pytest.mark.asyncio
async def test_decompose_task_creates_subtasks(decompose_tool, mock_task_store):
    """Test that decompose_task creates appropriate subtasks."""
    # Arrange
    request = "Create a user authentication system"
    
    # Act
    result = await decompose_tool.decompose_task(request)
    
    # Assert
    assert result is not None
    # Verify that subtasks were created (specific number depends on implementation)
    assert len(result.subtasks) >= 2  # Should have at least 2 subtasks


@pytest.mark.asyncio
async def test_decompose_task_sets_correct_status(decompose_tool, mock_task_store):
    """Test that decompose_task sets correct initial status."""
    # Arrange
    request = "Build a notification service"
    
    # Act
    result = await decompose_tool.decompose_task(request)
    
    # Assert
    assert result.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_decompose_task_with_complex_request(decompose_tool, mock_task_store):
    """Test decompose_task with a complex multi-component request."""
    # Arrange
    request = """
    Implement a microservice architecture with:
    1. User service
    2. Product service
    3. Order service
    4. API Gateway
    """
    
    # Act
    result = await decompose_tool.decompose_task(request)
    
    # Assert
    assert result is not None
    assert len(result.subtasks) >= 4  # Should have at least 4 subtasks


@pytest.mark.asyncio
async def test_decompose_task_with_single_item(decompose_tool, mock_task_store):
    """Test decompose_task with a single item request."""
    # Arrange
    request = "Implement user authentication"
    
    # Act
    result = await decompose_tool.decompose_task(request)
    
    # Assert
    assert result is not None
    assert len(result.subtasks) == 4  # Should use default template


@pytest.mark.asyncio
async def test_decompose_task_with_comma_separated(decompose_tool, mock_task_store):
    """Test decompose_task with comma-separated items."""
    # Arrange
    request = "Design API, Implement models, Write tests"
    
    # Act
    result = await decompose_tool.decompose_task(request)
    
    # Assert
    assert result is not None
    assert len(result.subtasks) == 3