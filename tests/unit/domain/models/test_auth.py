"""
Tests for authentication domain models.
"""
import pytest
from pydantic import ValidationError

from src.domain.models.auth import TokenData, TokenPair


def test_token_data_creation():
    """Test creating a token data model."""
    # Valid token data
    token_data = TokenData(
        sub="123e4567-e89b-12d3-a456-426614174000",
        username="testuser",
        exp=1677321600,  # 2023-02-25T12:00:00Z
        iat=1677321000,  # 2023-02-25T11:50:00Z
    )
    
    assert token_data.sub == "123e4567-e89b-12d3-a456-426614174000"
    assert token_data.username == "testuser"
    assert token_data.exp == 1677321600
    assert token_data.iat == 1677321000
    assert token_data.refresh is False


def test_token_data_with_refresh():
    """Test creating a token data model with refresh=True."""
    token_data = TokenData(
        sub="123e4567-e89b-12d3-a456-426614174000",
        username="testuser",
        exp=1677321600,
        iat=1677321000,
        refresh=True
    )
    
    assert token_data.refresh is True


def test_token_data_missing_fields():
    """Test that required fields are enforced."""
    # Missing required fields
    with pytest.raises(ValidationError):
        TokenData(
            sub="123e4567-e89b-12d3-a456-426614174000",
            username="testuser",
            # Missing exp and iat
        )


def test_token_pair_creation():
    """Test creating a token pair model."""
    token_pair = TokenPair(
        access_token="access.token.example",
        refresh_token="refresh.token.example"
    )
    
    assert token_pair.access_token == "access.token.example"
    assert token_pair.refresh_token == "refresh.token.example"
    assert token_pair.token_type == "bearer"  # Default value


def test_token_pair_with_custom_type():
    """Test creating a token pair with a custom token type."""
    token_pair = TokenPair(
        access_token="access.token.example",
        refresh_token="refresh.token.example",
        token_type="custom"
    )
    
    assert token_pair.token_type == "custom" 