"""
Integration tests for WebSocket endpoints.
"""
import typing as t
import json
import uuid
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.interface.main import create_app
from src.interface.websocket.auth import validate_token
from src.domain.models.chat import Chat, ChatParticipant, ChatType


class TestWebSocketEndpoint:
    """Test cases for WebSocket endpoints."""
    
    @pytest.fixture
    def app(self, redis_container):
        """Create a FastAPI app for testing."""
        return create_app()
    
    @pytest.fixture
    def client(self, app):
        """Create a test client for FastAPI."""
        return TestClient(app)
    
    @pytest.fixture
    def user_id(self):
        """Create a test user ID."""
        return uuid.UUID("00000000-0000-0000-0000-000000000001")
    
    @pytest.fixture
    def valid_token(self):
        """Create a valid token for testing."""
        return "valid_token"
    
    @pytest.fixture
    def mock_chat(self, user_id):
        """Create a mock chat for testing."""
        chat_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        
        # Create participants for the chat
        participants = [
            ChatParticipant(user_id=user_id, role="admin"),
            ChatParticipant(user_id=uuid.UUID("00000000-0000-0000-0000-000000000003"), role="member")
        ]
        
        # Create a chat
        return Chat(
            id=chat_id,
            name="Test Chat",
            type=ChatType.PRIVATE,
            participants=participants
        )
    
    @patch("src.interface.websocket.auth.validate_token")
    @patch("src.infrastructure.repositories.chat_repository.SQLAlchemyChatRepository.get_by_id")
    @patch("src.interface.websocket.websocket_routes.get_chat_repository")
    @patch("src.interface.websocket.websocket_routes.get_message_broadcaster")
    @patch("src.interface.websocket.websocket_routes.get_message_repository")
    @patch("src.interface.websocket.websocket_manager.add_connection")
    @patch("src.interface.websocket.websocket_manager.touch_connection")
    def test_websocket_connection(
        self, 
        mock_touch, 
        mock_add_connection, 
        mock_get_message_repo,
        mock_get_broadcaster, 
        mock_get_repo, 
        mock_get_by_id, 
        mock_validate_token, 
        client, 
        user_id, 
        valid_token, 
        mock_chat, 
        redis_container
    ):
        """Test WebSocket connection with valid token."""
        # Mock Redis connections
        mock_add_connection.return_value = 1
        mock_touch.return_value = True
        
        # Mock repository and broadcaster
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_chat
        mock_get_repo.return_value = mock_repo
        
        # Mock message repository
        mock_message_repo = AsyncMock()
        mock_message_repo.create.return_value = None
        mock_message_repo.update_read_status.return_value = True
        mock_get_message_repo.return_value = mock_message_repo
        
        mock_broadcaster = AsyncMock()
        mock_broadcaster.get_queued_messages.return_value = []
        mock_get_broadcaster.return_value = mock_broadcaster
        
        # Mock token validation to return our test user ID
        mock_validate_token.return_value = user_id
        
        # Create a UUID for the message_id to use in tests
        test_message_id = uuid.uuid4()
        with patch('uuid.uuid4', return_value=test_message_id):
            # Connect to the WebSocket with a valid token
            with client.websocket_connect(f"/ws", headers={"cookie": f"token={valid_token}"}) as websocket:
                # We should receive a welcome message
                data = websocket.receive_json()
                assert data["type"] == "system"
                assert "Connected to WebSocket server" in data["message"]
                
                # Send a chat message
                message = {
                    "type": "chat",
                    "chat_id": str(mock_chat.id),
                    "content": "Hello, world!"
                }
                websocket.send_json(message)
                
                # We should receive confirmation back
                response = websocket.receive_json()
                assert response["type"] == "chat"
                assert response["chat_id"] == message["chat_id"]
                assert response["content"] == message["content"]
                assert response["sender_id"] == str(user_id)
                assert response["message_id"] == str(test_message_id)
                assert "status" in response
                assert response["status"] == "sent"
                
                # Verify message repository was called
                mock_message_repo.create.assert_called_once()
                
                # Send a typing notification
                typing_message = {
                    "type": "typing",
                    "chat_id": str(mock_chat.id),
                    "is_typing": True
                }
                websocket.send_json(typing_message)
                
                # We should receive confirmation back
                typing_response = websocket.receive_json()
                assert typing_response["type"] == "typing"
                assert typing_response["chat_id"] == typing_message["chat_id"]
                assert typing_response["is_typing"] == typing_message["is_typing"]
                assert typing_response["user_id"] == str(user_id)
                assert "status" in typing_response
                assert typing_response["status"] == "sent"
                
                # Send a read receipt
                read_message = {
                    "type": "read",
                    "message_id": str(test_message_id)
                }
                websocket.send_json(read_message)
                
                # We should receive confirmation back
                read_response = websocket.receive_json()
                assert read_response["type"] == "read"
                assert read_response["message_id"] == str(test_message_id)
                assert read_response["user_id"] == str(user_id)
                assert "status" in read_response
                assert read_response["status"] == "received"
                
                # Verify read status was updated
                mock_message_repo.update_read_status.assert_called_once_with(
                    message_id=test_message_id,
                    user_id=user_id,
                    read=True
                )
    
    @patch("src.interface.websocket.auth.validate_token")
    def test_websocket_invalid_token(self, mock_validate_token, client):
        """Test WebSocket connection with invalid token."""
        # Mock token validation to return None (invalid token)
        mock_validate_token.return_value = None
        
        # Attempt to connect with an invalid token
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?token=invalid_token") as websocket:
                # This should fail with a 1008 policy violation
                pass
    
    @patch("src.interface.websocket.auth.validate_token")
    @patch("src.interface.websocket.websocket_routes.get_chat_repository")
    @patch("src.interface.websocket.websocket_routes.get_message_broadcaster")
    @patch("src.interface.websocket.websocket_routes.get_message_repository")
    @patch("src.interface.websocket.websocket_manager.add_connection")
    @patch("src.interface.websocket.websocket_manager.touch_connection")
    @patch("src.interface.websocket.websocket_manager.get_user_connections")
    def test_websocket_invalid_message(
        self, 
        mock_get_connections, 
        mock_touch, 
        mock_add_connection, 
        mock_get_message_repo,
        mock_get_broadcaster, 
        mock_get_repo, 
        mock_validate_token, 
        client, 
        user_id, 
        valid_token, 
        redis_container
    ):
        """Test sending invalid message format."""
        # Mock Redis connections
        mock_add_connection.return_value = 1
        mock_touch.return_value = True
        mock_get_connections.return_value = []
        
        # Mock repository and broadcaster
        mock_repo = AsyncMock()
        mock_get_repo.return_value = mock_repo
        
        # Mock message repository
        mock_message_repo = AsyncMock()
        mock_get_message_repo.return_value = mock_message_repo
        
        mock_broadcaster = AsyncMock()
        mock_broadcaster.get_queued_messages.return_value = []
        mock_get_broadcaster.return_value = mock_broadcaster
        
        # Mock token validation to return our test user ID
        mock_validate_token.return_value = user_id
        
        # Connect to the WebSocket with a valid token
        with client.websocket_connect(f"/ws", headers={"cookie": f"token={valid_token}"}) as websocket:
            # Receive welcome message
            websocket.receive_json()
            
            # Send an invalid JSON message
            websocket.send_text("This is not JSON")
            
            # We should receive an error
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Invalid JSON" in response["message"]
            
            # Send a message with missing required fields
            websocket.send_json({"type": "chat"})
            
            # We should receive an error
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Missing required fields" in response["message"]
    
    @patch("src.interface.websocket.auth.validate_token")
    @patch("src.interface.websocket.websocket_routes.get_chat_repository")
    @patch("src.interface.websocket.websocket_routes.get_message_broadcaster")
    @patch("src.interface.websocket.websocket_routes.get_message_repository")
    @patch("src.interface.websocket.websocket_manager.add_connection")
    @patch("src.interface.websocket.websocket_manager.touch_connection")
    @patch("src.interface.websocket.websocket_manager.get_user_connections")
    def test_websocket_chat_not_found(
        self, 
        mock_get_connections, 
        mock_touch, 
        mock_add_connection, 
        mock_get_message_repo,
        mock_get_broadcaster, 
        mock_get_repo, 
        mock_validate_token, 
        client, 
        user_id, 
        valid_token, 
        redis_container
    ):
        """Test sending a message to a non-existent chat."""
        # Mock Redis connections
        mock_add_connection.return_value = 1
        mock_touch.return_value = True
        mock_get_connections.return_value = []
        
        # Mock repository and broadcaster
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        mock_get_repo.return_value = mock_repo
        
        # Mock message repository
        mock_message_repo = AsyncMock()
        mock_get_message_repo.return_value = mock_message_repo
        
        mock_broadcaster = AsyncMock()
        mock_broadcaster.get_queued_messages.return_value = []
        mock_get_broadcaster.return_value = mock_broadcaster
        
        # Mock token validation to return our test user ID
        mock_validate_token.return_value = user_id
        
        # Connect to the WebSocket with a valid token
        with client.websocket_connect(f"/ws", headers={"cookie": f"token={valid_token}"}) as websocket:
            # Receive welcome message
            websocket.receive_json()
            
            # Send a chat message to a non-existent chat
            message = {
                "type": "chat",
                "chat_id": str(uuid.uuid4()),
                "content": "Hello, world!"
            }
            websocket.send_json(message)
            
            # We should receive an error
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Chat not found" in response["message"]
            
            # Send a typing notification to a non-existent chat
            typing_message = {
                "type": "typing",
                "chat_id": str(uuid.uuid4()),
                "is_typing": True
            }
            websocket.send_json(typing_message)
            
            # We should receive an error
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Chat not found" in response["message"]
    
    @patch("src.interface.websocket.auth.validate_token")
    @patch("src.interface.websocket.websocket_routes.get_chat_repository")
    @patch("src.interface.websocket.websocket_routes.get_message_broadcaster")
    @patch("src.interface.websocket.websocket_routes.get_message_repository")
    @patch("src.interface.websocket.websocket_manager.add_connection")
    @patch("src.interface.websocket.websocket_manager.touch_connection")
    @patch("src.interface.websocket.websocket_manager.get_user_connections")
    def test_websocket_user_not_in_chat(
        self, 
        mock_get_connections, 
        mock_touch, 
        mock_add_connection, 
        mock_get_message_repo,
        mock_get_broadcaster, 
        mock_get_repo, 
        mock_validate_token, 
        client, 
        user_id, 
        valid_token, 
        redis_container
    ):
        """Test sending a message to a chat the user is not a member of."""
        # Mock Redis connections
        mock_add_connection.return_value = 1
        mock_touch.return_value = True
        mock_get_connections.return_value = []
        
        # Create a chat where the user is not a participant
        other_user_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
        chat_id = uuid.UUID("00000000-0000-0000-0000-000000000004")
        participants = [
            ChatParticipant(user_id=other_user_id, role="admin"),
            ChatParticipant(user_id=uuid.UUID("00000000-0000-0000-0000-000000000005"), role="member")
        ]
        mock_chat = Chat(
            id=chat_id,
            name="Test Chat",
            type=ChatType.GROUP,
            participants=participants
        )
        
        # Mock repository and broadcaster
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_chat
        mock_get_repo.return_value = mock_repo
        
        # Mock message repository
        mock_message_repo = AsyncMock()
        mock_get_message_repo.return_value = mock_message_repo
        
        mock_broadcaster = AsyncMock()
        mock_broadcaster.get_queued_messages.return_value = []
        mock_get_broadcaster.return_value = mock_broadcaster
        
        # Mock token validation to return our test user ID
        mock_validate_token.return_value = user_id
        
        # Connect to the WebSocket with a valid token
        with client.websocket_connect(f"/ws", headers={"cookie": f"token={valid_token}"}) as websocket:
            # Receive welcome message
            websocket.receive_json()
            
            # Send a chat message to a chat the user is not a member of
            message = {
                "type": "chat",
                "chat_id": str(chat_id),
                "content": "Hello, world!"
            }
            websocket.send_json(message)
            
            # We should receive an error
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "not a member of this chat" in response["message"]
            
            # Send a typing notification to a chat the user is not a member of
            typing_message = {
                "type": "typing",
                "chat_id": str(chat_id),
                "is_typing": True
            }
            websocket.send_json(typing_message)
            
            # We should receive an error
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "not a member of this chat" in response["message"] 