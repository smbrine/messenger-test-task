"""
Tests for the UserService.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.domain.models.user import User, UserPasswordHasher
from src.application.services.user_service import UserService
from src.application.repositories.user_repository import UserRepository


class TestUserService:
    """Test cases for the UserService."""

    @pytest.fixture
    def user_repository_mock(self):
        """Fixture for a mocked user repository."""
        repository = AsyncMock(spec=UserRepository)
        return repository

    @pytest.fixture
    def user_service(self, user_repository_mock):
        """Fixture for the user service."""
        return UserService(user_repository_mock)

    @pytest.fixture
    def test_user(self):
        """Fixture for a test user."""
        return User(
            id=uuid.uuid4(),
            username="testuser",
            name="Test User",
            password_hash=UserPasswordHasher.hash_password("password123"),
            phone="+1234567890",
        )

    async def test_register_user_success(self, user_service, user_repository_mock):
        """Test successful user registration."""
        # Mock repository to return None for get_by_username (user doesn't exist)
        user_repository_mock.get_by_username.return_value = None
        
        # Mock repository create method to return a user with a generated ID
        user_id = uuid.uuid4()
        
        async def mock_create(user):
            return User(
                id=user_id,
                username=user.username,
                name=user.name,
                password_hash=user.password_hash,
                phone=user.phone,
            )
        
        user_repository_mock.create.side_effect = mock_create
        
        # Test data
        username = "newuser"
        password = "securepassword"
        name = "New User"
        phone = "+9876543210"
        
        # Call the service method
        created_user = await user_service.register_user(username, password, name, phone)
        
        # Assertions
        assert created_user is not None
        assert created_user.username == username
        assert created_user.name == name
        assert created_user.phone == phone
        assert UserPasswordHasher.verify_password(password, created_user.password_hash)
        
        # Verify repository calls
        user_repository_mock.get_by_username.assert_called_once_with(username)
        assert user_repository_mock.create.call_count == 1

    async def test_register_user_username_taken(self, user_service, user_repository_mock, test_user):
        """Test user registration with a username that's already taken."""
        # Mock repository to return a user for get_by_username (username exists)
        user_repository_mock.get_by_username.return_value = test_user
        
        # Test data
        username = "testuser"  # Same as test_user
        password = "securepassword"
        name = "New User"
        phone = "+9876543210"
        
        # Call the service method and expect an exception
        with pytest.raises(ValueError, match="Username already taken"):
            await user_service.register_user(username, password, name, phone)
        
        # Verify repository calls
        user_repository_mock.get_by_username.assert_called_once_with(username)
        user_repository_mock.create.assert_not_called()

    async def test_authenticate_user_success(self, user_service, user_repository_mock, test_user):
        """Test successful user authentication."""
        # Create a test password and update the test user with its hash
        raw_password = "password123"
        test_user_with_password = User(
            id=test_user.id,
            username=test_user.username,
            name=test_user.name,
            password_hash=UserPasswordHasher.hash_password(raw_password),
            phone=test_user.phone,
        )
        
        # Mock repository to return the test user
        user_repository_mock.get_by_username.return_value = test_user_with_password
        
        # Call the service method
        authenticated_user = await user_service.authenticate_user(test_user.username, raw_password)
        
        # Assertions
        assert authenticated_user is not None
        assert authenticated_user.id == test_user.id
        assert authenticated_user.username == test_user.username
        
        # Verify repository calls
        user_repository_mock.get_by_username.assert_called_once_with(test_user.username)

    async def test_authenticate_user_wrong_password(self, user_service, user_repository_mock, test_user):
        """Test authentication with incorrect password."""
        # Create a test password and update the test user with its hash
        raw_password = "password123"
        wrong_password = "wrongpassword"
        test_user_with_password = User(
            id=test_user.id,
            username=test_user.username,
            name=test_user.name,
            password_hash=UserPasswordHasher.hash_password(raw_password),
            phone=test_user.phone,
        )
        
        # Mock repository to return the test user
        user_repository_mock.get_by_username.return_value = test_user_with_password
        
        # Call the service method with the wrong password
        authenticated_user = await user_service.authenticate_user(test_user.username, wrong_password)
        
        # Assertions
        assert authenticated_user is None
        
        # Verify repository calls
        user_repository_mock.get_by_username.assert_called_once_with(test_user.username)

    async def test_authenticate_user_nonexistent(self, user_service, user_repository_mock):
        """Test authentication with a non-existent username."""
        # Mock repository to return None for get_by_username
        user_repository_mock.get_by_username.return_value = None
        
        # Call the service method
        authenticated_user = await user_service.authenticate_user("nonexistentuser", "anypassword")
        
        # Assertions
        assert authenticated_user is None
        
        # Verify repository calls
        user_repository_mock.get_by_username.assert_called_once_with("nonexistentuser")

    async def test_update_user_profile_success(self, user_service, user_repository_mock, test_user):
        """Test successful user profile update."""
        # Mock repository get_by_id to return the test user
        user_repository_mock.get_by_id.return_value = test_user
        
        # Mock update to return an updated user
        updated_name = "Updated Name"
        updated_phone = "+9876543210"
        
        updated_user = User(
            id=test_user.id,
            username=test_user.username,
            name=updated_name,
            password_hash=test_user.password_hash,
            phone=updated_phone,
        )
        
        user_repository_mock.update.return_value = updated_user
        
        # Call the service method
        result_user = await user_service.update_profile(test_user.id, updated_name, updated_phone)
        
        # Assertions
        assert result_user is not None
        assert result_user.id == test_user.id
        assert result_user.name == updated_name
        assert result_user.phone == updated_phone
        
        # Verify repository calls
        user_repository_mock.get_by_id.assert_called_once_with(test_user.id)
        assert user_repository_mock.update.call_count == 1

    async def test_update_user_profile_nonexistent(self, user_service, user_repository_mock):
        """Test updating a non-existent user profile."""
        # Mock repository get_by_id to return None
        user_repository_mock.get_by_id.return_value = None
        
        # Call the service method and expect an exception
        user_id = uuid.uuid4()
        with pytest.raises(ValueError, match="User not found"):
            await user_service.update_profile(user_id, "New Name", "+9876543210")
        
        # Verify repository calls
        user_repository_mock.get_by_id.assert_called_once_with(user_id)
        user_repository_mock.update.assert_not_called()

    async def test_change_password_success(self, user_service, user_repository_mock, test_user):
        """Test successful password change."""
        # Create a test password and update the test user with its hash
        old_password = "oldpassword"
        new_password = "newpassword"
        test_user_with_password = User(
            id=test_user.id,
            username=test_user.username,
            name=test_user.name,
            password_hash=UserPasswordHasher.hash_password(old_password),
            phone=test_user.phone,
        )
        
        # Mock repository to return the test user
        user_repository_mock.get_by_id.return_value = test_user_with_password
        
        # Mock update to succeed
        def mock_update(user):
            # Verify the password was updated
            assert UserPasswordHasher.verify_password(new_password, user.password_hash)
            return user
        
        user_repository_mock.update.side_effect = mock_update
        
        # Call the service method
        success = await user_service.change_password(test_user.id, old_password, new_password)
        
        # Assertions
        assert success is True
        
        # Verify repository calls
        user_repository_mock.get_by_id.assert_called_once_with(test_user.id)
        assert user_repository_mock.update.call_count == 1

    async def test_change_password_wrong_old_password(self, user_service, user_repository_mock, test_user):
        """Test password change with incorrect old password."""
        # Create a test password and update the test user with its hash
        old_password = "oldpassword"
        wrong_old_password = "wrongoldpassword"
        new_password = "newpassword"
        test_user_with_password = User(
            id=test_user.id,
            username=test_user.username,
            name=test_user.name,
            password_hash=UserPasswordHasher.hash_password(old_password),
            phone=test_user.phone,
        )
        
        # Mock repository to return the test user
        user_repository_mock.get_by_id.return_value = test_user_with_password
        
        # Call the service method with the wrong old password
        success = await user_service.change_password(test_user.id, wrong_old_password, new_password)
        
        # Assertions
        assert success is False
        
        # Verify repository calls
        user_repository_mock.get_by_id.assert_called_once_with(test_user.id)
        user_repository_mock.update.assert_not_called()

    async def test_is_username_available_true(self, user_service, user_repository_mock):
        """Test username availability check when the username is available."""
        # Mock repository to return None for get_by_username
        user_repository_mock.get_by_username.return_value = None
        
        # Call the service method
        available = await user_service.is_username_available("availableusername")
        
        # Assertions
        assert available is True
        
        # Verify repository calls
        user_repository_mock.get_by_username.assert_called_once_with("availableusername")

    async def test_is_username_available_false(self, user_service, user_repository_mock, test_user):
        """Test username availability check when the username is taken."""
        # Mock repository to return a user for get_by_username
        user_repository_mock.get_by_username.return_value = test_user
        
        # Call the service method
        available = await user_service.is_username_available(test_user.username)
        
        # Assertions
        assert available is False
        
        # Verify repository calls
        user_repository_mock.get_by_username.assert_called_once_with(test_user.username) 