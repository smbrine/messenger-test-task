"""
Read status manager for handling message read status operations.
"""
import typing as t
import uuid

from src.application.repositories.message_repository import MessageRepository
from src.application.services.message_broadcaster import MessageBroadcaster


class ReadStatusManager:
    """
    Service for managing message read status operations.
    
    This service handles:
    - Marking messages as read
    - Getting unread message counts
    - Broadcasting read status updates to chat participants
    """
    
    def __init__(
        self,
        message_repository: MessageRepository,
        message_broadcaster: MessageBroadcaster
    ):
        """
        Initialize the read status manager.
        
        Args:
            message_repository: Repository for message data access
            message_broadcaster: Service for broadcasting status updates
        """
        self.message_repository = message_repository
        self.message_broadcaster = message_broadcaster
    
    async def mark_as_read(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        chat_id: uuid.UUID
    ) -> bool:
        """
        Mark a message as read by a user and broadcast the status update.
        
        Args:
            message_id: The UUID of the message
            user_id: The UUID of the user
            chat_id: The UUID of the chat (needed for broadcasting)
            
        Returns:
            True if the status was updated, False otherwise
        """
        # Update the read status in the database
        success = await self.message_repository.update_read_status(
            message_id=message_id,
            user_id=user_id,
            read=True
        )
        
        # If successful, broadcast the read status update
        if success:
            # Create the read status update message
            status_update = {
                "type": "read_status",
                "status": {
                    "message_id": str(message_id),
                    "user_id": str(user_id),
                    "read": True
                }
            }
            
            # Broadcast to all users in the chat
            await self.message_broadcaster.broadcast_to_chat(
                chat_id=chat_id,
                message=status_update,
                user_ids=[],  # Empty list means broadcast will fetch participants
                exclude_user_id=None  # Don't exclude any user
            )
        
        return success
    
    async def mark_multiple_as_read(
        self,
        message_ids: t.List[uuid.UUID],
        user_id: uuid.UUID,
        chat_id: uuid.UUID
    ) -> int:
        """
        Mark multiple messages as read by a user.
        
        Args:
            message_ids: List of message UUIDs to mark as read
            user_id: The UUID of the user
            chat_id: The UUID of the chat (needed for broadcasting)
            
        Returns:
            The number of messages successfully marked as read
        """
        # Update each message's read status
        success_count = 0
        for message_id in message_ids:
            if await self.message_repository.update_read_status(
                message_id=message_id,
                user_id=user_id,
                read=True
            ):
                success_count += 1
        
        # If any messages were marked as read, broadcast a batch update
        if success_count > 0:
            # Create the batch read status update message
            status_update = {
                "type": "batch_read_status",
                "status": {
                    "message_ids": [str(mid) for mid in message_ids],
                    "user_id": str(user_id),
                    "read": True,
                    "count": success_count
                }
            }
            
            # Broadcast to all users in the chat
            await self.message_broadcaster.broadcast_to_chat(
                chat_id=chat_id,
                message=status_update,
                user_ids=[],  # Empty list means broadcast will fetch participants
                exclude_user_id=None  # Don't exclude any user
            )
        
        return success_count
    
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
        # Mark all messages as read in the database
        count = await self.message_repository.mark_all_as_read(
            chat_id=chat_id,
            user_id=user_id
        )
        
        # If any messages were marked as read, broadcast an update
        if count > 0:
            # Create the all read status update message
            status_update = {
                "type": "all_read_status",
                "status": {
                    "chat_id": str(chat_id),
                    "user_id": str(user_id),
                    "count": count
                }
            }
            
            # Broadcast to all users in the chat
            await self.message_broadcaster.broadcast_to_chat(
                chat_id=chat_id,
                message=status_update,
                user_ids=[],  # Empty list means broadcast will fetch participants
                exclude_user_id=None  # Don't exclude any user
            )
        
        return count
    
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


# Factory function for getting a read status manager
async def get_read_status_manager(
    message_repository: MessageRepository,
    message_broadcaster: MessageBroadcaster
) -> ReadStatusManager:
    """
    Get a read status manager instance with the required dependencies.
    
    Args:
        message_repository: Repository for message data access
        message_broadcaster: Service for broadcasting status updates
        
    Returns:
        A read status manager instance
    """
    return ReadStatusManager(
        message_repository=message_repository,
        message_broadcaster=message_broadcaster
    ) 