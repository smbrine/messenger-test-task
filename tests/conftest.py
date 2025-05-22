"""
Pytest configuration and fixtures.
"""
import os
import uuid
import pytest
import asyncio
import logging
import pytest_asyncio
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


from src.domain.models.user import User
from src.infrastructure.database.database import Base
from src.config.settings import get_settings
from src.infrastructure.redis.redis import get_redis_client, close_redis_connections
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from src.infrastructure.security.jwt import JoseJWTService
from src.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from src.application.services.user_service import UserService
from src.interface.main import create_app
from fastapi import FastAPI
from httpx import AsyncClient


# Configure logger
logger = logging.getLogger(__name__)

# Constants for test containers
POSTGRES_VERSION = "17"
POSTGRES_USER = "test_user"
POSTGRES_PASSWORD = "test_password"
POSTGRES_DB = "test_db"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Setup the test environment settings.
    """
    # Set testing flag
    os.environ["TESTING"] = "True"
    os.environ["ENVIRONMENT"] = "testing"
    
    # Clear settings cache to ensure we get fresh settings
    get_settings.cache_clear()
    
    yield
    
    # Clear environment variables
    os.environ.pop("TESTING", None)
    os.environ.pop("ENVIRONMENT", None)
    
    # Clear settings cache
    get_settings.cache_clear()


# Clear Redis cache between tests to avoid shared state
@pytest.fixture(autouse=True)
def clear_redis_cache():
    """Clear Redis client cache between tests."""
    yield
    # Clear the LRU cache for Redis client to ensure a fresh client for each test
    get_redis_client.cache_clear()


# Use a fresh event loop for each test function
@pytest.fixture
def event_loop():
    """
    Create a fresh event loop for each test function.
    
    This prevents issues with "Event loop is closed" errors and
    "Future attached to a different loop" errors.
    """
    # Create a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Yield the loop for the test to use
    yield loop
    
    # Clean up after the test
    try:
        # Close pending tasks
        pending = asyncio.all_tasks(loop)
        if pending:
            # Allow pending tasks to complete with a timeout
            loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True)
            )
        # Clean up Redis connections before closing loop
        loop.run_until_complete(close_redis_connections())
        # Close the loop
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
    except Exception as e:
        logger.error(f"Error cleaning up event loop: {e}")


@pytest.fixture
def jwt_service():
    """
    Get a JWT service for tests.
    """
    return JoseJWTService()


@pytest_asyncio.fixture(scope="session")
async def postgres_container():
    """
    Start a Postgres container for testing.
    """
    container = PostgresContainer(
        f"postgres:{POSTGRES_VERSION}",
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        dbname=POSTGRES_DB,
    )
    container.start()
    
    # Get the connection URL
    host = container.get_container_host_ip()
    port = container.get_exposed_port(5432)
    
    # Format with asyncpg
    db_url = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{host}:{port}/{POSTGRES_DB}"
    
    # Set the environment variable for the database URL
    os.environ["DATABASE_URL"] = db_url
    
    # Clear settings cache to ensure we get fresh settings with new DB URL
    get_settings.cache_clear()
    
    yield container
    
    # Clear environment variables
    os.environ.pop("DATABASE_URL", None)
    
    # Clear settings cache
    get_settings.cache_clear()
    
    container.stop()


@pytest_asyncio.fixture(scope="session")
async def redis_container():
    """
    Start a Redis container for testing.
    """
    container = RedisContainer(password="password")
    container.start()
    
    # Set the environment variables for Redis
    host = container.get_container_host_ip()
    port = container.get_exposed_port(6379)
    redis_url = f"redis://:password@{host}:{port}/0"
    
    # Setting environment variable for Redis URL
    # Note: The default Redis container doesn't have auth enabled
    # So we don't set username/password which would trigger auth errors
    os.environ["REDIS_URL"] = redis_url
    
    # Make sure username/password aren't set
    if "REDIS_USERNAME" in os.environ:
        os.environ.pop("REDIS_USERNAME")
    if "REDIS_PASSWORD" in os.environ:
        os.environ.pop("REDIS_PASSWORD")
    
    # Clear settings cache to ensure we get fresh settings with new Redis URL
    get_settings.cache_clear()
    
    yield container
    
    # Clean up Redis connections
    await close_redis_connections()
    
    # Clear environment variables
    os.environ.pop("REDIS_URL", None)
    
    # Clear settings cache
    get_settings.cache_clear()
    
    container.stop()


@pytest_asyncio.fixture
async def test_db_engine(postgres_container):
    """
    Create a test database engine.
    """
    settings = get_settings()
    engine = create_async_engine(
        settings.db.url,
        echo=True,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_db_engine):
    """
    Create a test database session.
    """
    connection = await test_db_engine.connect()
    transaction = await connection.begin()
    
    session = AsyncSession(bind=connection, expire_on_commit=False)
    
    yield session
    
    await session.close()
    await transaction.rollback()
    await connection.close()

@pytest_asyncio.fixture
async def redis_client(redis_container):
    """
    Create a Redis client for testing.
    """
    return get_redis_client()


# Helper utility for testing
def generate_uuid() -> uuid.UUID:
    """
    Generate a UUID for testing.
    """
    return uuid.uuid4() 


