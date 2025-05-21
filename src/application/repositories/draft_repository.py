"""
Draft repository interface.
"""
import typing as t
from uuid import UUID
from abc import ABC, abstractmethod

from src.domain.models.draft import MessageDraft


class DraftRepository(ABC):
    """
    Interface for the draft repository.
    
    This defines the contract for draft storage implementations
    following the repository pattern.
    """
    
    @abstractmethod
    async def save(self, draft: MessageDraft) -> bool:
        """
        Save a draft message.
        
        Args:
            draft: The draft message to save
            
        Returns:
            True if the operation was successful, False otherwise
            
        Raises:
            RepositoryError: If there was an error saving the draft
        """
        pass
    
    @abstractmethod
    async def get(self, user_id: UUID, chat_id: UUID) -> t.Optional[MessageDraft]:
        """
        Get a draft message by user_id and chat_id.
        
        Args:
            user_id: The UUID of the user
            chat_id: The UUID of the chat
            
        Returns:
            The draft message or None if not found
            
        Raises:
            RepositoryError: If there was an error retrieving the draft
        """
        pass
    
    @abstractmethod
    async def delete(self, user_id: UUID, chat_id: UUID) -> bool:
        """
        Delete a draft message.
        
        Args:
            user_id: The UUID of the user
            chat_id: The UUID of the chat
            
        Returns:
            True if the draft was deleted, False if it didn't exist
            
        Raises:
            RepositoryError: If there was an error deleting the draft
        """
        pass


# Factory function will be imported conditionally to avoid circular imports
def get_draft_repository() -> DraftRepository:
    """
    Get a draft repository instance.
    
    Returns:
        A draft repository instance
        
    Note:
        This function uses a conditional import to avoid circular imports.
    """
    from src.infrastructure.repositories.redis_draft_repository import RedisDraftRepository
    return RedisDraftRepository() 