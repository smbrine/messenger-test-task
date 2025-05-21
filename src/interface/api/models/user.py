"""
User-related API models for request/response serialization.
"""
import uuid
import typing as t

from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    """Request model for user registration."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    name: t.Optional[str] = None
    phone: t.Optional[str] = None


class UserResponse(BaseModel):
    """Response model for user data."""
    id: uuid.UUID
    username: str
    name: t.Optional[str] = None
    phone: t.Optional[str] = None


class UserUpdateRequest(BaseModel):
    """Request model for user profile update."""
    name: t.Optional[str] = None
    phone: t.Optional[str] = None


class PasswordChangeRequest(BaseModel):
    """Request model for password change."""
    old_password: str
    new_password: str = Field(..., min_length=8)


class PasswordResetRequest(BaseModel):
    """Request model for password reset."""
    username: str
    new_password: str = Field(..., min_length=8)
    # In a real-world scenario, this would include a reset token
    # or verification code from email/SMS


class UsernameAvailabilityRequest(BaseModel):
    """Request model for username availability check."""
    username: str


class UsernameAvailabilityResponse(BaseModel):
    """Response model for username availability check."""
    username: str
    available: bool 