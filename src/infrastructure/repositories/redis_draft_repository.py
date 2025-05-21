"""
Redis implementation of the draft repository.
"""
import json
import logging
import typing as t
from uuid import UUID
from datetime import datetime, timezone
from functools import wraps

import redis.asyncio as redis
from redis.exceptions import RedisError

from src.config.settings import get_settings
from src.domain.models.draft import MessageDraft
from src.domain.exceptions.repository_exceptions import (
    RepositoryError,
    ConnectionError,
    QueryError,
    DataSerializationError,
)
from src.application.repositories.draft_repository import DraftRepository
from src.infrastructure.redis.redis import get_redis_client

# Configure logger
logger = logging.getLogger(__name__)


def handle_redis_errors(func):
    """Decorator to handle Redis errors."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            raise ConnectionError(f"Failed to connect to Redis: {e}") from e
        except redis.RedisError as e:
            logger.error(f"Redis error: {e}")
            raise QueryError(f"Error executing Redis operation: {e}") from e
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.error(f"Data serialization error: {e}")
            raise DataSerializationError(f"Error serializing or deserializing data: {e}") from e
    return wrapper


class RedisDraftRepository(DraftRepository):
    """Redis-based implementation of the draft repository."""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 0.5):
        """
        Initialize the Redis draft repository.
        
        Args:
            max_retries: Maximum number of retry attempts for Redis operations
            retry_delay: Delay in seconds between retry attempts
        """
        self.settings = get_settings()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def _get_key(self, user_id: UUID, chat_id: UUID) -> str:
        """
        Get the Redis key for a draft.
        
        Args:
            user_id: The UUID of the user
            chat_id: The UUID of the chat
            
        Returns:
            The Redis key string
        """
        return self.settings.redis.draft_key_format.format(
            user_id=str(user_id),
            chat_id=str(chat_id)
        )
    
    @handle_redis_errors
    async def save(self, draft: MessageDraft) -> bool:
        """
        Save a draft message to Redis.
        
        Args:
            draft: The draft message to save
            
        Returns:
            True if the operation was successful, False otherwise
            
        Raises:
            ConnectionError: If there was an error connecting to Redis
            QueryError: If there was an error executing the Redis operation
            DataSerializationError: If there was an error serializing the draft
        """
        key = self._get_key(draft.user_id, draft.chat_id)
        
        # Update the timestamp
        draft.updated_at = datetime.now(timezone.utc)
        
        # Convert to JSON-serializable dict
        draft_data = {
            "text": draft.text,
            "updated_at": draft.updated_at.isoformat()
        }
        
        client = get_redis_client()
        result = await client.set(
            key, 
            json.dumps(draft_data), 
            ex=self.settings.redis.draft_ttl
        )
        return result
    
    @handle_redis_errors
    async def get(self, user_id: UUID, chat_id: UUID) -> t.Optional[MessageDraft]:
        """
        Get a draft message from Redis.
        
        Args:
            user_id: The UUID of the user
            chat_id: The UUID of the chat
            
        Returns:
            The draft message or None if not found
            
        Raises:
            ConnectionError: If there was an error connecting to Redis
            QueryError: If there was an error executing the Redis operation
            DataSerializationError: If there was an error deserializing the draft
        """
        key = self._get_key(user_id, chat_id)
        
        client = get_redis_client()
        draft_json = await client.get(key)
        if not draft_json:
            return None
        
        try:
            draft_data = json.loads(draft_json)
            
            return MessageDraft(
                user_id=user_id,
                chat_id=chat_id,
                text=draft_data["text"],
                updated_at=datetime.fromisoformat(draft_data["updated_at"])
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing draft data: {e}")
            raise DataSerializationError(f"Error deserializing draft data: {e}") from e
    
    @handle_redis_errors
    async def delete(self, user_id: UUID, chat_id: UUID) -> bool:
        """
        Delete a draft message from Redis.
        
        Args:
            user_id: The UUID of the user
            chat_id: The UUID of the chat
            
        Returns:
            True if the draft was deleted, False if it didn't exist
            
        Raises:
            ConnectionError: If there was an error connecting to Redis
            QueryError: If there was an error executing the Redis operation
        """
        key = self._get_key(user_id, chat_id)
        
        client = get_redis_client()
        result = await client.delete(key)
        return result > 0 