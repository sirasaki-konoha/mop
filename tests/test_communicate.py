"""
Tests for agent_communicate tool.

This module contains tests for the agent_communicate tool implementation.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.orchestrator.tools.communicate import agent_communicate, Message, MessageStore


@pytest.fixture
def mock_message_store():
    """Create a mock message store."""
    store = MagicMock(spec=MessageStore)
    store.add = MagicMock()
    store.get_inbox = MagicMock()
    store.get_sent = MagicMock()
    return store


@pytest.mark.asyncio
async def test_send_message_success(mock_message_store):
    """Test successful message sending between agents."""
    # Arrange
    from_agent = "agent-a"
    to_agent = "agent-b"
    message_type = "request"
    content = "Need clarification on API spec"
    task_id = "task-1"
    
    with patch('src.orchestrator.tools.communicate.get_message_store', return_value=mock_message_store):
        # Act
        result = await agent_communicate(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            task_id=task_id
        )
    
    # Assert
    assert result is not None
    assert result["from_agent"] == from_agent
    assert result["to_agent"] == to_agent
    assert result["message_type"] == message_type
    assert result["content"] == content
    assert result["task_id"] == task_id
    mock_message_store.add.assert_called_once()


@pytest.mark.asyncio
async def test_send_message_without_task_id(mock_message_store):
    """Test sending a message without a task ID."""
    # Arrange
    from_agent = "agent-a"
    to_agent = "agent-b"
    message_type = "question"
    content = "General question about architecture"
    
    with patch('src.orchestrator.tools.communicate.get_message_store', return_value=mock_message_store):
        # Act
        result = await agent_communicate(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            task_id=None
        )
    
    # Assert
    assert result is not None
    assert result["task_id"] is None


@pytest.mark.asyncio
async def test_send_message_invalid_type():
    """Test sending a message with invalid type."""
    # Arrange
    from_agent = "agent-a"
    to_agent = "agent-b"
    message_type = "invalid_type"
    content = "Test message"
    
    # Act & Assert
    with pytest.raises(ValueError, match="Invalid message_type"):
        await agent_communicate(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            task_id=None
        )


@pytest.mark.asyncio
async def test_send_message_empty_from_agent():
    """Test sending a message with empty from_agent."""
    # Arrange
    from_agent = ""
    to_agent = "agent-b"
    message_type = "request"
    content = "Test message"
    
    # Act & Assert
    with pytest.raises(ValueError, match="from_agent must not be empty"):
        await agent_communicate(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            task_id=None
        )


@pytest.mark.asyncio
async def test_send_message_empty_to_agent():
    """Test sending a message with empty to_agent."""
    # Arrange
    from_agent = "agent-a"
    to_agent = ""
    message_type = "request"
    content = "Test message"
    
    # Act & Assert
    with pytest.raises(ValueError, match="to_agent must not be empty"):
        await agent_communicate(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            task_id=None
        )


@pytest.mark.asyncio
async def test_send_message_empty_content():
    """Test sending a message with empty content."""
    # Arrange
    from_agent = "agent-a"
    to_agent = "agent-b"
    message_type = "request"
    content = ""
    
    # Act & Assert
    with pytest.raises(ValueError, match="content must not be empty"):
        await agent_communicate(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            task_id=None
        )


@pytest.mark.asyncio
async def test_send_message_stores_message(mock_message_store):
    """Test that message is stored in the message store."""
    # Arrange
    from_agent = "agent-a"
    to_agent = "agent-b"
    message_type = "request"
    content = "Test message"
    
    with patch('src.orchestrator.tools.communicate.get_message_store', return_value=mock_message_store):
        # Act
        await agent_communicate(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            task_id=None
        )
    
    # Assert
    mock_message_store.add.assert_called_once()
    call_args = mock_message_store.add.call_args[0][0]
    assert isinstance(call_args, Message)
    assert call_args.from_agent == from_agent
    assert call_args.to_agent == to_agent
    assert call_args.content == content


@pytest.mark.asyncio
async def test_message_store_get_inbox(mock_message_store):
    """Test getting inbox messages for an agent."""
    # Arrange
    agent_id = "agent-b"
    expected_messages = [
        Message(
            id="msg-1",
            from_agent="agent-a",
            to_agent=agent_id,
            message_type="request",
            content="Message 1",
            task_id="task-1"
        ),
        Message(
            id="msg-2",
            from_agent="agent-c",
            to_agent=agent_id,
            message_type="review",
            content="Message 2",
            task_id="task-2"
        )
    ]
    mock_message_store.get_inbox.return_value = expected_messages
    
    # Act
    result = mock_message_store.get_inbox(agent_id)
    
    # Assert
    assert len(result) == 2
    assert all(msg.to_agent == agent_id for msg in result)
    mock_message_store.get_inbox.assert_called_once_with(agent_id)


@pytest.mark.asyncio
async def test_message_store_get_sent(mock_message_store):
    """Test getting sent messages for an agent."""
    # Arrange
    agent_id = "agent-a"
    expected_messages = [
        Message(
            id="msg-1",
            from_agent=agent_id,
            to_agent="agent-b",
            message_type="request",
            content="Message 1",
            task_id="task-1"
        )
    ]
    mock_message_store.get_sent.return_value = expected_messages
    
    # Act
    result = mock_message_store.get_sent(agent_id)
    
    # Assert
    assert len(result) == 1
    assert all(msg.from_agent == agent_id for msg in result)
    mock_message_store.get_sent.assert_called_once_with(agent_id)