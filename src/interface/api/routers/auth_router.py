"""
Auth API endpoints.
"""
import typing as t

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from src.domain.models.user import User
from src.application.services.user_service import UserService
from src.interface.api.dependencies import get_user_service, get_db, get_jwt_service_dependency
from src.interface.api.auth import get_current_user
from src.interface.api.models.user import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    UsernameAvailabilityRequest,
    UsernameAvailabilityResponse,
)
from src.application.security.jwt_interface import JWTService
from src.domain.models.auth import TokenPair


# Create router
router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreateRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    Register a new user.
    """
    try:
        user = await user_service.register_user(
            user_data.username,
            user_data.password,
            user_data.name,
            user_data.phone
        )
        return UserResponse(
            id=user.id,
            username=user.username,
            name=user.name,
            phone=user.phone
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenPair)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service),
    jwt_service: JWTService = Depends(get_jwt_service_dependency)
):
    """
    Authenticate a user and return access and refresh tokens.
    """
    user = await user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_pair = await jwt_service.create_token_pair(user)
    
    return token_pair


@router.post("/refresh-token", response_model=TokenPair)
async def refresh_access_token(
    token: str,
    user_service: UserService = Depends(get_user_service),
    jwt_service: JWTService = Depends(get_jwt_service_dependency)
):
    """
    Generate a new access token using a refresh token.
    """
    # In a real implementation, this would validate the refresh token
    # and check if it's in a token blocklist
    
    # Validate refresh token
    user_id = await jwt_service.validate_refresh_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get the user
    user = await user_service.user_repository.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate new token pair
    token_pair = await jwt_service.create_token_pair(user)
    
    return token_pair


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Change the password of the current authenticated user.
    """
    success = await user_service.change_password(
        current_user.id,
        password_data.old_password,
        password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    reset_data: PasswordResetRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    Reset a user's password (simplified version).
    
    In a real application, this would validate a reset token
    that was sent to the user's email or phone.
    """
    # This is a simplified implementation
    # In a real app, you would validate a token from email/SMS
    
    # For now, we'll just raise an exception
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password reset functionality not implemented in this demo"
    )
    
    # Real implementation would look something like:
    # success = await user_service.reset_password(
    #     reset_data.username,
    #     reset_data.reset_token,
    #     reset_data.new_password
    # )
    # 
    # if not success:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Invalid reset token"
    #     )
