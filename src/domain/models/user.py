"""
User domain model.
"""
import re
import uuid
import typing as t
from pydantic import BaseModel, Field, field_validator

from passlib.context import CryptContext


class UserPasswordHasher:
    """
    Handles password hashing and verification for User entities.
    """
    # Create a password context for hashing and verification
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: The plaintext password to hash
            
        Returns:
            The hashed password
        """
        return cls.pwd_context.hash(password)
    
    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash.
        
        Args:
            plain_password: The plaintext password to verify
            hashed_password: The hashed password to check against
            
        Returns:
            True if the password matches the hash, False otherwise
        """
        return cls.pwd_context.verify(plain_password, hashed_password)


class User(BaseModel):
    """
    User domain model representing a user in the system.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    username: str = Field(..., min_length=3, max_length=50)
    name: t.Optional[str] = None
    password_hash: str
    phone: t.Optional[str] = None
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """
        Validate username format.
        
        Args:
            v: The username to validate
            
        Returns:
            The validated username
        
        Raises:
            ValueError: If the username contains invalid characters
        """
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username may only contain letters, numbers, and underscores')
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: t.Optional[str]) -> t.Optional[str]:
        """
        Validate name format if provided.
        
        Args:
            v: The name to validate
            
        Returns:
            The validated name
        
        Raises:
            ValueError: If the name is invalid
        """
        if v is not None and (len(v) < 1 or len(v) > 100):
            raise ValueError('Name must be between 1 and 100 characters')
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: t.Optional[str]) -> t.Optional[str]:
        """
        Validate phone number format.
        
        Args:
            v: The phone number to validate
            
        Returns:
            The validated phone number
        
        Raises:
            ValueError: If the phone number has an invalid format
        """
        if v is None:
            return v
        
        # Basic phone number validation (international format)
        if not re.match(r'^\+?[0-9]{10,15}$', v):
            raise ValueError('Phone number must be in international format, e.g., +1234567890')
        return v
    
    def __eq__(self, other: t.Any) -> bool:
        """
        Compare users for equality.
        
        Args:
            other: The object to compare with
            
        Returns:
            True if equal, False otherwise
        """
        if not isinstance(other, User):
            return False
        return self.id == other.id
    
    class Config:
        """Pydantic model configuration."""
        frozen = True  # Make the model immutable 