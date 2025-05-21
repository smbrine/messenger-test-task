"""
Draft service for managing message drafts.
"""
import typing as t
import logging
from uuid import UUID

from src.domain.models.draft import MessageDraft
from src.domain.exceptions.repository_exceptions import RepositoryError
from src.application.repositories.draft_repository import DraftRepository, get_draft_repository
from src.interface.websocket.websocket_manager import manager

# Configure logger
logger = logging.getLogger(__name__)


class DraftService:
    """Service for managing user message drafts."""
    
    def __init__(self, draft_repository: DraftRepository):
        """
        Initialize the draft service with a repository.
        
        Args:
            draft_repository: The repository to use for draft storage
        """
        self.repository = draft_repository
    
    async def save_user_draft(self, user_id: UUID, chat_id: UUID, text: str) -> t.Optional[MessageDraft]:
        """
        Save a user's draft message for a specific chat.
        
        Args:
            user_id: The UUID of the user
            chat_id: The UUID of the chat
            text: The draft message text
            
        Returns:
            The saved message draft or None if there was an error
            
        Raises:
            RepositoryError: If there was an error saving the draft
        """
        draft = MessageDraft(
            user_id=user_id,
            chat_id=chat_id,
            text=text
        )
        
        success = await self.repository.save(draft)
        
        if success:
            # Broadcast the draft to all user's connections to synchronize tabs
            await self._broadcast_draft_update(draft)
            return draft
        
        logger.warning(f"Failed to save draft for user {user_id} in chat {chat_id}")
        return None
    
    async def get_user_draft(self, user_id: UUID, chat_id: UUID) -> t.Optional[MessageDraft]:
        """
        Get a user's draft message for a specific chat.
        
        Args:
            user_id: The UUID of the user
            chat_id: The UUID of the chat
            
        Returns:
            The message draft or None if not found
            
        Raises:
            RepositoryError: If there was an error retrieving the draft
        """
        return await self.repository.get(user_id, chat_id)
    
    async def delete_user_draft(self, user_id: UUID, chat_id: UUID) -> bool:
        """
        Delete a user's draft message for a specific chat.
        
        Args:
            user_id: The UUID of the user
            chat_id: The UUID of the chat
            
        Returns:
            True if deleted, False otherwise
            
        Raises:
            RepositoryError: If there was an error deleting the draft
        """
        result = await self.repository.delete(user_id, chat_id)
        
        if result:
            # Broadcast the draft deletion to all user's connections
            await self._broadcast_draft_deletion(user_id, chat_id)
        
        return result
    
    async def _broadcast_draft_update(self, draft: MessageDraft) -> int:
        """
        Broadcast draft update to all user's connections.
        
        Args:
            draft: The draft message
            
        Returns:
            The number of connections that received the message
        """
        message = {
            "type": "draft_update",
            "chat_id": str(draft.chat_id),
            "text": draft.text,
            "updated_at": draft.updated_at.isoformat()
        }
        
        return await manager.broadcast_to_user(draft.user_id, message)
    
    async def _broadcast_draft_deletion(self, user_id: UUID, chat_id: UUID) -> int:
        """
        Broadcast draft deletion to all user's connections.
        
        Args:
            user_id: The UUID of the user
            chat_id: The UUID of the chat
            
        Returns:
            The number of connections that received the message
        """
        message = {
            "type": "draft_delete",
            "chat_id": str(chat_id)
        }
        
        return await manager.broadcast_to_user(user_id, message)


def get_draft_service() -> DraftService:
    """
    Get a draft service instance.
    
    Returns:
        A draft service instance
    """
    return DraftService(get_draft_repository()) 