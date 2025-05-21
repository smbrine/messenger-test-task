"""
Message broadcaster service for WebSocket communication.
"""
import typing as t
import uuid
import abc


class MessageBroadcaster(abc.ABC):
    """
    Interface for message broadcasting services used for WebSocket communication.
    """
    
    @abc.abstractmethod
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
        pass
    
    @abc.abstractmethod
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
        pass
    
    @abc.abstractmethod
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
        pass
    
    @abc.abstractmethod
    async def get_queued_messages(
        self, user_id: uuid.UUID
    ) -> t.List[dict]:
        """
        Get all queued messages for a user.
        
        Args:
            user_id: The UUID of the user
            
        Returns:
            A list of queued messages
        """
        pass 