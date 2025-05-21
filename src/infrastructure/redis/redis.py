"""
Redis connection management module.
"""
import typing as t
import logging
import asyncio
from functools import lru_cache

import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError

from src.config.settings import get_settings

# Configure logger
logger = logging.getLogger(__name__)

# Global connection pool reference
_connection_pool = None
_clients = set()


def get_connection_pool() -> ConnectionPool:
    """
    Get the Redis connection pool, creating it if necessary.
    
    Returns:
        The Redis connection pool
    """
    global _connection_pool
    if _connection_pool is None:
        settings = get_settings()
        _connection_pool = redis.ConnectionPool.from_url(
            settings.redis.url,
            max_connections=settings.redis.max_connections,
            decode_responses=settings.redis.decode_responses,
            username=settings.redis.username,
            password=settings.redis.password,
        )
    return _connection_pool


@lru_cache(maxsize=32)
def get_redis_client() -> Redis:
    """
    Get a Redis client using the connection pool.
    
    Returns:
        A Redis client instance
        
    Note:
        Each call to this function creates a new client if not in cache.
        The client is cached with @lru_cache for performance, but this
        means that client cleanup must explicitly clear the cache using
        get_redis_client.cache_clear().
    """
    client = redis.Redis(connection_pool=get_connection_pool())
    _clients.add(client)
    return client


async def ping_redis() -> bool:
    """
    Ping Redis to check the connection.
    
    Returns:
        True if ping was successful, False otherwise
    """
    try:
        client = get_redis_client()
        return await client.ping()
    except RedisError as e:
        logger.error(f"Redis ping failed: {e}")
        return False


async def close_redis_connections() -> None:
    """
    Close all Redis connections in the pool.
    
    This function:
    1. Closes all client instances that were tracked
    2. Disconnects the connection pool 
    3. Clears the LRU cache for get_redis_client
    4. Resets the global connection pool reference
    
    This ensures a clean slate for new tests.
    """
    global _connection_pool
    
    # Close each Redis client
    close_tasks = []
    for client in list(_clients):
        try:
            if client.connection_pool.connection_kwargs["decode_responses"]:
                close_tasks.append(client.aclose())
            
            _clients.remove(client)
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")
    
    # Wait for all close tasks to complete
    if close_tasks:
        try:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error waiting for Redis client close tasks: {e}")
    
    # Clear the LRU cache for get_redis_client
    get_redis_client.cache_clear()
    
    # Disconnect the connection pool if it exists
    if _connection_pool is not None:
        try:
            await _connection_pool.disconnect(inuse_connections=True)
        except Exception as e:
            logger.error(f"Error disconnecting Redis connection pool: {e}")
        
        # Reset the global connection pool
        _connection_pool = None


# Common Redis utility functions with retries and error handling
async def set_key(key: str, value: str, expiry: t.Optional[int] = None) -> bool:
    """
    Set a key in Redis with optional expiry time in seconds.
    
    Args:
        key: The Redis key
        value: The value to set
        expiry: Optional TTL in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_redis_client()
        return await client.set(key, value, ex=expiry)
    except RedisError as e:
        logger.error(f"Redis set_key error for '{key}': {e}")
        return False


async def get_key(key: str) -> t.Optional[str]:
    """
    Get a value from Redis by key.
    
    Args:
        key: The Redis key
        
    Returns:
        The value or None if not found or an error occurred
    """
    try:
        client = get_redis_client()
        return await client.get(key)
    except RedisError as e:
        logger.error(f"Redis get_key error for '{key}': {e}")
        return None


async def delete_key(key: str) -> int:
    """
    Delete a key from Redis.
    
    Args:
        key: The Redis key
        
    Returns:
        Number of keys deleted (0 if key didn't exist)
    """
    try:
        client = get_redis_client()
        return await client.delete(key)
    except RedisError as e:
        logger.error(f"Redis delete_key error for '{key}': {e}")
        return 0


async def add_to_set(key: str, *values: str) -> int:
    """
    Add values to a Redis set.
    
    Args:
        key: The Redis key
        values: Values to add to the set
        
    Returns:
        Number of values added to the set
    """
    try:
        client = get_redis_client()
        return await client.sadd(key, *values)
    except RedisError as e:
        logger.error(f"Redis add_to_set error for '{key}': {e}")
        return 0


async def remove_from_set(key: str, *values: str) -> int:
    """
    Remove values from a Redis set.
    
    Args:
        key: The Redis key
        values: Values to remove from the set
        
    Returns:
        Number of values removed from the set
    """
    try:
        client = get_redis_client()
        return await client.srem(key, *values)
    except RedisError as e:
        logger.error(f"Redis remove_from_set error for '{key}': {e}")
        return 0


async def get_set_members(key: str) -> t.List[str]:
    """
    Get all members of a Redis set.
    
    Args:
        key: The Redis key
        
    Returns:
        List of set members or empty list if not found or an error occurred
    """
    try:
        client = get_redis_client()
        return await client.smembers(key)
    except RedisError as e:
        logger.error(f"Redis get_set_members error for '{key}': {e}")
        return []


# Redis list operations for message queues
async def add_to_list(key: str, value: str) -> int:
    """
    Add a value to the end of a Redis list.
    
    Args:
        key: The Redis key
        value: The value to add
        
    Returns:
        The new length of the list or 0 if an error occurred
    """
    try:
        client = get_redis_client()
        return await client.rpush(key, value)
    except RedisError as e:
        logger.error(f"Redis add_to_list error for '{key}': {e}")
        return 0


async def get_list(key: str) -> t.List[str]:
    """
    Get all values from a Redis list.
    
    Args:
        key: The Redis key
        
    Returns:
        List of values or empty list if not found or an error occurred
    """
    try:
        client = get_redis_client()
        return await client.lrange(key, 0, -1)
    except RedisError as e:
        logger.error(f"Redis get_list error for '{key}': {e}")
        return []


async def delete_list(key: str) -> int:
    """
    Delete a Redis list.
    
    Args:
        key: The Redis key
        
    Returns:
        1 if the key was deleted, 0 if it didn't exist or an error occurred
    """
    try:
        client = get_redis_client()
        return await client.delete(key)
    except RedisError as e:
        logger.error(f"Redis delete_list error for '{key}': {e}")
        return 0 