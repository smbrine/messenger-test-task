"""
JWT authentication interface for the application layer.
"""
import uuid
import typing as t
from abc import ABC, abstractmethod
from datetime import timedelta

from src.domain.models.user import User
from src.domain.models.auth import TokenData, TokenPair


class JWTService(ABC):
    """
    Interface for JWT service implementations.
    Defines the contract for JWT operations.
    """
    
    @abstractmethod
    async def create_access_token(
        self, 
        user: User, 
        expires_delta: t.Optional[timedelta] = None
    ) -> str:
        """
        Create a new JWT access token.
        
        Args:
            user: The user to create a token for
            expires_delta: Optional expiration time override
            
        Returns:
            The encoded JWT token
        """
        pass
    
    @abstractmethod
    async def create_refresh_token(self, user: User) -> str:
        """
        Create a new refresh token with longer expiration.
        
        Args:
            user: The user to create a refresh token for
            
        Returns:
            The encoded refresh token
        """
        pass
    
    @abstractmethod
    async def create_token_pair(self, user: User) -> TokenPair:
        """
        Create both access and refresh tokens.
        
        Args:
            user: The user to create tokens for
            
        Returns:
            A pair of access and refresh tokens
        """
        pass
    
    @abstractmethod
    async def decode_token(self, token: str) -> t.Optional[TokenData]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: The JWT token to decode
            
        Returns:
            The decoded token data or None if invalid
        """
        pass
    
    @abstractmethod
    async def validate_access_token(self, token: str) -> t.Optional[uuid.UUID]:
        """
        Validate an access token and extract the user ID.
        
        Args:
            token: The JWT access token
            
        Returns:
            The user ID if the token is valid, None otherwise
        """
        pass
    
    @abstractmethod
    async def validate_refresh_token(self, token: str) -> t.Optional[uuid.UUID]:
        """
        Validate a refresh token and extract the user ID.
        
        Args:
            token: The JWT refresh token
            
        Returns:
            The user ID if the token is valid, None otherwise
        """
        pass
    
    @abstractmethod
    async def blacklist_token(self, token: str) -> bool:
        """
        Add a token to the blacklist to prevent its future use.
        
        Args:
            token: The JWT token to blacklist
            
        Returns:
            True if successful, False otherwise
        """
        pass 