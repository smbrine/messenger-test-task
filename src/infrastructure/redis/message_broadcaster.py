"""
Redis-based implementation of message broadcaster service.
"""
import typing as t
import uuid
import json
from datetime import datetime

from src.application.services.message_broadcaster import MessageBroadcaster
from src.config.settings import get_settings
from src.interface.websocket.websocket_manager import manager
from src.infrastructure.redis.redis import set_key, get_key, delete_key, add_to_list, get_list, delete_list


class RedisMessageBroadcaster(MessageBroadcaster):
    """
    Redis-based implementation of the message broadcaster service.
    """
    
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
        # Use the WebSocket manager to broadcast the message
        return await manager.broadcast_to_user(user_id, message)
    
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
        # Use the WebSocket manager to broadcast the message
        return await manager.broadcast_to_chat(chat_id, message, user_ids, exclude_user_id)
    
    async def add_to_queue(
        self, 
        user_id: uuid.UUID, 
        message: dict,
        ttl: t.Optional[int] = None
    ) -> bool:
        """
        Add a message to the queue for a user who is currently offline.
        
        Args:
            user_id: The UUID of the user
            message: The message to queue as a dictionary
            ttl: Optional time-to-live in seconds (after which message expires)
            
        Returns:
            True if the message was added to the queue, False otherwise
        """
        # Add timestamp to the message
        message["queued_at"] = datetime.now().isoformat()
        
        # Serialize the message to JSON
        serialized_message = json.dumps(message)
        
        settings = get_settings()
        # Create the key for this user's message queue
        key = settings.redis.message_queue_key_format.format(user_id=str(user_id))
        
        # Add the message to the list
        await add_to_list(key, serialized_message)
        
        # Set expiry on the key if TTL is provided
        settings = get_settings()
        
        if ttl is not None:
            await set_key(f"{key}:ttl", "1", expiry=ttl)
        elif settings.redis.default_queue_ttl > 0:
            await set_key(f"{key}:ttl", "1", expiry=settings.redis.default_queue_ttl)
        
        return True
    
    async def get_queued_messages(
        self, user_id: uuid.UUID
    ) -> t.List[dict]:
        """
        Get all queued messages for a user and clear the queue.
        
        Args:
            user_id: The UUID of the user
            
        Returns:
            A list of queued messages
        """
        # Create the key for this user's message queue
        settings = get_settings()
        key = settings.redis.message_queue_key_format.format(user_id=str(user_id))
        
        # Get all messages from the list
        serialized_messages = await get_list(key)
        
        # Delete the list and TTL key
        await delete_list(key)
        await delete_key(f"{key}:ttl")
        
        # Deserialize the messages
        messages = []
        for serialized_message in serialized_messages:
            try:
                message = json.loads(serialized_message)
                messages.append(message)
            except json.JSONDecodeError:
                # Skip invalid messages
                continue
        
        return messages


# Factory function for creating a message broadcaster
async def get_message_broadcaster() -> MessageBroadcaster:
    """
    Get a message broadcaster instance.
    """
    return RedisMessageBroadcaster() 