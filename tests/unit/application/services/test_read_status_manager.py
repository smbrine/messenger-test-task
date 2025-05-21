"""
Tests for the ReadStatusManager.
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.domain.models.message import Message, MessageStatus
from src.application.repositories.message_repository import MessageRepository
from src.application.services.message_broadcaster import MessageBroadcaster
from src.application.services.read_status_manager import ReadStatusManager


@pytest.fixture
def message_repository():
    """Create a mock message repository."""
    return AsyncMock(spec=MessageRepository)


@pytest.fixture
def message_broadcaster():
    """Create a mock message broadcaster."""
    return AsyncMock(spec=MessageBroadcaster)


@pytest.fixture
def read_status_manager(message_repository, message_broadcaster):
    """Create a read status manager with mock dependencies."""
    return ReadStatusManager(
        message_repository=message_repository,
        message_broadcaster=message_broadcaster
    )


@pytest.mark.asyncio
class TestReadStatusManager:
    """Test cases for the ReadStatusManager."""
    
    async def test_mark_as_read(self, read_status_manager, message_repository, message_broadcaster):
        """Test marking a message as read."""
        # Setup
        message_id = uuid.uuid4()
        user_id = uuid.uuid4()
        chat_id = uuid.uuid4()
        
        message_repository.update_read_status.return_value = True
        
        # Execute
        result = await read_status_manager.mark_as_read(
            message_id=message_id,
            user_id=user_id,
            chat_id=chat_id
        )
        
        # Verify
        assert result is True
        
        # Verify repository method was called
        message_repository.update_read_status.assert_called_once_with(
            message_id=message_id,
            user_id=user_id,
            read=True
        )
        
        # Verify broadcaster was called
        message_broadcaster.broadcast_to_chat.assert_called_once()
        
    async def test_mark_as_read_failed(self, read_status_manager, message_repository, message_broadcaster):
        """Test marking a message as read when it fails."""
        # Setup
        message_id = uuid.uuid4()
        user_id = uuid.uuid4()
        chat_id = uuid.uuid4()
        
        message_repository.update_read_status.return_value = False
        
        # Execute
        result = await read_status_manager.mark_as_read(
            message_id=message_id,
            user_id=user_id,
            chat_id=chat_id
        )
        
        # Verify
        assert result is False
        
        # Verify repository method was called
        message_repository.update_read_status.assert_called_once()
        
        # Verify broadcaster was NOT called
        message_broadcaster.broadcast_to_chat.assert_not_called()
    
    async def test_mark_multiple_as_read(self, read_status_manager, message_repository, message_broadcaster):
        """Test marking multiple messages as read."""
        # Setup
        message_ids = [uuid.uuid4() for _ in range(3)]
        user_id = uuid.uuid4()
        chat_id = uuid.uuid4()
        
        # Message repository should be called for each message
        message_repository.update_read_status.side_effect = [True, True, True]
        
        # Execute
        result = await read_status_manager.mark_multiple_as_read(
            message_ids=message_ids,
            user_id=user_id,
            chat_id=chat_id
        )
        
        # Verify
        assert result == 3  # All messages marked as read
        
        # Verify repository method was called for each message
        assert message_repository.update_read_status.call_count == 3
        
        # Verify broadcaster was called once with batch update
        message_broadcaster.broadcast_to_chat.assert_called_once()
        
    async def test_mark_all_as_read(self, read_status_manager, message_repository, message_broadcaster):
        """Test marking all messages in a chat as read."""
        # Setup
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        message_repository.mark_all_as_read.return_value = 5  # 5 messages marked as read
        
        # Execute
        result = await read_status_manager.mark_all_as_read(
            chat_id=chat_id,
            user_id=user_id
        )
        
        # Verify
        assert result == 5
        
        # Verify repository method was called
        message_repository.mark_all_as_read.assert_called_once_with(
            chat_id=chat_id,
            user_id=user_id
        )
        
        # Verify broadcaster was called
        message_broadcaster.broadcast_to_chat.assert_called_once()
    
    async def test_get_unread_count(self, read_status_manager, message_repository):
        """Test getting the count of unread messages in a chat."""
        # Setup
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        message_repository.get_unread_count.return_value = 3
        
        # Execute
        result = await read_status_manager.get_unread_count(
            chat_id=chat_id,
            user_id=user_id
        )
        
        # Verify
        assert result == 3
        
        # Verify repository method was called
        message_repository.get_unread_count.assert_called_once_with(
            chat_id=chat_id,
            user_id=user_id
        ) 