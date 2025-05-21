"""
JWT authentication infrastructure.
"""
import uuid
import time
import typing as t
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from src.config.settings import get_settings
from src.domain.models.user import User
from src.domain.models.auth import TokenData, TokenPair
from src.application.security.jwt_interface import JWTService

# Get JWT settings
settings = get_settings()


class JoseJWTService(JWTService):
    """
    Implementation of JWTService using python-jose.
    """
    
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
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt.access_token_expire_minutes)
        
        # Create token data
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "exp": int(expire.timestamp()),
            "iat": int(time.time()),
            "refresh": False
        }
        
        # Encode the token
        encoded_jwt = jwt.encode(token_data, settings.jwt.secret_key, algorithm=settings.jwt.algorithm)
        return encoded_jwt
    
    async def create_refresh_token(self, user: User) -> str:
        """
        Create a new refresh token with longer expiration.
        
        Args:
            user: The user to create a refresh token for
            
        Returns:
            The encoded refresh token
        """
        expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt.refresh_token_expire_days)
        
        # Create token data
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "exp": int(expire.timestamp()),
            "iat": int(time.time()),
            "refresh": True
        }
        
        # Encode the token
        encoded_jwt = jwt.encode(token_data, settings.jwt.secret_key, algorithm=settings.jwt.algorithm)
        return encoded_jwt
    
    async def create_token_pair(self, user: User) -> TokenPair:
        """
        Create both access and refresh tokens.
        
        Args:
            user: The user to create tokens for
            
        Returns:
            A pair of access and refresh tokens
        """
        access_token = await self.create_access_token(user)
        refresh_token = await self.create_refresh_token(user)
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token
        )
    
    async def decode_token(self, token: str) -> t.Optional[TokenData]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: The JWT token to decode
            
        Returns:
            The decoded token data or None if invalid
        """
        try:
            payload = jwt.decode(
                token, 
                settings.jwt.secret_key, 
                algorithms=[settings.jwt.algorithm]
            )
            return TokenData(**payload)
        except (JWTError, ValueError):
            return None
    
    async def validate_access_token(self, token: str) -> t.Optional[uuid.UUID]:
        """
        Validate an access token and extract the user ID.
        
        Args:
            token: The JWT access token
            
        Returns:
            The user ID if the token is valid, None otherwise
        """
        token_data = await self.decode_token(token)
        
        if token_data is None:
            return None
            
        # Check if it's a refresh token
        if token_data.refresh:
            return None
            
        # Extract user ID
        user_id_str = token_data.sub
        if user_id_str is None:
            return None
        
        # Convert to UUID
        try:
            return uuid.UUID(user_id_str)
        except ValueError:
            return None
    
    async def validate_refresh_token(self, token: str) -> t.Optional[uuid.UUID]:
        """
        Validate a refresh token and extract the user ID.
        
        Args:
            token: The JWT refresh token
            
        Returns:
            The user ID if the token is valid, None otherwise
        """
        token_data = await self.decode_token(token)
        
        if token_data is None:
            return None
            
        # Check if it's a refresh token
        if not token_data.refresh:
            return None
            
        # Extract user ID
        user_id_str = token_data.sub
        if user_id_str is None:
            return None
        
        # Convert to UUID
        try:
            return uuid.UUID(user_id_str)
        except ValueError:
            return None
    
    async def blacklist_token(self, token: str) -> bool:
        """
        Add a token to the blacklist to prevent its future use.
        
        Args:
            token: The JWT token to blacklist
            
        Returns:
            True if successful, False otherwise
        """
        # TODO: Implement token blacklisting with Redis
        # This is a placeholder for future implementation
        return True 