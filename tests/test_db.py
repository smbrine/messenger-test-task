"""
Tests for database connection.
"""
import typing as t
import pytest
import pytest_asyncio
from sqlalchemy import text

from src.infrastructure.database.database import get_db_session


@pytest_asyncio.fixture
async def db_session():
    """
    Create a test database session for direct testing.
    """
    async with get_db_session() as session:
        yield session


@pytest.mark.asyncio
async def test_db_connection(db_session):
    """
    Test that we can connect to the database and execute a simple query.
    """
    # Execute a simple query
    result = await db_session.execute(text("SELECT 1"))
    value = result.scalar()
    
    assert value == 1 