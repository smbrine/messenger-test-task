"""
Tests for the User domain model.
"""
import uuid
import pytest
from pydantic import ValidationError

from src.domain.models.user import User, UserPasswordHasher


class TestUserModel:
    """Test cases for the User domain model."""

    def test_user_creation_valid(self):
        """Test creating a valid user."""
        user = User(
            id=uuid.uuid4(),
            username="testuser",
            name="Test User",
            password_hash="hashed_password",
            phone="+1234567890",
        )
        assert user.username == "testuser"
        assert user.name == "Test User"
        assert user.password_hash == "hashed_password"
        assert user.phone == "+1234567890"
        assert isinstance(user.id, uuid.UUID)

    def test_user_creation_with_default_id(self):
        """Test creating a user with a default UUID."""
        user = User(
            username="testuser",
            name="Test User",
            password_hash="hashed_password",
        )
        assert isinstance(user.id, uuid.UUID)

    def test_user_creation_with_invalid_username(self):
        """Test that creating a user with invalid username raises ValidationError."""
        # Test with username too short
        with pytest.raises(ValidationError):
            User(
                username="te",
                name="Test User",
                password_hash="hashed_password",
            )
        
        # Test with username too long
        with pytest.raises(ValidationError):
            User(
                username="a" * 51,
                name="Test User",
                password_hash="hashed_password",
            )
        
        # Test with invalid characters
        with pytest.raises(ValidationError):
            User(
                username="test@user",
                name="Test User",
                password_hash="hashed_password",
            )

    def test_user_creation_with_invalid_phone(self):
        """Test that creating a user with invalid phone raises ValidationError."""
        with pytest.raises(ValidationError):
            User(
                username="testuser",
                name="Test User",
                password_hash="hashed_password",
                phone="invalid_phone",
            )

    def test_user_equality(self):
        """Test user equality comparison."""
        user_id = uuid.uuid4()
        user1 = User(
            id=user_id,
            username="testuser",
            name="Test User",
            password_hash="hashed_password",
        )
        user2 = User(
            id=user_id,
            username="testuser",
            name="Test User",
            password_hash="hashed_password",
        )
        user3 = User(
            id=uuid.uuid4(),
            username="testuser",
            name="Test User",
            password_hash="hashed_password",
        )
        
        assert user1 == user2
        assert user1 != user3
        assert user1 != "not_a_user"


class TestUserPasswordHasher:
    """Test cases for the UserPasswordHasher."""

    def test_password_hashing(self):
        """Test that password hashing works correctly."""
        raw_password = "secure_password123"
        password_hash = UserPasswordHasher.hash_password(raw_password)
        
        # Verify the hash is not the raw password
        assert password_hash != raw_password
        
        # Verify we can validate the password correctly
        assert UserPasswordHasher.verify_password(raw_password, password_hash) is True
        
        # Verify incorrect password fails validation
        assert UserPasswordHasher.verify_password("wrong_password", password_hash) is False
    
    def test_password_hashing_different_salts(self):
        """Test that hashing the same password twice gives different results."""
        raw_password = "secure_password123"
        hash1 = UserPasswordHasher.hash_password(raw_password)
        hash2 = UserPasswordHasher.hash_password(raw_password)
        
        # Should generate different hashes for same password due to different salts
        assert hash1 != hash2
        
        # Both hashes should validate with the original password
        assert UserPasswordHasher.verify_password(raw_password, hash1) is True
        assert UserPasswordHasher.verify_password(raw_password, hash2) is True 