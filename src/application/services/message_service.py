"""
Message service for managing messages and read status.
"""
import typing as t
import uuid
from datetime import datetime, timezone

from src.domain.models.message import Message
from src.application.repositories.message_repository import MessageRepository
from src.application.repositories.chat_repository import ChatRepository
from src.application.services.message_broadcaster import MessageBroadcaster


class MessageService:
    """
    Service for managing messages and read status.
    
    This service handles:
    - Sending messages with idempotency protection
    - Retrieving message history with pagination
    - Managing read status for messages
    - Broadcasting message events to connected users
    """
    
    def __init__(
        self,
        message_repository: MessageRepository,
        chat_repository: ChatRepository,
        message_broadcaster: MessageBroadcaster
    ):
        """
        Initialize the message service.
        
        Args:
            message_repository: Repository for message data access
            chat_repository: Repository for chat data access
            message_broadcaster: Service for broadcasting messages to users
        """
        self.message_repository = message_repository
        self.chat_repository = chat_repository
        self.message_broadcaster = message_broadcaster
    
    async def send_message(
        self,
        chat_id: uuid.UUID,
        sender_id: uuid.UUID,
        text: str,
        idempotency_key: str
    ) -> Message:
        """
        Send a message to a chat.
        
        This method handles:
        - Checking if the chat exists
        - Verifying the sender is a participant in the chat
        - Checking for duplicate messages using idempotency key
        - Creating and persisting the message
        - Broadcasting the message to chat participants
        
        Args:
            chat_id: The UUID of the chat to send the message to
            sender_id: The UUID of the message sender
            text: The text content of the message
            idempotency_key: A unique key to prevent duplicate message sending
        
        Returns:
            The created or existing message
            
        Raises:
            ValueError: If the chat doesn't exist or the sender is not a participant
        """
        # Verify the chat exists
        chat = await self.chat_repository.get_by_id(chat_id)
        if chat is None:
            raise ValueError(f"Chat not found: {chat_id}")
        
        # Verify the sender is a participant in the chat
        is_participant = False
        participant_ids = []
        for participant in chat.participants:
            participant_ids.append(participant.user_id)
            if participant.user_id == sender_id:
                is_participant = True
                break
        
        if not is_participant:
            raise ValueError(f"User is not a participant in this chat: {sender_id}")
        
        # Check for duplicate message using idempotency key
        existing_message = await self.message_repository.find_by_idempotency_key(
            chat_id=chat_id,
            sender_id=sender_id,
            idempotency_key=idempotency_key
        )
        
        if existing_message is not None:
            return existing_message
        
        # Create a new message
        message = Message(
            id=uuid.uuid4(),
            chat_id=chat_id,
            sender_id=sender_id,
            text=text,
            idempotency_key=idempotency_key
        )
        
        # Persist the message
        created_message = await self.message_repository.create(message)
        
        # Broadcast the message to all participants
        message_data = {
            "type": "message",
            "message": {
                "id": str(created_message.id),
                "chat_id": str(created_message.chat_id),
                "sender_id": str(created_message.sender_id),
                "text": created_message.text,
                "created_at": created_message.created_at.isoformat(),
                "updated_at": created_message.updated_at.isoformat()
            }
        }
        
        await self.message_broadcaster.broadcast_to_chat(
            chat_id=chat_id,
            message=message_data,
            user_ids=participant_ids,
            exclude_user_id=None  # Send to all participants, including sender
        )
        
        return created_message
    
    async def get_chat_messages(
        self,
        chat_id: uuid.UUID,
        limit: int = 50,
        before_id: t.Optional[uuid.UUID] = None
    ) -> t.List[Message]:
        """
        Get messages for a chat with pagination.
        
        Retrieved messages are ordered by creation time (newest first),
        with optional pagination using a message ID as a cursor.
        
        Args:
            chat_id: The UUID of the chat
            limit: Maximum number of messages to return
            before_id: The ID of the message before which to start the pagination
        Returns:
            A list of messages in the chat
        """
        return await self.message_repository.get_chat_messages(
            chat_id=chat_id,
            limit=limit,
            before_id=before_id
        )
    
    async def mark_as_read(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        Mark a message as read by a user.
        
        Args:
            message_id: The UUID of the message
            user_id: The UUID of the user
            
        Returns:
            True if the status was updated, False if the message doesn't exist or user is not a participant
        """
        return await self.message_repository.update_read_status(
            message_id=message_id,
            user_id=user_id,
            read=True
        )
    
    async def mark_all_as_read(
        self,
        chat_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> int:
        """
        Mark all messages in a chat as read for a user.
        
        Args:
            chat_id: The UUID of the chat
            user_id: The UUID of the user
            
        Returns:
            The number of messages marked as read
        """
        return await self.message_repository.mark_all_as_read(
            chat_id=chat_id,
            user_id=user_id
        )
    
    async def get_unread_count(
        self,
        chat_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> int:
        """
        Get count of unread messages in a chat for a user.
        
        Args:
            chat_id: The UUID of the chat
            user_id: The UUID of the user
            
        Returns:
            The count of unread messages
        """
        return await self.message_repository.get_unread_count(
            chat_id=chat_id,
            user_id=user_id
        )


# Factory function for getting a message service
async def get_message_service(
    message_repository: MessageRepository,
    chat_repository: ChatRepository,
    message_broadcaster: MessageBroadcaster
) -> MessageService:
    """
    Get a message service instance with the required dependencies.
    
    Args:
        message_repository: Repository for message data access
        chat_repository: Repository for chat data access
        message_broadcaster: Service for broadcasting messages to users
        
    Returns:
        A message service instance
    """
    return MessageService(
        message_repository=message_repository,
        chat_repository=chat_repository,
        message_broadcaster=message_broadcaster
    )