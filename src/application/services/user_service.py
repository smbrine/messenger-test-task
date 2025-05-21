"""
User service for handling user-related operations.
"""
import uuid
import typing as t

from src.domain.models.user import User, UserPasswordHasher
from src.application.repositories.user_repository import UserRepository


class UserService:
    """
    Service for managing user-related operations.
    """
    
    def __init__(self, user_repository: UserRepository):
        """
        Initialize the user service with a repository.
        
        Args:
            user_repository: Repository for user data access
        """
        self.user_repository = user_repository
    
    async def register_user(
        self, 
        username: str, 
        password: str, 
        name: t.Optional[str] = None, 
        phone: t.Optional[str] = None
    ) -> User:
        """
        Register a new user.
        
        Args:
            username: Unique username for the user
            password: Password for the user
            name: Optional display name for the user
            phone: Optional phone number
            
        Returns:
            The created user
            
        Raises:
            ValueError: If the username is already taken
        """
        # Check if username is already taken
        existing_user = await self.user_repository.get_by_username(username)
        if existing_user:
            raise ValueError("Username already taken")
        
        # Hash the password
        password_hash = UserPasswordHasher.hash_password(password)
        
        # Create a new user entity
        user = User(
            username=username,
            name=name,
            password_hash=password_hash,
            phone=phone,
        )
        
        # Save the user to the repository
        return await self.user_repository.create(user)
    
    async def authenticate_user(self, username: str, password: str) -> t.Optional[User]:
        """
        Authenticate a user with username and password.
        
        Args:
            username: The username to authenticate
            password: The password to verify
            
        Returns:
            The user if authentication is successful, None otherwise
        """
        # Get the user by username
        user = await self.user_repository.get_by_username(username)
        if not user:
            return None
        
        # Verify the password
        if UserPasswordHasher.verify_password(password, user.password_hash):
            return user
        
        return None
    
    async def update_profile(
        self, 
        user_id: uuid.UUID, 
        name: t.Optional[str] = None, 
        phone: t.Optional[str] = None
    ) -> User:
        """
        Update a user's profile information.
        
        Args:
            user_id: The ID of the user to update
            name: The new display name (optional)
            phone: The new phone number (optional)
            
        Returns:
            The updated user
            
        Raises:
            ValueError: If the user doesn't exist
        """
        # Check if the user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Create an updated user entity
        updated_user = User(
            id=user.id,
            username=user.username,
            name=name,
            password_hash=user.password_hash,
            phone=phone,
        )
        
        # Update the user in the repository
        result = await self.user_repository.update(updated_user)
        if not result:
            raise ValueError("Failed to update user profile")
        
        return result
    
    async def change_password(
        self, 
        user_id: uuid.UUID, 
        old_password: str, 
        new_password: str
    ) -> bool:
        """
        Change a user's password.
        
        Args:
            user_id: The ID of the user
            old_password: The current password for verification
            new_password: The new password to set
            
        Returns:
            True if the password was changed, False otherwise
        """
        # Get the user
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            return False
        
        # Verify the old password
        if not UserPasswordHasher.verify_password(old_password, user.password_hash):
            return False
        
        # Hash the new password
        new_password_hash = UserPasswordHasher.hash_password(new_password)
        
        # Create an updated user entity
        updated_user = User(
            id=user.id,
            username=user.username,
            name=user.name,
            password_hash=new_password_hash,
            phone=user.phone,
        )
        
        # Update the user in the repository
        result = await self.user_repository.update(updated_user)
        
        return result is not None
    
    async def is_username_available(self, username: str) -> bool:
        """
        Check if a username is available for registration.
        
        Args:
            username: The username to check
            
        Returns:
            True if the username is available, False otherwise
        """
        user = await self.user_repository.get_by_username(username)
        return user is None 
    
    async def get_many(self, limit: int, offset: int, page: int) -> list[User]:
        """
        Get all users.
        """
        return await self.user_repository.get_many(limit, offset, page)