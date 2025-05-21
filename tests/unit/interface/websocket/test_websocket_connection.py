"""
Unit tests for WebSocket connection management.
"""
import typing as t
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import WebSocket, WebSocketDisconnect

from src.interface.websocket.websocket_manager import ConnectionManager


class TestConnectionManager:
    """
    Test the ConnectionManager class for WebSocket connections.
    """

    @pytest.fixture
    def connection_manager(self):
        """Create a ConnectionManager instance for testing."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.close = AsyncMock()
        websocket.send_json = AsyncMock()
        return websocket

    @pytest.fixture
    def user_id(self):
        """Create a test user ID."""
        return uuid.UUID("00000000-0000-0000-0000-000000000001")

    @patch("src.interface.websocket.websocket_manager.add_connection")
    async def test_connect(self, mock_add_connection, connection_manager, mock_websocket, user_id):
        """Test connecting a WebSocket."""
        # Set up the mock to return a fixed value for add_connection
        mock_add_connection.return_value = 1

        # Connect the WebSocket
        connection_id = await connection_manager.connect(mock_websocket, user_id)

        # Verify accept was called
        mock_websocket.accept.assert_called_once()

        # Verify connections were stored correctly
        assert connection_id in connection_manager.active_connections
        assert connection_manager.active_connections[connection_id] == mock_websocket
        assert connection_manager.connection_to_user[connection_id] == user_id

        # Verify Redis connection tracking was called
        mock_add_connection.assert_called_once_with(user_id, connection_id)

    @patch("src.interface.websocket.websocket_manager.remove_connection")
    async def test_disconnect(self, mock_remove_connection, connection_manager, mock_websocket, user_id):
        """Test disconnecting a WebSocket."""
        # Set up the mock to return a fixed value for remove_connection
        mock_remove_connection.return_value = 1

        # Connect the WebSocket first
        with patch("src.interface.websocket.websocket_manager.add_connection", return_value=1):
            connection_id = await connection_manager.connect(mock_websocket, user_id)

        # Disconnect the WebSocket
        await connection_manager.disconnect(connection_id)

        # Verify connections were removed correctly
        assert connection_id not in connection_manager.active_connections
        assert connection_id not in connection_manager.connection_to_user

        # Verify Redis connection tracking was updated
        mock_remove_connection.assert_called_once_with(user_id, connection_id)

        # We no longer expect close to be called as per our implementation
        mock_websocket.close.assert_not_called()

    @patch("src.interface.websocket.websocket_manager.touch_connection")
    async def test_send_json(self, mock_touch_connection, connection_manager, mock_websocket, user_id):
        """Test sending a JSON message to a WebSocket."""
        # Connect the WebSocket first
        with patch("src.interface.websocket.websocket_manager.add_connection", return_value=1):
            connection_id = await connection_manager.connect(mock_websocket, user_id)

        # Send a message
        message = {"type": "test", "content": "Hello, world!"}
        result = await connection_manager.send_json(connection_id, message)

        # Verify message was sent
        assert result is True
        mock_websocket.send_json.assert_called_once_with(message)
        mock_touch_connection.assert_called_once_with(connection_id)

    @patch("src.interface.websocket.websocket_manager.touch_connection")
    async def test_send_json_connection_not_found(self, mock_touch_connection, connection_manager):
        """Test sending a JSON message to a non-existent connection."""
        # Send a message to a connection that doesn't exist
        message = {"type": "test", "content": "Hello, world!"}
        result = await connection_manager.send_json("non_existent_connection", message)

        # Verify the result is False
        assert result is False
        mock_touch_connection.assert_not_called()

    @patch("src.interface.websocket.websocket_manager.get_user_connections")
    @patch("src.interface.websocket.websocket_manager.touch_connection")
    async def test_broadcast_to_user(self, mock_touch_connection, mock_get_user_connections, 
                                   connection_manager, mock_websocket, user_id):
        """Test broadcasting a message to all connections of a user."""
        # Connect the WebSocket first
        with patch("src.interface.websocket.websocket_manager.add_connection", return_value=1):
            connection_id = await connection_manager.connect(mock_websocket, user_id)

        # Set up the mock to return our connection ID
        mock_get_user_connections.return_value = [connection_id]

        # Broadcast a message
        message = {"type": "broadcast", "content": "Hello, all!"}
        sent_count = await connection_manager.broadcast_to_user(user_id, message)

        # Verify message was sent and Redis was called
        assert sent_count == 1
        mock_websocket.send_json.assert_called_once_with(message)
        mock_get_user_connections.assert_called_once_with(user_id)
        mock_touch_connection.assert_called_once_with(connection_id)

    async def test_broadcast_to_chat(self, connection_manager):
        """Test broadcasting a message to all users in a chat."""
        # Create a patched version of broadcast_to_user method for testing
        connection_manager.broadcast_to_user = AsyncMock(return_value=1)
        
        # Create test data
        chat_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        user_ids = [
            uuid.UUID("00000000-0000-0000-0000-000000000001"),
            uuid.UUID("00000000-0000-0000-0000-000000000003"),
        ]
        message = {"type": "chat", "content": "Hello, chat!"}
        
        # Broadcast the message
        sent_count = await connection_manager.broadcast_to_chat(chat_id, message, user_ids)
        
        # Verify broadcasts were sent
        assert sent_count == 2
        assert connection_manager.broadcast_to_user.call_count == 2
        connection_manager.broadcast_to_user.assert_any_call(user_ids[0], message)
        connection_manager.broadcast_to_user.assert_any_call(user_ids[1], message)

    async def test_broadcast_to_chat_with_exclude(self, connection_manager):
        """Test broadcasting a message to all users in a chat excluding one user."""
        # Create a patched version of broadcast_to_user method for testing
        connection_manager.broadcast_to_user = AsyncMock(return_value=1)
        
        # Create test data
        chat_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        user_ids = [
            uuid.UUID("00000000-0000-0000-0000-000000000001"),
            uuid.UUID("00000000-0000-0000-0000-000000000003"),
        ]
        exclude_user_id = user_ids[0]
        message = {"type": "chat", "content": "Hello, chat!"}
        
        # Broadcast the message with exclusion
        sent_count = await connection_manager.broadcast_to_chat(
            chat_id, message, user_ids, exclude_user_id
        )
        
        # Verify broadcasts were sent correctly
        assert sent_count == 1
        assert connection_manager.broadcast_to_user.call_count == 1
        connection_manager.broadcast_to_user.assert_called_once_with(user_ids[1], message) 