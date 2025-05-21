"""
Authentication domain models.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class TokenData(BaseModel):
    """Domain model representing the data inside a JWT token."""
    sub: str  # Subject (user ID)
    username: str
    exp: int = Field(...)  # Expiration timestamp
    iat: int = Field(...)  # Issued at timestamp
    refresh: bool = False  # Whether this is a refresh token


class TokenPair(BaseModel):
    """Domain model representing an access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer" 