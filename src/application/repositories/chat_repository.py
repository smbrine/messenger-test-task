"""
Chat repository interface.
"""
import uuid
import typing as t
from abc import ABC, abstractmethod

from src.domain.models.chat import Chat, ChatParticipant


class ChatRepository(ABC):
    """
    Interface for chat repository implementations.
    Defines the contract for chat data access operations.
    """
    
    @abstractmethod
    async def create(self, chat: Chat) -> Chat:
        """
        Create a new chat in the repository.
        
        Args:
            chat: The chat to create
            
        Returns:
            The created chat with any system-generated fields populated
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, chat_id: uuid.UUID) -> t.Optional[Chat]:
        """
        Retrieve a chat by ID.
        
        Args:
            chat_id: The UUID of the chat to retrieve
            
        Returns:
            The chat if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_participant(self, user_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> t.List[Chat]:
        """
        Retrieve chats where a user is a participant.
        
        Args:
            user_id: The UUID of the user
            limit: Maximum number of chats to return
            offset: Number of chats to skip
            
        Returns:
            A list of chats where the user is a participant
        """
        pass
    
    @abstractmethod
    async def find_private_chat(self, user1_id: uuid.UUID, user2_id: uuid.UUID) -> t.Optional[Chat]:
        """
        Find a private chat between two specific users.
        
        Args:
            user1_id: The UUID of the first user
            user2_id: The UUID of the second user
            
        Returns:
            The chat if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def update(self, chat: Chat) -> t.Optional[Chat]:
        """
        Update an existing chat.
        
        Args:
            chat: The chat with updated values
            
        Returns:
            The updated chat if found, None if the chat doesn't exist
        """
        pass
    
    @abstractmethod
    async def delete(self, chat_id: uuid.UUID) -> bool:
        """
        Delete a chat from the repository.
        
        Args:
            chat_id: The UUID of the chat to delete
            
        Returns:
            True if the chat was deleted, False if the chat doesn't exist
        """
        pass
    
    @abstractmethod
    async def add_participant(self, chat_id: uuid.UUID, participant: ChatParticipant) -> bool:
        """
        Add a participant to a chat.
        
        Args:
            chat_id: The UUID of the chat
            participant: The participant to add
            
        Returns:
            True if the participant was added, False if the chat doesn't exist
        """
        pass
    
    @abstractmethod
    async def remove_participant(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Remove a participant from a chat.
        
        Args:
            chat_id: The UUID of the chat
            user_id: The UUID of the user to remove
            
        Returns:
            True if the participant was removed, False if the chat doesn't exist or user is not a participant
        """
        pass
    
    @abstractmethod
    async def update_participant_role(self, chat_id: uuid.UUID, user_id: uuid.UUID, new_role: str) -> bool:
        """
        Update a participant's role in a chat.
        
        Args:
            chat_id: The UUID of the chat
            user_id: The UUID of the user
            new_role: The new role for the participant
            
        Returns:
            True if the role was updated, False if the chat doesn't exist or user is not a participant
        """
        pass 