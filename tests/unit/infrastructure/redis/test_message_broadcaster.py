"""
Unit tests for Redis message broadcaster implementation.
"""
import typing as t
import uuid
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.application.services.message_broadcaster import MessageBroadcaster
from src.infrastructure.redis.message_broadcaster import RedisMessageBroadcaster


class TestRedisMessageBroadcaster:
    """Tests for the RedisMessageBroadcaster implementation."""
    
    @pytest.fixture
    def broadcaster(self):
        """Create a message broadcaster for testing."""
        return RedisMessageBroadcaster()
    
    @patch("src.interface.websocket.websocket_manager.manager.broadcast_to_user")
    async def test_broadcast_to_user(self, mock_broadcast_to_user, broadcaster):
        """Test broadcasting a message to a user."""
        # Set up mocks
        mock_broadcast_to_user.return_value = 2
        
        # Set up test data
        user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        message = {"type": "test", "content": "Hello, user!"}
        
        # Call the method
        result = await broadcaster.broadcast_to_user(user_id, message)
        
        # Verify the result
        assert result == 2
        mock_broadcast_to_user.assert_called_once_with(user_id, message)
    
    @patch("src.interface.websocket.websocket_manager.manager.broadcast_to_chat")
    async def test_broadcast_to_chat(self, mock_broadcast_to_chat, broadcaster):
        """Test broadcasting a message to a chat."""
        # Set up mocks
        mock_broadcast_to_chat.return_value = 3
        
        # Set up test data
        chat_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        user_ids = [
            uuid.UUID("00000000-0000-0000-0000-000000000001"),
            uuid.UUID("00000000-0000-0000-0000-000000000003"),
        ]
        message = {"type": "chat", "content": "Hello, chat!"}
        
        # Call the method
        result = await broadcaster.broadcast_to_chat(chat_id, message, user_ids)
        
        # Verify the result
        assert result == 3
        mock_broadcast_to_chat.assert_called_once_with(chat_id, message, user_ids, None)
    
    @patch("src.interface.websocket.websocket_manager.manager.broadcast_to_chat")
    async def test_broadcast_to_chat_with_exclude(self, mock_broadcast_to_chat, broadcaster):
        """Test broadcasting a message to a chat with exclusion."""
        # Set up mocks
        mock_broadcast_to_chat.return_value = 2
        
        # Set up test data
        chat_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        user_ids = [
            uuid.UUID("00000000-0000-0000-0000-000000000001"),
            uuid.UUID("00000000-0000-0000-0000-000000000003"),
        ]
        exclude_user_id = user_ids[0]
        message = {"type": "chat", "content": "Hello, chat!"}
        
        # Call the method
        result = await broadcaster.broadcast_to_chat(chat_id, message, user_ids, exclude_user_id)
        
        # Verify the result
        assert result == 2
        mock_broadcast_to_chat.assert_called_once_with(chat_id, message, user_ids, exclude_user_id)
    
    async def test_add_to_queue(self, broadcaster):
        """Test adding a message to the queue."""
        # Create a patched version of add_to_list and set_key
        with patch("src.infrastructure.redis.message_broadcaster.add_to_list", 
                  new=AsyncMock(return_value=1)) as mock_add_to_list, \
             patch("src.infrastructure.redis.message_broadcaster.set_key", 
                  new=AsyncMock(return_value=True)) as mock_set_key:
            
            # Set up test data
            user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
            message = {"type": "queued", "content": "Hello, offline user!"}
            
            # Call the method
            result = await broadcaster.add_to_queue(user_id, message, ttl=3600)
            
            # Verify the result
            assert result is True
            
            # Verify the message was added to the list
            mock_add_to_list.assert_called_once()
            key = f"user:{user_id}:message_queue"
            
            # Check that the function was called with the right key and a JSON string
            call_args = mock_add_to_list.call_args[0]
            assert call_args[0] == key
            
            # The second argument should be a JSON string containing our message plus a timestamp
            message_json = call_args[1]
            message_dict = json.loads(message_json)
            assert message_dict["type"] == message["type"]
            assert message_dict["content"] == message["content"]
            assert "queued_at" in message_dict
            
            # Verify TTL was set
            mock_set_key.assert_called_once_with(f"{key}:ttl", "1", expiry=3600)
    
    async def test_get_queued_messages(self, broadcaster):
        """Test getting queued messages."""
        # Set up test data with our mocked messages
        messages = [
            json.dumps({"type": "queued", "content": "Message 1", "queued_at": "2023-01-01T12:00:00"}),
            json.dumps({"type": "queued", "content": "Message 2", "queued_at": "2023-01-01T12:01:00"}),
        ]
        
        # Create patched versions of all redis functions
        with patch("src.infrastructure.redis.message_broadcaster.get_list", 
                  new=AsyncMock(return_value=messages)) as mock_get_list, \
             patch("src.infrastructure.redis.message_broadcaster.delete_list", 
                  new=AsyncMock(return_value=1)) as mock_delete_list, \
             patch("src.infrastructure.redis.message_broadcaster.delete_key", 
                  new=AsyncMock(return_value=1)) as mock_delete_key:
            
            # Set up test data
            user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
            
            # Call the method
            result = await broadcaster.get_queued_messages(user_id)
            
            # Verify the result
            assert len(result) == 2
            assert result[0]["type"] == "queued"
            assert result[0]["content"] == "Message 1"
            assert result[0]["queued_at"] == "2023-01-01T12:00:00"
            assert result[1]["type"] == "queued"
            assert result[1]["content"] == "Message 2"
            assert result[1]["queued_at"] == "2023-01-01T12:01:00"
            
            # Verify Redis calls
            key = f"user:{user_id}:message_queue"
            mock_get_list.assert_called_once_with(key)
            mock_delete_list.assert_called_once_with(key)
            mock_delete_key.assert_called_once_with(f"{key}:ttl")
    
    async def test_get_queued_messages_invalid_json(self, broadcaster):
        """Test getting queued messages with some invalid JSON."""
        # Set up mocks with one valid message and one invalid message
        messages = [
            json.dumps({"type": "queued", "content": "Message 1", "queued_at": "2023-01-01T12:00:00"}),
            "invalid JSON",
        ]
        
        # Create patched versions of all redis functions
        with patch("src.infrastructure.redis.message_broadcaster.get_list", 
                  new=AsyncMock(return_value=messages)) as mock_get_list, \
             patch("src.infrastructure.redis.message_broadcaster.delete_list", 
                  new=AsyncMock(return_value=1)) as mock_delete_list, \
             patch("src.infrastructure.redis.message_broadcaster.delete_key", 
                  new=AsyncMock(return_value=1)) as mock_delete_key:
        
            # Set up test data
            user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
            
            # Call the method
            result = await broadcaster.get_queued_messages(user_id)
            
            # Verify the result - the valid message should still be processed
            assert len(result) == 1
            assert result[0]["type"] == "queued"
            assert result[0]["content"] == "Message 1"
            assert result[0]["queued_at"] == "2023-01-01T12:00:00" 