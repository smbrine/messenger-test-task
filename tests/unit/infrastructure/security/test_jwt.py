"""
Tests for JWT service.
"""
import pytest
import uuid
import time
from datetime import datetime, timedelta, timezone

from src.domain.models.user import User
from src.infrastructure.security.jwt import JoseJWTService
from src.application.security.jwt_interface import JWTService


@pytest.fixture
def jwt_service() -> JWTService:
    """Get a JWT service for tests."""
    return JoseJWTService()


@pytest.fixture
def test_user() -> User:
    """Get a test user for JWT tests."""
    return User(
        id=uuid.uuid4(),
        username="testuser",
        name="Test User",
        password_hash="hashed_password",
        phone="+1234567890"
    )


@pytest.mark.asyncio
class TestJWTService:
    """Test cases for the JWT service."""
    
    async def test_create_access_token(self, jwt_service: JWTService, test_user: User):
        """Test creating an access token."""
        token = await jwt_service.create_access_token(test_user)
        
        # Verify the token is a string
        assert isinstance(token, str)
        
        # Verify the token can be decoded
        token_data = await jwt_service.decode_token(token)
        assert token_data is not None
        assert token_data.sub == str(test_user.id)
        assert token_data.username == test_user.username
        assert token_data.refresh is False
        
    async def test_create_refresh_token(self, jwt_service: JWTService, test_user: User):
        """Test creating a refresh token."""
        token = await jwt_service.create_refresh_token(test_user)
        
        # Verify the token is a string
        assert isinstance(token, str)
        
        # Verify the token can be decoded
        token_data = await jwt_service.decode_token(token)
        assert token_data is not None
        assert token_data.sub == str(test_user.id)
        assert token_data.username == test_user.username
        assert token_data.refresh is True
        
    async def test_create_token_pair(self, jwt_service: JWTService, test_user: User):
        """Test creating a token pair."""
        tokens = await jwt_service.create_token_pair(test_user)
        
        # Verify the tokens exist and are strings
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert isinstance(tokens.access_token, str)
        assert isinstance(tokens.refresh_token, str)
        
        # Verify the tokens can be decoded
        access_token_data = await jwt_service.decode_token(tokens.access_token)
        refresh_token_data = await jwt_service.decode_token(tokens.refresh_token)
        
        # Check access token
        assert access_token_data is not None
        assert access_token_data.sub == str(test_user.id)
        assert access_token_data.username == test_user.username
        assert access_token_data.refresh is False
        
        # Check refresh token
        assert refresh_token_data is not None
        assert refresh_token_data.sub == str(test_user.id)
        assert refresh_token_data.username == test_user.username
        assert refresh_token_data.refresh is True
        
    async def test_validate_access_token(self, jwt_service: JWTService, test_user: User):
        """Test validating an access token."""
        token = await jwt_service.create_access_token(test_user)
        
        # Validate the token
        user_id = await jwt_service.validate_access_token(token)
        assert user_id == test_user.id
        
        # Try to validate the token as a refresh token (should fail)
        user_id = await jwt_service.validate_refresh_token(token)
        assert user_id is None
        
    async def test_validate_refresh_token(self, jwt_service: JWTService, test_user: User):
        """Test validating a refresh token."""
        token = await jwt_service.create_refresh_token(test_user)
        
        # Validate the token
        user_id = await jwt_service.validate_refresh_token(token)
        assert user_id == test_user.id
        
        # Try to validate the token as an access token (should fail)
        user_id = await jwt_service.validate_access_token(token)
        assert user_id is None
        
    async def test_token_expiration(self, jwt_service: JWTService, test_user: User):
        """Test token expiration."""
        # Create a token that expires in 1 second
        token = await jwt_service.create_access_token(
            test_user, 
            expires_delta=timedelta(seconds=1)
        )
        
        # Verify the token is valid
        user_id = await jwt_service.validate_access_token(token)
        assert user_id == test_user.id
        
        # Wait for the token to expire
        time.sleep(2)
        
        # Verify the token is now invalid
        user_id = await jwt_service.validate_access_token(token)
        assert user_id is None
        
    async def test_invalid_token(self, jwt_service: JWTService):
        """Test handling invalid tokens."""
        # Test with an empty token
        user_id = await jwt_service.validate_access_token("")
        assert user_id is None
        
        # Test with a malformed token
        user_id = await jwt_service.validate_access_token("not.a.token")
        assert user_id is None
        
        # Test with a token that has an invalid signature
        user_id = await jwt_service.validate_access_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.INVALID")
        assert user_id is None
        
    async def test_blacklist_token(self, jwt_service: JWTService, test_user: User):
        """Test blacklisting a token."""
        # Create a token
        token = await jwt_service.create_access_token(test_user)
        
        # Blacklist the token (current implementation always returns True)
        result = await jwt_service.blacklist_token(token)
        assert result is True 