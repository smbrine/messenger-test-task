"""
Pytest fixtures for API integration tests.
"""
import re
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from testcontainers.postgres import PostgresContainer
from unittest.mock import AsyncMock

from src.interface.main import create_app
from src.domain.models.user import User
from src.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from src.infrastructure.repositories.chat_repository import SQLAlchemyChatRepository
from src.application.services.user_service import UserService
from src.application.services.chat_service import ChatService
from src.infrastructure.security.jwt import JoseJWTService
from src.application.security.jwt_interface import JWTService
from src.infrastructure.database.database import Base


class TestHttpBearer(HTTPBearer):
    """Custom HTTP bearer for tests that skips verification."""
    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        # For tests, we'll just extract the token without validating
        auth_header = request.headers.get("Authorization")
        if auth_header:
            scheme, token = auth_header.split()
            if scheme.lower() == "bearer":
                return HTTPAuthorizationCredentials(scheme=scheme, credentials=token)
        # If no token, we'll still allow access for tests
        return HTTPAuthorizationCredentials(scheme="bearer", credentials="test_token")


# Dictionary to store users by token for testing
test_users_by_token = {}


@pytest.fixture(scope="session")
def postgres_container():
    """Create a PostgreSQL container for testing."""
    with PostgresContainer("postgres:17") as postgres:
        yield postgres


@pytest_asyncio.fixture
async def db_engine(postgres_container):
    """Create a test database engine with PostgreSQL."""
    # Get the connection URL from the container
    container_url = postgres_container.get_connection_url()
    
    # Parse the URL to extract components
    if "postgresql+" in container_url:
        # The URL already has a driver prefix
        url_parts = container_url.split("://", 1)
        prefix = "postgresql+asyncpg://"
        rest = url_parts[1]
        db_url = f"{prefix}{rest}"
    else:
        # Standard postgresql:// URL
        url_parts = container_url.split("://", 1)
        prefix = "postgresql+asyncpg://"
        rest = url_parts[1]
        db_url = f"{prefix}{rest}"
    
    engine = create_async_engine(db_url, echo=True)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create a test database session."""
    # Use expire_on_commit=False and autocommit=True to ensure changes are immediately visible
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=True)
    
    async with session_factory() as session:
        # Enable autocommit mode
        await session.begin()
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def user_repository(db_session: AsyncSession):
    """Get a user repository for tests."""
    return SQLAlchemyUserRepository(db_session)


@pytest_asyncio.fixture
async def chat_repository(db_session: AsyncSession):
    """Get a chat repository for tests."""
    return SQLAlchemyChatRepository(db_session)


@pytest_asyncio.fixture
async def user_service(user_repository):
    """Get a user service for tests."""
    return UserService(user_repository)


@pytest_asyncio.fixture
async def chat_service(chat_repository, user_repository):
    """Get a chat service for tests."""
    return ChatService(chat_repository, user_repository)


@pytest_asyncio.fixture
async def jwt_service():
    """Get a JWT service for tests."""
    return JoseJWTService()


@pytest_asyncio.fixture
async def message_repository(db_session: AsyncSession):
    """Get a message repository for tests."""
    from src.infrastructure.repositories.message_repository import SQLAlchemyMessageRepository
    return SQLAlchemyMessageRepository(db_session)


@pytest_asyncio.fixture
async def message_broadcaster():
    """Get a message broadcaster for tests."""
    from src.infrastructure.redis.message_broadcaster import RedisMessageBroadcaster
    # Use a mock broadcaster for tests
    return AsyncMock(spec=RedisMessageBroadcaster)


@pytest_asyncio.fixture
async def message_service(message_repository, chat_repository, message_broadcaster, db_session):
    """Get a message service for tests."""
    from src.application.services.message_service import MessageService
    from src.domain.models.chat import Chat, ChatParticipant, ChatType
    
    # Create a custom test version of the message service that commits before doing operations
    class TestMessageService(MessageService):
        async def send_message(self, chat_id, sender_id, text, idempotency_key):
            # Commit any pending changes to make sure chat is visible
            await db_session.commit()
            
            # Call the parent implementation
            return await super().send_message(chat_id, sender_id, text, idempotency_key)
        
        # Override chat_repository.get_by_id to handle database transaction isolation
        async def _get_chat_by_id(self, chat_id):
            # Make sure changes are visible by committing first
            await db_session.commit()
            
            # Standard implementation from the ChatRepository
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from src.infrastructure.database.models.chat import ChatModel
            
            # Query directly rather than through repository to avoid transaction issues
            query = (
                select(ChatModel)
                .options(selectinload(ChatModel.participants))
                .where(ChatModel.id == chat_id)
            )
            
            result = await db_session.execute(query)
            model = result.scalar_one_or_none()
            
            if model is None:
                return None
                
            # Map to domain model
            from src.domain.models.chat import Chat, ChatParticipant, ChatType
            from src.infrastructure.database.models.chat import ChatTypeEnum
            
            def _map_enum_to_chat_type(enum_type):
                if enum_type == ChatTypeEnum.PRIVATE:
                    return ChatType.PRIVATE
                return ChatType.GROUP
                
            def _map_to_domain_participant(model):
                return ChatParticipant(
                    user_id=model.user_id,
                    role=model.role,
                )
                
            return Chat(
                id=model.id,
                name=model.name,
                type=_map_enum_to_chat_type(model.type),
                participants=[_map_to_domain_participant(p) for p in model.participants]
            )
    
    # Patch the message service's send_message method to ensure commits
    message_service = TestMessageService(
        message_repository=message_repository,
        chat_repository=chat_repository,
        message_broadcaster=message_broadcaster
    )
    
    # Monkey patch the get_by_id method
    message_service.chat_repository.get_by_id = message_service._get_chat_by_id
    
    return message_service


@pytest_asyncio.fixture
async def app(test_user: User, db_session: AsyncSession, user_repository, chat_repository, 
             message_repository, message_broadcaster, user_service, chat_service, 
             message_service, jwt_service):
    """
    Create a test FastAPI application with authentication overrides.
    """
    app = create_app()
    
    # Override database session for tests
    from src.infrastructure.database.database import get_db_session
    
    async def get_test_db_session():
        # For tests, we'll use autocommit mode to ensure changes are immediately visible
        yield db_session
        await db_session.commit()
        
    app.dependency_overrides[get_db_session] = get_test_db_session
    
    # Override services directly
    from src.interface.api.dependencies import get_user_service, get_chat_service, get_db, get_jwt_service_dependency
    from src.infrastructure.repositories.message_repository import get_message_repository
    from src.infrastructure.redis.message_broadcaster import get_message_broadcaster
    from src.application.services.message_service import get_message_service
    
    async def get_test_db():
        yield db_session
    
    async def get_test_user_service():
        return user_service
        
    async def get_test_chat_service():
        return chat_service
        
    async def get_test_message_repository():
        return message_repository
        
    async def get_test_message_broadcaster():
        return message_broadcaster
        
    async def get_test_message_service():
        return message_service

    async def get_test_jwt_service():
        return jwt_service
    
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_user_service] = get_test_user_service
    app.dependency_overrides[get_chat_service] = get_test_chat_service
    app.dependency_overrides[get_message_repository] = get_test_message_repository
    app.dependency_overrides[get_message_broadcaster] = get_test_message_broadcaster
    app.dependency_overrides[get_message_service] = get_test_message_service
    app.dependency_overrides[get_jwt_service_dependency] = get_test_jwt_service
    
    # Override authentication for tests
    from src.interface.api.auth import oauth2_scheme
    app.dependency_overrides[oauth2_scheme] = TestHttpBearer()
    
    # Override get_current_user to return our test user
    from src.interface.api.dependencies import get_current_user
    
    async def get_test_user_override(token: str = Depends(TestHttpBearer())):
        # Check if we have a token-to-user mapping for tests
        if token.credentials in test_users_by_token:
            return test_users_by_token[token.credentials]
        # Default to the test_user
        return test_user
        
    app.dependency_overrides[get_current_user] = get_test_user_override
    
    return app


@pytest_asyncio.fixture
async def test_client(app: FastAPI):
    """
    Create a test client for the FastAPI application.
    """
    # Debug: print all available routes
    for route in app.routes:
        if hasattr(route, 'methods'):
            print(f"Route: {route.path}, methods: {route.methods}")
        else:
            print(f"Route: {route.path}, type: {type(route).__name__}")
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, user_repository):
    """
    Create a test user.
    """
    # Create a test user
    test_user = User(
        username="test_user",
        name="Test User",
        password_hash="$2b$12$g56gZ9bz.qZJ6i3QiWl3weLNfQ5EMCprxH3yCv/d8HwpGrYP15.5y",  # hashed "password123"
    )
    
    # Save the user to the database
    await user_repository.create(test_user)
    await db_session.commit()
    
    return test_user


@pytest_asyncio.fixture
async def test_user2(db_session: AsyncSession, user_repository):
    """
    Create a second test user.
    """
    # Create a test user
    test_user = User(
        username="test_user2",
        name="Test User 2",
        password_hash="$2b$12$g56gZ9bz.qZJ6i3QiWl3weLNfQ5EMCprxH3yCv/d8HwpGrYP15.5y",  # hashed "password123"
    )
    
    # Save the user to the database
    await user_repository.create(test_user)
    await db_session.commit()
    
    return test_user


@pytest_asyncio.fixture
async def test_user3(db_session: AsyncSession, user_repository):
    """
    Create a third test user.
    """
    # Create a test user
    test_user = User(
        username="test_user3",
        name="Test User 3",
        password_hash="$2b$12$g56gZ9bz.qZJ6i3QiWl3weLNfQ5EMCprxH3yCv/d8HwpGrYP15.5y",  # hashed "password123"
    )
    
    # Save the user to the database
    await user_repository.create(test_user)
    await db_session.commit()
    
    return test_user


@pytest_asyncio.fixture
async def test_user_token(test_user: User, jwt_service: JWTService):
    """
    Create a JWT token for the test user.
    """
    token = await jwt_service.create_access_token(test_user)
    # Store in our test dictionary for the override
    test_users_by_token[token] = test_user
    return token


@pytest_asyncio.fixture
async def test_user2_token(test_user2: User, jwt_service: JWTService):
    """
    Create a JWT token for the second test user.
    """
    token = await jwt_service.create_access_token(test_user2)
    # Store in our test dictionary for the override
    test_users_by_token[token] = test_user2
    return token


@pytest_asyncio.fixture
async def test_user3_token(test_user3: User, jwt_service: JWTService):
    """
    Create a JWT token for the third test user.
    """
    token = await jwt_service.create_access_token(test_user3)
    # Store in our test dictionary for the override
    test_users_by_token[token] = test_user3
    return token 