"""
WebSocket connection management module.
"""
import typing as t
import uuid
import json
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect, status

from src.infrastructure.redis.connection_tracker import (
    add_connection,
    remove_connection,
    get_user_connections,
    touch_connection,
)
from src.interface.websocket.auth import authenticate_websocket

class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.
    """
    
    def __init__(self):
        # Store active WebSocket connections: {connection_id: WebSocket}
        self.active_connections: dict[str, WebSocket] = {}
        # Map connection IDs to user IDs: {connection_id: user_id}
        self.connection_to_user: dict[str, uuid.UUID] = {}
    
    async def connect(
        self, websocket: WebSocket, user_id: uuid.UUID
    ) -> str:
        """
        Connect a WebSocket and associate it with a user.
        
        Args:
            websocket: The WebSocket connection
            user_id: The UUID of the user
            
        Returns:
            The unique connection ID
        """
        # The user is already authenticated by the caller, so we just accept the connection
        await websocket.accept()
        
        # Generate a unique connection ID
        connection_id = str(uuid.uuid4())
        
        # Store the connection
        self.active_connections[connection_id] = websocket
        self.connection_to_user[connection_id] = user_id
        
        # Track the connection in Redis
        await add_connection(user_id, connection_id)
        
        return connection_id
    
    async def disconnect(self, connection_id: str) -> None:
        """
        Disconnect a WebSocket by its connection ID.
        
        Args:
            connection_id: The unique ID of the connection
        """
        if connection_id in self.active_connections:
            # Get the user ID associated with this connection
            user_id = self.connection_to_user.get(connection_id)
            
            # Remove from active connections
            websocket = self.active_connections.pop(connection_id)
            self.connection_to_user.pop(connection_id, None)
            
            # Remove from Redis if we have the user ID
            if user_id:
                await remove_connection(user_id, connection_id)
            
            # Do not close the WebSocket here, as it might already be closed or
            # will be closed by the caller
    
    async def send_json(self, connection_id: str, message: dict) -> bool:
        """
        Send a JSON message to a specific connection.
        
        Args:
            connection_id: The unique ID of the connection
            message: The message to send as a dictionary
            
        Returns:
            True if message was sent, False otherwise
        """
        if connection_id not in self.active_connections:
            return False
        
        websocket = self.active_connections[connection_id]
        try:
            await websocket.send_json(message)
            await touch_connection(connection_id)
            return True
        except RuntimeError:
            # Connection might be closed
            await self.disconnect(connection_id)
            return False
    
    async def broadcast_to_user(
        self, user_id: uuid.UUID, message: dict
    ) -> int:
        """
        Broadcast a message to all connections of a user.
        
        Args:
            user_id: The UUID of the user
            message: The message to broadcast as a dictionary
            
        Returns:
            The number of connections that received the message
        """
        # Get all connection IDs for this user
        connection_ids = await get_user_connections(user_id)
        
        sent_count = 0
        for connection_id in connection_ids:
            if await self.send_json(connection_id, message):
                sent_count += 1
                
        return sent_count
    
    async def broadcast_to_chat(
        self, 
        chat_id: uuid.UUID, 
        message: dict,
        user_ids: t.List[uuid.UUID],
        exclude_user_id: t.Optional[uuid.UUID] = None,
    ) -> int:
        """
        Broadcast a message to all users in a chat.
        
        Args:
            chat_id: The UUID of the chat
            message: The message to broadcast as a dictionary
            user_ids: List of user IDs in the chat
            exclude_user_id: Optional user ID to exclude from broadcasting
            
        Returns:
            The number of connections that received the message
        """
        sent_count = 0
        
        for user_id in user_ids:
            # Skip excluded user
            if exclude_user_id and user_id == exclude_user_id:
                continue
                
            sent_count += await self.broadcast_to_user(user_id, message)
                
        return sent_count


# Global connection manager instance
manager = ConnectionManager() 