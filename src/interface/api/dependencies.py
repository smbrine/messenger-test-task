"""
FastAPI dependency injection system.
"""
import typing as t

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.repositories.chat_repository import ChatRepository
from src.application.repositories.message_repository import MessageRepository
from src.application.security.jwt_interface import JWTService
from src.application.services.chat_service import ChatService
from src.application.services.message_service import MessageService
from src.application.services.read_status_manager import ReadStatusManager
from src.infrastructure.database.database import get_db_session
from src.infrastructure.redis.message_broadcaster import RedisMessageBroadcaster, get_message_broadcaster
from src.infrastructure.repositories.chat_repository import SQLAlchemyChatRepository
from src.infrastructure.repositories.message_repository import SQLAlchemyMessageRepository
from src.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from src.application.services.user_service import UserService
from src.domain.models.user import User
from src.application.security.jwt_interface import JWTService
from src.infrastructure.security.jwt_factory import get_jwt_service

# Import get_current_user_from_token from auth after we've defined the necessary functions
# to avoid circular imports
from src.interface.api.auth import get_current_user_from_token


async def get_db() -> t.AsyncGenerator[AsyncSession, None]:
    """
    Get database session dependency.
    """
    async with get_db_session() as session:
        yield session


async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """
    Get user service with database repository.
    """
    user_repository = SQLAlchemyUserRepository(db)
    return UserService(user_repository)


async def get_chat_service(db: AsyncSession = Depends(get_db)) -> ChatService:
    """
    Get chat service with database repositories.
    """
    chat_repository = SQLAlchemyChatRepository(db)
    user_repository = SQLAlchemyUserRepository(db)
    return ChatService(chat_repository, user_repository)


async def get_message_service(db: AsyncSession = Depends(get_db)) -> MessageService:
    """
    Get message service with database repositories.
    """
    message_repository = SQLAlchemyMessageRepository(db)
    chat_repository = SQLAlchemyChatRepository(db)
    message_broadcaster = RedisMessageBroadcaster()
    
    return MessageService(
        message_repository=message_repository,
        chat_repository=chat_repository,
        message_broadcaster=message_broadcaster
    )


async def get_read_status_manager(db: AsyncSession = Depends(get_db)) -> ReadStatusManager:
    """
    Get read status manager with database repositories.
    """
    message_repository = SQLAlchemyMessageRepository(db)
    message_broadcaster = RedisMessageBroadcaster()
    
    return ReadStatusManager(
        message_repository=message_repository,
        message_broadcaster=message_broadcaster
    )


async def get_jwt_service_dependency() -> JWTService:
    """
    Get JWT service dependency.
    """
    return get_jwt_service()


async def get_current_user(
    user_service: UserService = Depends(get_user_service),
    user: dict = Depends(get_current_user_from_token)
) -> User:
    """
    Get the current authenticated user.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    db_user = await user_service.user_repository.get_by_id(user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return db_user