"""
Unit tests for WebSocket authentication.
"""
import typing as t
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import WebSocket, WebSocketDisconnect, status

from src.interface.websocket.auth import authenticate_websocket


class TestWebSocketAuth:
    """Tests for WebSocket authentication functions."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.query_params = {}
        websocket.cookies = {}
        websocket.close = AsyncMock()
        return websocket
    
    @patch("src.interface.websocket.auth.validate_token")
    async def test_authenticate_websocket_with_query_param(self, mock_validate_token, mock_websocket):
        """Test authenticating a WebSocket with a token in query parameters."""
        # Set up test data
        test_token = "valid_token"
        test_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        mock_websocket.query_params["token"] = test_token
        
        # Set up mock to return a valid user ID
        mock_validate_token.return_value = test_user_id
        
        # Call the function
        result = await authenticate_websocket(mock_websocket)
        
        # Verify the result
        assert result == test_user_id
        mock_validate_token.assert_called_once_with(test_token)
        mock_websocket.close.assert_not_called()
    
    @patch("src.interface.websocket.auth.validate_token")
    async def test_authenticate_websocket_with_cookie(self, mock_validate_token, mock_websocket):
        """Test authenticating a WebSocket with a token in cookies."""
        # Set up test data
        test_token = "valid_token"
        test_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        mock_websocket.cookies["token"] = test_token
        
        # Set up mock to return a valid user ID
        mock_validate_token.return_value = test_user_id
        
        # Call the function
        result = await authenticate_websocket(mock_websocket)
        
        # Verify the result
        assert result == test_user_id
        mock_validate_token.assert_called_once_with(test_token)
        mock_websocket.close.assert_not_called()
    
    @patch("src.interface.websocket.auth.validate_token")
    async def test_authenticate_websocket_no_token(self, mock_validate_token, mock_websocket):
        """Test authenticating a WebSocket with no token."""
        # Call the function
        result = await authenticate_websocket(mock_websocket)
        
        # Verify the result
        assert result is None
        mock_validate_token.assert_not_called()
        mock_websocket.close.assert_called_once_with(code=status.WS_1008_POLICY_VIOLATION)
    
    @patch("src.interface.websocket.auth.validate_token")
    async def test_authenticate_websocket_invalid_token(self, mock_validate_token, mock_websocket):
        """Test authenticating a WebSocket with an invalid token."""
        # Set up test data
        test_token = "invalid_token"
        mock_websocket.query_params["token"] = test_token
        
        # Set up mock to return None (invalid token)
        mock_validate_token.return_value = None
        
        # Call the function
        result = await authenticate_websocket(mock_websocket)
        
        # Verify the result
        assert result is None
        mock_validate_token.assert_called_once_with(test_token)
        mock_websocket.close.assert_called_once_with(code=status.WS_1008_POLICY_VIOLATION) 