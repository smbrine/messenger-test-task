"""
Integration tests for the draft synchronization feature.
"""
import json
import uuid
import pytest
import asyncio
import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.config.settings import get_settings
from src.domain.models.draft import MessageDraft
from src.domain.models.user import User
from src.domain.models.chat import Chat, ChatParticipant
from src.infrastructure.redis.redis import close_redis_connections, set_key, get_redis_client
from src.application.services.draft_service import DraftService
from src.application.repositories.draft_repository import get_draft_repository
from src.interface.websocket.websocket_manager import ConnectionManager


logger = logging.getLogger(__name__)


# Clear Redis cache between tests
@pytest.fixture(autouse=True)
def clear_redis_cache():
    """Clear Redis client cache between tests."""
    yield
    # Clear the LRU cache for Redis client to ensure a fresh client for each test
    get_redis_client.cache_clear()


# Ensure Redis connections are cleaned up after all tests
@pytest.fixture(scope="module")
async def cleanup_redis():
    """Clean up Redis connections after all tests in the module."""
    yield
    # Close all Redis connections at the end of the module
    await close_redis_connections()


# Redis cleanup after each test
@pytest.fixture(autouse=True)
async def redis_cleanup():
    """
    Clean up Redis connections after each test.
    """
    yield
    # Clean up Redis connections 
    await close_redis_connections()


@pytest.fixture(autouse=True)
async def test_event_loop(event_loop):
    """
    Set up and yield the default event loop for each test.
    
    This prevents issues with event loops closing between tests.
    """
    # The loop is created by pytest-asyncio's event_loop fixture
    yield event_loop
    
    # Clean up Redis connections before the loop is closed
    await close_redis_connections()


@pytest.fixture
async def test_user_a():
    """Create a test user."""
    return User(
        id=uuid.uuid4(),
        username="testuser_a",
        name="Test User A",
        password_hash="hashed_password",
        phone="+1234567890"
    )


@pytest.fixture
async def test_user_b():
    """Create a test user."""
    return User(
        id=uuid.uuid4(),
        username="testuser_b",
        name="Test User B",
        password_hash="hashed_password",
        phone="+1234567890"
    )


@pytest.fixture
async def test_chat(test_user_a, test_user_b):
    """Create a test chat with the test user as a participant."""
    chat_id = uuid.uuid4()
    return Chat(
        id=chat_id,
        name="Test Chat",
        type="private",
        participants=[
            ChatParticipant(
                user_id=test_user_a.id,
                chat_id=chat_id,
                role="member"
            ),
            ChatParticipant(
                user_id=test_user_b.id,
                chat_id=chat_id,
                role="member"
            )
        ]
    )


@pytest.fixture
async def draft_service():
    """Get a draft service instance."""
    # Use the repository factory to get a draft repository
    repository = get_draft_repository()
    service = DraftService(repository)
    # Return the service for use in tests
    yield service
    # Clean up any Redis connections after the test
    await close_redis_connections()


# Mock connection manager for WebSocket tests
@pytest.fixture
def mock_connection_manager():
    """Create a mock connection manager for WebSocket tests."""
    # Create a class that mimes the API of the real connection manager
    class MockConnectionManager(ConnectionManager):
        def __init__(self):
            super().__init__()
            self.broadcast_messages = []
            
        async def broadcast_to_user(self, user_id, message):
            self.broadcast_messages.append((user_id, message))
            return 1  # Indicate 1 connection received the message
            
        async def connect(self, websocket, user_id):
            # Generate a unique connection ID
            connection_id = str(uuid.uuid4())
            return connection_id
            
        async def disconnect(self, connection_id):
            # No-op for testing
            pass
    
    return MockConnectionManager()


@pytest.mark.asyncio
class TestDraftSync:
    """Integration tests for draft synchronization."""
    
    async def test_save_and_retrieve_draft(self, draft_service, test_user_a, test_user_b, test_chat):
        """Test saving and retrieving a draft."""
        try:
            # Save a draft
            draft_text = "Hello, this is a draft message!"
            saved_draft = await draft_service.save_user_draft(
                test_user_a.id, 
                test_chat.id, 
                draft_text
            )
            
            # Verify the draft was saved correctly
            assert saved_draft is not None
            assert saved_draft.user_id == test_user_a.id
            assert saved_draft.chat_id == test_chat.id
            assert saved_draft.text == draft_text
            
            # Retrieve the draft
            retrieved_draft = await draft_service.get_user_draft(
                test_user_a.id,
                test_chat.id
            )
            
            # Verify the retrieved draft matches
            assert retrieved_draft is not None
            assert retrieved_draft.user_id == test_user_a.id
            assert retrieved_draft.chat_id == test_chat.id
            assert retrieved_draft.text == draft_text
            
            # Clean up - delete the draft
            delete_result = await draft_service.delete_user_draft(
                test_user_a.id,
                test_chat.id
            )
            assert delete_result is True
            
            # Verify the draft was deleted
            deleted_draft = await draft_service.get_user_draft(
                test_user_a.id,
                test_chat.id
            )
            assert deleted_draft is None
        finally:
            # Extra cleanup in case test fails before normal cleanup
            try:
                await draft_service.delete_user_draft(test_user_a.id, test_chat.id)
            except Exception as e:
                # Log but don't throw from cleanup
                logger.error(f"Cleanup error: {e}")
    
    # @pytest.mark.skip(reason="This test is commented out because it would require waiting for the TTL to expire, which would make the test slow.")
    async def test_draft_ttl(self, test_user_a, test_chat):
        """
        Test that drafts expire after their TTL.
        
        NOTE: This test is skipped because it would require 
        waiting for the TTL to expire, which would make the test slow.
        In a real scenario, you might want to use a shorter TTL for testing
        or mock the TTL mechanism.
        """
        # Save a draft directly with a short TTL for testing
        draft = MessageDraft(
            user_id=test_user_a.id,
            chat_id=test_chat.id,
            text="This draft should expire quickly"
        )
        
        # Use a short TTL for testing (e.g., 1 second)
        settings = get_settings()
        key = settings.redis.draft_key_format.format(
            user_id=str(test_user_a.id),
            chat_id=str(test_chat.id)
        )
        
        # Save with a 1-second TTL
        draft_data = {
            "text": draft.text,
            "updated_at": draft.updated_at.isoformat()
        }
        await set_key(key, json.dumps(draft_data), expiry=1)
        
        # Verify the draft exists immediately
        draft_service = DraftService(get_draft_repository())
        retrieved_draft = await draft_service.get_user_draft(test_user_a.id, test_chat.id)
        assert retrieved_draft is not None
        assert retrieved_draft.text == draft.text
        
        # Wait for the TTL to expire
        await asyncio.sleep(2)
        
        # Verify the draft is now gone
        expired_draft = await draft_service.get_user_draft(test_user_a.id, test_chat.id)
        assert expired_draft is None
    
    async def test_multiple_drafts_for_same_user(self, draft_service, test_user_a, test_user_b):
        """Test saving and retrieving multiple drafts for the same user in different chats."""
        # Create test chat IDs (don't need full chat objects for this test)
        chat_id_1 = uuid.uuid4()
        chat_id_2 = uuid.uuid4()
        
        try:
            # Save drafts for each chat
            draft_text_1 = "Draft for chat 1"
            draft_text_2 = "Draft for chat 2"
            
            # Save the first draft
            draft_1 = await draft_service.save_user_draft(test_user_a.id, chat_id_1, draft_text_1)
            assert draft_1 is not None
            assert draft_1.text == draft_text_1
            
            # Save the second draft
            draft_2 = await draft_service.save_user_draft(test_user_a.id, chat_id_2, draft_text_2)
            assert draft_2 is not None
            assert draft_2.text == draft_text_2
            
            # Retrieve and verify each draft
            retrieved_draft_1 = await draft_service.get_user_draft(test_user_a.id, chat_id_1)
            retrieved_draft_2 = await draft_service.get_user_draft(test_user_a.id, chat_id_2)
            
            assert retrieved_draft_1 is not None
            assert retrieved_draft_1.text == draft_text_1
            
            assert retrieved_draft_2 is not None
            assert retrieved_draft_2.text == draft_text_2
        finally:
            # Clean up
            try:
                await draft_service.delete_user_draft(test_user_a.id, chat_id_1)
                await draft_service.delete_user_draft(test_user_a.id, chat_id_2)
            except Exception as e:
                # Log but don't throw from cleanup
                logger.error(f"Cleanup error: {e}")
    
    async def test_update_existing_draft(self, draft_service, test_user_a, test_chat):
        """Test updating an existing draft."""
        try:
            # Save initial draft
            initial_text = "Initial draft"
            initial_draft = await draft_service.save_user_draft(test_user_a.id, test_chat.id, initial_text)
            assert initial_draft is not None
            assert initial_draft.text == initial_text
            
            # Update the draft
            updated_text = "Updated draft"
            updated_draft = await draft_service.save_user_draft(
                test_user_a.id, 
                test_chat.id, 
                updated_text
            )
            
            # Verify the draft was updated
            assert updated_draft is not None
            assert updated_draft.text == updated_text
            
            # Retrieve and verify the draft
            retrieved_draft = await draft_service.get_user_draft(
                test_user_a.id,
                test_chat.id
            )
            
            assert retrieved_draft is not None
            assert retrieved_draft.text == updated_text
        finally:
            # Clean up
            try:
                await draft_service.delete_user_draft(test_user_a.id, test_chat.id)
            except Exception as e:
                # Log but don't throw from cleanup
                logger.error(f"Cleanup error: {e}")
    
    @patch('src.application.services.draft_service.manager')
    async def test_cross_tab_synchronization(self, mock_manager, draft_service, test_user_a, test_chat):
        """Test draft synchronization across multiple tabs/connections."""
        try:
            # Create an awaitable mock for broadcast_to_user
            async def mock_broadcast(*args, **kwargs):
                return 2  # Simulate 2 connections receiving the message
            
            # Setup the mock to use our awaitable function
            mock_manager.broadcast_to_user.side_effect = mock_broadcast
            
            # Save a draft
            draft_text = "Draft to be synchronized"
            draft = await draft_service.save_user_draft(test_user_a.id, test_chat.id, draft_text)
            
            # Verify the draft was saved
            assert draft is not None
            assert draft.text == draft_text
            
            # Check that broadcast_to_user was called with the expected arguments
            mock_manager.broadcast_to_user.assert_called_once()
            
            # Verify the call arguments
            call_args = mock_manager.broadcast_to_user.call_args
            user_id, message = call_args[0]
            
            assert user_id == test_user_a.id
            assert message["type"] == "draft_update"
            assert message["chat_id"] == str(test_chat.id)
            assert message["text"] == draft_text
            
            # Test draft deletion broadcast
            mock_manager.broadcast_to_user.reset_mock()
            
            # Create an awaitable mock for broadcast_to_user for deletion
            async def mock_broadcast_delete(*args, **kwargs):
                return 2  # Simulate 2 connections receiving the message
            
            # Setup the mock for deletion
            mock_manager.broadcast_to_user.side_effect = mock_broadcast_delete
            
            # Delete the draft
            await draft_service.delete_user_draft(test_user_a.id, test_chat.id)
            
            # Check that broadcast_to_user was called for deletion
            mock_manager.broadcast_to_user.assert_called_once()
            
            # Verify the deletion broadcast
            call_args = mock_manager.broadcast_to_user.call_args
            user_id, message = call_args[0]
            
            assert user_id == test_user_a.id
            assert message["type"] == "draft_delete"
            assert message["chat_id"] == str(test_chat.id)
        finally:
            # Clean up
            try:
                await draft_service.delete_user_draft(test_user_a.id, test_chat.id)
            except Exception as e:
                # Log but don't throw from cleanup
                logger.error(f"Cleanup error: {e}") 