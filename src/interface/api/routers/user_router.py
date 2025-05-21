"""
User API endpoints.
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


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get the profile of the current authenticated user.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        name=current_user.name,
        phone=current_user.phone
    )


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    user_data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update the profile of the current authenticated user.
    """
    try:
        updated_user = await user_service.update_profile(
            current_user.id,
            user_data.name,
            user_data.phone
        )
        return UserResponse(
            id=updated_user.id,
            username=updated_user.username,
            name=updated_user.name,
            phone=updated_user.phone
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get('', response_model=list[UserResponse])
async def get_users(
    limit: int = 10,
    offset: int = 0, 
    page: int = 1,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get all users with pagination.
    
    Args:
        limit: Maximum number of users to return
        offset: Number of users to skip
        page: Page number
    """
    users = await user_service.get_many(limit=limit, offset=offset, page=page)
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            name=user.name,
            phone=user.phone
        ) for user in users
    ]


@router.post("/username-availability", response_model=UsernameAvailabilityResponse)
async def check_username_availability(
    request: UsernameAvailabilityRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    Check if a username is available for registration.
    """
    available = await user_service.is_username_available(request.username)
    
    return UsernameAvailabilityResponse(
        username=request.username,
        available=available
    ) 

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    """
    Get a user by their ID.
    """
    user = await user_service.user_repository.get_by_id(user_id)
    return UserResponse(
        id=user.id,
        username=user.username,
        name=user.name,
        phone=user.phone
    )