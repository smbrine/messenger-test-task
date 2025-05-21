"""
WebSocket authentication utilities.
"""
import typing as t
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import WebSocket, WebSocketDisconnect, status

from src.infrastructure.security.jwt_factory import get_jwt_service


async def validate_token(token: str) -> t.Optional[uuid.UUID]:
    """
    Validate a JWT token and extract the user ID.
    
    Args:
        token: The JWT token to validate
        
    Returns:
        The UUID of the user, or None if the token is invalid
    """
    jwt_service = get_jwt_service()
    return await jwt_service.validate_access_token(token)


async def authenticate_websocket(websocket: WebSocket) -> t.Optional[uuid.UUID]:
    """
    Authenticate a WebSocket connection using a JWT token.
    
    Args:
        websocket: The WebSocket connection
        
    Returns:
        The UUID of the authenticated user, or None if authentication failed
    """
    # Try to get token from the query parameters first
    token = websocket.query_params.get("token")
    
    # If not in query params, try cookies
    if not token and "token" in websocket.cookies:
        token = websocket.cookies.get("token")
    
    if not token:
        # No token provided
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    
    # Validate the token
    user_id = await validate_token(token)
    
    if not user_id:
        # Invalid token
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    
    return user_id 