"""
Tests for the UserRepository.
"""
import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.user import User
from src.application.repositories.user_repository import UserRepository
from src.infrastructure.repositories.user_repository import SQLAlchemyUserRepository


@pytest.mark.asyncio
class TestUserRepository:
    """Test cases for the UserRepository interface and its implementations."""
    
    @pytest_asyncio.fixture
    async def session(self, db_session):
        """Fixture for the database session."""
        # Simply yield the session directly, it's already an AsyncSession
        yield db_session
            
    @pytest_asyncio.fixture
    async def repository(self, session: AsyncSession):
        """Fixture for the user repository."""
        return SQLAlchemyUserRepository(session)
    
    @pytest_asyncio.fixture
    async def test_user(self):
        """Fixture for a test user."""
        return User(
            username="testuser",
            name="Test User",
            password_hash="hashed_password",
            phone="+1234567890",
        )
    
    async def test_create_user(self, repository: UserRepository, test_user: User):
        """Test creating a user."""
        # Create a user through the repository
        created_user = await repository.create(test_user)
        
        # Verify the created user has the correct properties
        assert created_user.username == test_user.username
        assert created_user.name == test_user.name
        assert created_user.password_hash == test_user.password_hash
        assert created_user.phone == test_user.phone
        assert isinstance(created_user.id, uuid.UUID)
    
    async def test_get_user_by_id(self, repository: UserRepository, test_user: User):
        """Test retrieving a user by ID."""
        # Create a user first
        created_user = await repository.create(test_user)
        
        # Retrieve the user by ID
        retrieved_user = await repository.get_by_id(created_user.id)
        
        # Verify the retrieved user matches the created user
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.username == created_user.username
        assert retrieved_user.name == created_user.name
        assert retrieved_user.password_hash == created_user.password_hash
        assert retrieved_user.phone == created_user.phone
    
    async def test_get_non_existent_user(self, repository: UserRepository):
        """Test retrieving a non-existent user."""
        # Generate a random UUID that shouldn't exist in the database
        random_id = uuid.uuid4()
        
        # Attempt to retrieve a user with the random ID
        retrieved_user = await repository.get_by_id(random_id)
        
        # Verify that no user was found
        assert retrieved_user is None
    
    async def test_get_user_by_username(self, repository: UserRepository, test_user: User):
        """Test retrieving a user by username."""
        # Create a user first
        created_user = await repository.create(test_user)
        
        # Retrieve the user by username
        retrieved_user = await repository.get_by_username(test_user.username)
        
        # Verify the retrieved user matches the created user
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.username == created_user.username
    
    async def test_get_user_by_non_existent_username(self, repository: UserRepository):
        """Test retrieving a user by a non-existent username."""
        # Attempt to retrieve a user with a username that shouldn't exist
        retrieved_user = await repository.get_by_username("nonexistentuser")
        
        # Verify that no user was found
        assert retrieved_user is None
    
    async def test_update_user(self, repository: UserRepository, test_user: User):
        """Test updating a user."""
        # Create a user first
        created_user = await repository.create(test_user)
        
        # Create an updated user model
        updated_user = User(
            id=created_user.id,
            username=created_user.username,
            name="Updated Name",
            password_hash="updated_password_hash",
            phone="+0987654321",
        )
        
        # Update the user
        result_user = await repository.update(updated_user)
        
        # Verify the update was successful
        assert result_user is not None
        assert result_user.id == created_user.id
        assert result_user.username == created_user.username  # Username shouldn't change
        assert result_user.name == "Updated Name"
        assert result_user.password_hash == "updated_password_hash"
        assert result_user.phone == "+0987654321"
        
        # Retrieve the user to verify changes in the database
        retrieved_user = await repository.get_by_id(created_user.id)
        assert retrieved_user is not None
        assert retrieved_user.name == "Updated Name"
        assert retrieved_user.password_hash == "updated_password_hash"
        assert retrieved_user.phone == "+0987654321"
    
    async def test_delete_user(self, repository: UserRepository, test_user: User):
        """Test deleting a user."""
        # Create a user first
        created_user = await repository.create(test_user)
        
        # Delete the user
        result = await repository.delete(created_user.id)
        
        # Verify deletion was successful
        assert result is True
        
        # Verify user no longer exists in the database
        retrieved_user = await repository.get_by_id(created_user.id)
        assert retrieved_user is None
    
    async def test_delete_non_existent_user(self, repository: UserRepository):
        """Test deleting a non-existent user."""
        # Generate a random UUID that shouldn't exist in the database
        random_id = uuid.uuid4()
        
        # Attempt to delete a user with the random ID
        result = await repository.delete(random_id)
        
        # Verify that the deletion reports failure
        assert result is False
    
    async def test_get_user_by_phone(self, repository: UserRepository, test_user: User):
        """Test finding a user by phone number."""
        # Create a user first
        created_user = await repository.create(test_user)
        
        # Retrieve the user by phone number
        retrieved_user = await repository.get_by_phone(test_user.phone)
        
        # Verify the retrieved user matches the created user
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.phone == test_user.phone
    
    async def test_get_user_by_non_existent_phone(self, repository: UserRepository):
        """Test retrieving a user by a non-existent phone number."""
        # Attempt to retrieve a user with a phone number that shouldn't exist
        retrieved_user = await repository.get_by_phone("+9999999999")
        
        # Verify that no user was found
        assert retrieved_user is None
        
    async def test_get_many(self, repository: UserRepository, test_user: User):
        """Test retrieving multiple users with pagination."""
        # Create multiple users
        users = [
            test_user,
            User(
                username="testuser2",
                name="Test User 2",
                password_hash="password_hash_2",
                phone="+2345678901"
            ),
            User(
                username="testuser3",
                name="Test User 3",
                password_hash="password_hash_3",
                phone="+3456789012"
            ),
            User(
                username="testuser4",
                name="Test User 4",
                password_hash="password_hash_4",
                phone="+4567890123"
            ),
            User(
                username="testuser5",
                name="Test User 5",
                password_hash="password_hash_5",
                phone="+5678901234"
            )
        ]
        
        # Create all users
        for user in users:
            await repository.create(user)
        
        # Test basic pagination - first page of 2 items
        result_page_1 = await repository.get_many(limit=2, offset=0, page=1)
        assert len(result_page_1) == 2
        
        # Test second page
        result_page_2 = await repository.get_many(limit=2, offset=0, page=2)
        assert len(result_page_2) == 2
        
        # Test third page
        result_page_3 = await repository.get_many(limit=2, offset=0, page=3)
        assert len(result_page_3) == 1  # Only one user on the last page
        
        # Test with offset
        result_with_offset = await repository.get_many(limit=2, offset=1, page=1)
        assert len(result_with_offset) == 2
        
        # Verify correct users are returned (comparing by usernames)
        usernames = [user.username for user in result_with_offset]
        # Since the offset is 1, we should skip the first user
        assert users[0].username not in usernames 