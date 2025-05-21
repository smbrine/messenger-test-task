"""
Authentication-related functionality for the API.
"""
import typing as t

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.user import User
from src.application.services.user_service import UserService
from src.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from src.infrastructure.database.database import get_db_session
from src.application.security.jwt_interface import JWTService
from src.infrastructure.security.jwt_factory import get_jwt_service
from src.domain.models.auth import TokenPair

# OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_db_for_auth() -> t.AsyncGenerator[AsyncSession, None]:
    """
    Get database session for auth dependencies to avoid circular imports.
    """
    async with get_db_session() as session:
        yield session


async def get_user_service_for_auth(db: AsyncSession = Depends(get_db_for_auth)) -> UserService:
    """
    Get user service with database repository for auth dependencies.
    This is defined here to avoid circular imports with dependencies.py
    """
    user_repository = SQLAlchemyUserRepository(db)
    return UserService(user_repository)


async def get_jwt_service_for_auth() -> JWTService:
    """
    Get JWT service for auth dependencies.
    This is defined here to avoid circular imports with dependencies.py
    """
    return get_jwt_service()


async def get_current_user_from_token(
    token: str = Depends(oauth2_scheme),
    jwt_service: JWTService = Depends(get_jwt_service_for_auth)
) -> dict:
    """
    Extract and validate user identity from token.
    
    Args:
        token: The JWT token from the Authorization header
        jwt_service: JWT service dependency
        
    Returns:
        Dict with user information from token
        
    Raises:
        HTTPException: If the token is invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Extract user ID from token
    user_id = await jwt_service.validate_access_token(token)
    if user_id is None:
        raise credentials_exception
    
    return {"sub": user_id}


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service_for_auth),
    jwt_service: JWTService = Depends(get_jwt_service_for_auth)
) -> User:
    """
    Get the current user based on the JWT token.
    
    Args:
        token: The JWT token from the Authorization header
        user_service: User service dependency
        jwt_service: JWT service dependency
        
    Returns:
        The current user
        
    Raises:
        HTTPException: If the token is invalid or the user doesn't exist
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Extract user ID from token
    user_id = await jwt_service.validate_access_token(token)
    if user_id is None:
        raise credentials_exception
    
    # Get the user from the database
    user = await user_service.user_repository.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    
    return user


async def get_optional_user(
    token: t.Optional[str] = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service_for_auth),
    jwt_service: JWTService = Depends(get_jwt_service_for_auth)
) -> t.Optional[User]:
    """
    Get the current user if a valid token is provided, otherwise return None.
    
    Args:
        token: The JWT token from the Authorization header (optional)
        user_service: User service dependency
        jwt_service: JWT service dependency
        
    Returns:
        The current user or None if no valid token is provided
    """
    if token is None:
        return None
    
    try:
        return await get_current_user(token, user_service, jwt_service)
    except HTTPException:
        return None 