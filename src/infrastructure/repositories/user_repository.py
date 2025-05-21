"""
SQLAlchemy implementation of the UserRepository.
"""
import uuid
import typing as t
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.user import User
from src.application.repositories.user_repository import UserRepository
from src.infrastructure.database.models.user import UserModel


class SQLAlchemyUserRepository(UserRepository):
    """
    SQLAlchemy implementation of the UserRepository interface.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.
        
        Args:
            session: The SQLAlchemy async session to use for database operations
        """
        self.session = session
    
    def _map_to_domain(self, model: UserModel) -> User:
        """
        Map a database model to a domain entity.
        
        Args:
            model: The database model to map
            
        Returns:
            The corresponding domain entity
        """
        return User(
            id=model.id,
            username=model.username,
            name=model.name,
            password_hash=model.password_hash,
            phone=model.phone,
        )
    
    def _map_to_model(self, entity: User) -> UserModel:
        """
        Map a domain entity to a database model.
        
        Args:
            entity: The domain entity to map
            
        Returns:
            The corresponding database model
        """
        return UserModel(
            id=entity.id,
            username=entity.username,
            name=entity.name,
            password_hash=entity.password_hash,
            phone=entity.phone,
        )
    
    async def create(self, user: User) -> User:
        """
        Create a new user in the database.
        
        Args:
            user: The user to create
            
        Returns:
            The created user with database-generated ID
        """
        # Create a model from the entity
        model = self._map_to_model(user)
        
        # Add the model to the session and flush to get the ID
        self.session.add(model)
        await self.session.flush()
        
        # Map the model back to an entity and return it
        return self._map_to_domain(model)
    
    async def get_by_id(self, user_id: uuid.UUID) -> t.Optional[User]:
        """
        Retrieve a user by ID.
        
        Args:
            user_id: The UUID of the user to retrieve
            
        Returns:
            The user if found, None otherwise
        """
        # Build a query to find the user by ID
        query = select(UserModel).where(UserModel.id == user_id)
        
        # Execute the query
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        # Map the model to an entity if found
        if model is not None:
            return self._map_to_domain(model)
        
        return None
    
    async def get_by_username(self, username: str) -> t.Optional[User]:
        """
        Retrieve a user by username.
        
        Args:
            username: The username to search for
            
        Returns:
            The user if found, None otherwise
        """
        # Build a query to find the user by username
        query = select(UserModel).where(UserModel.username == username)
        
        # Execute the query
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        # Map the model to an entity if found
        if model is not None:
            return self._map_to_domain(model)
        
        return None
    
    async def get_by_phone(self, phone: str) -> t.Optional[User]:
        """
        Retrieve a user by phone number.
        
        Args:
            phone: The phone number to search for
            
        Returns:
            The user if found, None otherwise
        """
        # Build a query to find the user by phone
        query = select(UserModel).where(UserModel.phone == phone)
        
        # Execute the query
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        # Map the model to an entity if found
        if model is not None:
            return self._map_to_domain(model)
        
        return None
    
    async def update(self, user: User) -> t.Optional[User]:
        """
        Update an existing user.
        
        Args:
            user: The user with updated values
            
        Returns:
            The updated user if found, None if the user doesn't exist
        """
        # Check if the user exists
        existing_user = await self.get_by_id(user.id)
        if existing_user is None:
            return None
        
        # Build an update query
        query = (
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(
                name=user.name,
                password_hash=user.password_hash,
                phone=user.phone,
            )
            .returning(UserModel)
        )
        
        # Execute the query
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        # Map the model to an entity if found
        if model is not None:
            return self._map_to_domain(model)
        
        return None
    
    async def delete(self, user_id: uuid.UUID) -> bool:
        """
        Delete a user from the database.
        
        Args:
            user_id: The UUID of the user to delete
            
        Returns:
            True if the user was deleted, False if the user doesn't exist
        """
        # Build a delete query
        query = delete(UserModel).where(UserModel.id == user_id)
        
        # Execute the query
        result = await self.session.execute(query)
        
        # Return True if at least one row was affected
        return result.rowcount > 0 
    
    async def get_many(self, limit: int, offset: int, page: int) -> list[User]:
        """
        Get multiple users with pagination.
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            page: Page number (used in combination with limit)
            
        Returns:
            List of users
        """
        # Calculate the correct offset based on page and limit
        calculated_offset = offset + (page - 1) * limit
        
        # Build a query to get users with pagination
        query = select(UserModel).limit(limit).offset(calculated_offset)
        
        # Execute the query
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        # Map the models to entities
        return [self._map_to_domain(model) for model in models] 