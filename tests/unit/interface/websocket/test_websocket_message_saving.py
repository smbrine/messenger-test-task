"""
Tests for WebSocket message saving functionality.
"""
import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import WebSocket
from src.interface.websocket.websocket_routes import websocket_endpoint
from src.application.repositories.message_repository import MessageRepository
from src.domain.models.message import Message


class TestWebSocketMessageSaving:
    """Test cases for WebSocket message saving functionality."""
    
    @pytest.fixture
    def websocket(self):
        """Fixture for a mock WebSocket connection."""
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.receive_text = AsyncMock()
        mock_ws.send_json = AsyncMock()
        return mock_ws
    
    @pytest.fixture
    def user_id(self):
        """Fixture for a user ID."""
        return uuid.uuid4()
    
    @pytest.fixture
    def chat_id(self):
        """Fixture for a chat ID."""
        return uuid.uuid4()
    
    @pytest.fixture
    def message_id(self):
        """Fixture for a message ID."""
        return uuid.uuid4()
    
    @pytest.fixture
    def mock_message_repository(self):
        """Fixture for a mock message repository."""
        repo = AsyncMock(spec=MessageRepository)
        repo.create = AsyncMock(return_value=None)
        repo.update_read_status = AsyncMock(return_value=True)
        return repo
    
    @pytest.mark.asyncio
    @patch("src.interface.websocket.websocket_routes.authenticate_websocket")
    @patch("src.interface.websocket.websocket_routes.manager")
    @patch("src.interface.websocket.websocket_routes.get_message_broadcaster")
    @patch("src.interface.websocket.websocket_routes.get_chat_repository")
    @patch("src.interface.websocket.websocket_routes.get_message_repository")
    @patch("uuid.uuid4")
    async def test_chat_message_is_saved(
        self, 
        mock_uuid4,
        mock_get_message_repo,
        mock_get_chat_repo,
        mock_get_broadcaster,
        mock_manager,
        mock_authenticate,
        websocket,
        user_id,
        chat_id,
        message_id,
        mock_message_repository
    ):
        """Test that chat messages sent via WebSocket are saved to the message repository."""
        # Set up the mocks
        mock_authenticate.return_value = user_id
        
        # Make sure manager methods are async mocks
        mock_manager.connect = AsyncMock(return_value="connection-id")
        mock_manager.broadcast_to_chat = AsyncMock(return_value=0)
        mock_manager.disconnect = AsyncMock()
        
        # Set up broadcaster mock
        mock_broadcaster = AsyncMock()
        mock_broadcaster.get_queued_messages = AsyncMock(return_value=[])
        mock_get_broadcaster.return_value = mock_broadcaster
        
        # Mock the chat repository
        mock_chat_repo = AsyncMock()
        mock_chat_repo.get_by_id = AsyncMock(return_value=MagicMock(
            participants=[MagicMock(user_id=user_id)]
        ))
        mock_get_chat_repo.return_value = mock_chat_repo
        
        # Mock the message repository
        mock_get_message_repo.return_value = mock_message_repository
        
        # Set up the UUID mock
        mock_uuid4.return_value = message_id
        
        # Set up the message data
        chat_message = {
            "type": "chat",
            "chat_id": str(chat_id),
            "content": "Hello, world!"
        }
        
        # Set up the WebSocket to receive the message and then disconnect
        websocket.receive_text.side_effect = [
            json.dumps(chat_message),
            Exception("WebSocketDisconnect")  # Simulate disconnect after message
        ]
        
        # Call the WebSocket endpoint
        with pytest.raises(Exception, match="WebSocketDisconnect"):
            await websocket_endpoint(websocket)
        
        # Verify that the message repository was called with the correct message
        mock_message_repository.create.assert_called_once()
        
        # Get the actual call arguments
        call_args = mock_message_repository.create.call_args[0][0]
        
        # Assert message fields
        assert isinstance(call_args, Message)
        assert call_args.id == message_id
        assert call_args.chat_id == chat_id
        assert call_args.sender_id == user_id
        assert call_args.text == "Hello, world!"
        assert call_args.idempotency_key == f"ws_{message_id}"
    
    @pytest.mark.asyncio
    @patch("src.interface.websocket.websocket_routes.authenticate_websocket")
    @patch("src.interface.websocket.websocket_routes.manager")
    @patch("src.interface.websocket.websocket_routes.get_message_broadcaster")
    @patch("src.interface.websocket.websocket_routes.get_chat_repository")
    @patch("src.interface.websocket.websocket_routes.get_message_repository")
    async def test_read_receipt_updates_message_status(
        self, 
        mock_get_message_repo,
        mock_get_chat_repo,
        mock_get_broadcaster,
        mock_manager,
        mock_authenticate,
        websocket,
        user_id,
        message_id,
        mock_message_repository
    ):
        """Test that read receipts sent via WebSocket update message status in the repository."""
        # Set up the mocks
        mock_authenticate.return_value = user_id
        
        # Make sure manager methods are async mocks
        mock_manager.connect = AsyncMock(return_value="connection-id")
        mock_manager.disconnect = AsyncMock()
        
        # Set up broadcaster mock
        mock_broadcaster = AsyncMock()
        mock_broadcaster.get_queued_messages = AsyncMock(return_value=[])
        mock_get_broadcaster.return_value = mock_broadcaster
        
        # Mock the chat repository
        mock_get_chat_repo.return_value = AsyncMock()
        
        # Mock the message repository
        mock_get_message_repo.return_value = mock_message_repository
        
        # Set up the message data
        read_receipt = {
            "type": "read",
            "message_id": str(message_id)
        }
        
        # Set up the WebSocket to receive the message and then disconnect
        websocket.receive_text.side_effect = [
            json.dumps(read_receipt),
            Exception("WebSocketDisconnect")  # Simulate disconnect after message
        ]
        
        # Call the WebSocket endpoint
        with pytest.raises(Exception, match="WebSocketDisconnect"):
            await websocket_endpoint(websocket)
        
        # Verify that the message repository was called to update read status
        mock_message_repository.update_read_status.assert_called_once_with(
            message_id=message_id,
            user_id=user_id,
            read=True
        ) 