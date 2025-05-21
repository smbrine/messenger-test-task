"""
Message repository interface.
"""
import typing as t
from datetime import datetime
from uuid import UUID
from abc import ABC, abstractmethod

from src.domain.models.message import Message, MessageStatus


class MessageRepository(ABC):
    """
    Interface for message repository implementations.
    Defines the contract for message data access operations.
    """
    
    @abstractmethod
    async def create(self, message: Message) -> Message:
        """
        Create a new message in the repository.
        
        Args:
            message: The message to create
            
        Returns:
            The created message with any system-generated fields populated
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, message_id: UUID) -> t.Optional[Message]:
        """
        Retrieve a message by ID.
        
        Args:
            message_id: The UUID of the message to retrieve
            
        Returns:
            The message if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_chat_messages(
        self, 
        chat_id: UUID, 
        limit: int = 50,
        before_id: t.Optional[UUID] = None
    ) -> t.List[Message]:
        """
        Get messages for a chat with pagination.
        
        Retrieves messages in a chat, ordered by creation time (newest first),
        with optional pagination using a message ID as a cursor.
        
        Args:
            chat_id: The UUID of the chat
            limit: Maximum number of messages to return
            before_id: The ID of the message before which to start the pagination

        Returns:
            A list of messages in the chat
        """
        pass
    
    @abstractmethod
    async def find_by_idempotency_key(
        self, 
        chat_id: UUID, 
        sender_id: UUID, 
        idempotency_key: str
    ) -> t.Optional[Message]:
        """
        Find a message by its idempotency key.
        
        Used to prevent duplicate message creation during retries.
        
        Args:
            chat_id: The UUID of the chat
            sender_id: The UUID of the message sender
            idempotency_key: The idempotency key to search for
            
        Returns:
            The message if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def update_read_status(
        self, 
        message_id: UUID, 
        user_id: UUID, 
        read: bool = True
    ) -> bool:
        """
        Update read status for a message.
        
        Args:
            message_id: The UUID of the message
            user_id: The UUID of the user
            read: The new read status
            
        Returns:
            True if the status was updated, False if the message doesn't exist or user is not a participant
        """
        pass
    
    @abstractmethod
    async def get_unread_count(
        self, 
        chat_id: UUID, 
        user_id: UUID
    ) -> int:
        """
        Get count of unread messages in a chat for a user.
        
        Args:
            chat_id: The UUID of the chat
            user_id: The UUID of the user
            
        Returns:
            The count of unread messages
        """
        pass
    
    @abstractmethod
    async def mark_all_as_read(
        self,
        chat_id: UUID,
        user_id: UUID
    ) -> int:
        """
        Mark all messages in a chat as read for a user.
        
        Args:
            chat_id: The UUID of the chat
            user_id: The UUID of the user
            
        Returns:
            The number of messages marked as read
        """
        pass 