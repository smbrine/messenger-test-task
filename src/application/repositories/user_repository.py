"""
User repository interface.
"""
import uuid
import typing as t
from abc import ABC, abstractmethod

from src.domain.models.user import User


class UserRepository(ABC):
    """
    Interface for user repository implementations.
    Defines the contract for user data access operations.
    """
    
    @abstractmethod
    async def create(self, user: User) -> User:
        """
        Create a new user in the repository.
        
        Args:
            user: The user to create
            
        Returns:
            The created user with any system-generated fields populated
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> t.Optional[User]:
        """
        Retrieve a user by ID.
        
        Args:
            user_id: The UUID of the user to retrieve
            
        Returns:
            The user if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_username(self, username: str) -> t.Optional[User]:
        """
        Retrieve a user by username.
        
        Args:
            username: The username to search for
            
        Returns:
            The user if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_phone(self, phone: str) -> t.Optional[User]:
        """
        Retrieve a user by phone number.
        
        Args:
            phone: The phone number to search for
            
        Returns:
            The user if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def update(self, user: User) -> t.Optional[User]:
        """
        Update an existing user.
        
        Args:
            user: The user with updated values
            
        Returns:
            The updated user if found, None if the user doesn't exist
        """
        pass
    
    @abstractmethod
    async def delete(self, user_id: uuid.UUID) -> bool:
        """
        Delete a user from the repository.
        
        Args:
            user_id: The UUID of the user to delete
            
        Returns:
            True if the user was deleted, False if the user doesn't exist
        """
        pass 
    
    @abstractmethod
    async def get_many(self, limit: int, offset: int, page: int) -> list[User]:
        """
        Get all users.
        """
        pass