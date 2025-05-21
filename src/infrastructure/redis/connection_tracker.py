"""
Redis-based connection tracker for WebSocket connections.
"""
import typing as t
import uuid

from src.infrastructure.redis.redis import (
    add_to_set,
    get_set_members,
    remove_from_set,
    set_key,
)

# Constants for key formats
USER_CONNECTIONS_KEY_FORMAT = "user:{user_id}:connections"
CONNECTION_TTL = 3600  # 1 hour TTL for inactive connections


async def add_connection(user_id: uuid.UUID, connection_id: str) -> int:
    """
    Add a connection ID to a user's connections set.
    
    Args:
        user_id: The UUID of the user
        connection_id: The unique ID of the connection
        
    Returns:
        The number of new connections added (0 or 1)
    """
    key = USER_CONNECTIONS_KEY_FORMAT.format(user_id=str(user_id))
    
    # Set TTL for the connection
    await set_key(
        f"connection:{connection_id}:last_active", 
        "active", 
        expiry=CONNECTION_TTL
    )
    
    return await add_to_set(key, connection_id)


async def remove_connection(user_id: uuid.UUID, connection_id: str) -> int:
    """
    Remove a connection ID from a user's connections set.
    
    Args:
        user_id: The UUID of the user
        connection_id: The unique ID of the connection
        
    Returns:
        The number of connections removed (0 or 1)
    """
    key = USER_CONNECTIONS_KEY_FORMAT.format(user_id=str(user_id))
    return await remove_from_set(key, connection_id)


async def get_user_connections(user_id: uuid.UUID) -> t.List[str]:
    """
    Get all active connection IDs for a user.
    
    Args:
        user_id: The UUID of the user
        
    Returns:
        A list of connection IDs
    """
    key = USER_CONNECTIONS_KEY_FORMAT.format(user_id=str(user_id))
    return await get_set_members(key)


async def touch_connection(connection_id: str) -> None:
    """
    Update the last active timestamp for a connection.
    
    Args:
        connection_id: The unique ID of the connection
    """
    await set_key(
        f"connection:{connection_id}:last_active", 
        "active", 
        expiry=CONNECTION_TTL
    ) 