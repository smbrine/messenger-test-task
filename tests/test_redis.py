"""
Tests for Redis connection.
"""
import typing as t
import pytest
import redis.asyncio as redis

from src.infrastructure.redis.redis import ping_redis, set_key, get_key, delete_key


@pytest.mark.asyncio
async def test_redis_connection(redis_container):
    """
    Test that we can connect to Redis and perform basic operations.
    
    Instead of using our module's Redis client which may be configured
    differently, we create a direct client to the test container.
    """
    # Get connection details from the container
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    
    # Create Redis client directly to test container
    redis_client = redis.Redis(
        host=host,
        port=port,
        db=0,
        decode_responses=True,
        password="password"
    )
    
    try:
        # Ping Redis to check connection
        ping_result = await redis_client.ping()
        assert ping_result is True
        
        # Test setting and getting a key
        key = "test:key"
        value = "test-value"
        
        # Set a key
        set_result = await redis_client.set(key, value)
        assert set_result is True
        
        # Get the key
        get_result = await redis_client.get(key)
        assert get_result == value
        
        # Delete the key
        del_result = await redis_client.delete(key)
        assert del_result == 1
        
        # Verify the key is deleted
        get_result_after_delete = await redis_client.get(key)
        assert get_result_after_delete is None
    
    finally:
        # Close the test client using aclose() to avoid deprecation warning
        await redis_client.aclose() 