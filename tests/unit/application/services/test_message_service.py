"""
Tests for the MessageService class.
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.domain.models.message import Message, MessageStatus
from src.domain.models.chat import Chat, ChatParticipant, ChatType
from src.domain.models.user import User
from src.application.services.message_service import MessageService
from src.application.repositories.message_repository import MessageRepository
from src.application.repositories.chat_repository import ChatRepository
from src.application.services.message_broadcaster import MessageBroadcaster


@pytest.fixture
def message_repository():
    """Create a mock message repository."""
    return AsyncMock(spec=MessageRepository)


@pytest.fixture
def chat_repository():
    """Create a mock chat repository."""
    return AsyncMock(spec=ChatRepository)


@pytest.fixture
def message_broadcaster():
    """Create a mock message broadcaster."""
    return AsyncMock(spec=MessageBroadcaster)


@pytest.fixture
def message_service(message_repository, chat_repository, message_broadcaster):
    """Create a message service with mock dependencies."""
    return MessageService(
        message_repository=message_repository,
        chat_repository=chat_repository,
        message_broadcaster=message_broadcaster
    )


@pytest.fixture
def test_user():
    """Create a test user."""
    return User(
        id=uuid.uuid4(),
        username="testuser",
        name="Test User",
        password_hash="hash",
        phone="+1234567890"
    )


@pytest.fixture
def test_chat(test_user):
    """Create a test chat with the test user as a participant."""
    user2_id = uuid.uuid4()
    return Chat(
        id=uuid.uuid4(),
        name="Test Chat",
        type=ChatType.GROUP,
        participants=[
            ChatParticipant(user_id=test_user.id, role="admin"),
            ChatParticipant(user_id=user2_id, role="member")
        ]
    )


@pytest.fixture
def test_message(test_chat, test_user):
    """Create a test message."""
    return Message(
        id=uuid.uuid4(),
        chat_id=test_chat.id,
        sender_id=test_user.id,
        text="Hello, world!",
        idempotency_key="test-key-123",
        created_at=datetime.now(timezone.utc)
    )


@pytest.mark.asyncio
class TestMessageService:
    """Test cases for the MessageService."""
    
    async def test_send_message(self, message_service, message_repository, chat_repository, message_broadcaster, test_user, test_chat):
        """Test sending a message."""
        # Setup
        chat_repository.get_by_id.return_value = test_chat
        message_repository.find_by_idempotency_key.return_value = None
        
        # Create a new message that will be returned by the create method
        new_message_id = uuid.uuid4()
        created_message = Message(
            id=new_message_id,
            chat_id=test_chat.id,
            sender_id=test_user.id,
            text="Hello, world!",
            idempotency_key="test-key-123",
            created_at=datetime.now(timezone.utc)
        )
        message_repository.create.return_value = created_message
        
        # Execute
        result = await message_service.send_message(
            chat_id=test_chat.id,
            sender_id=test_user.id,
            text="Hello, world!",
            idempotency_key="test-key-123"
        )
        
        # Verify
        assert result is not None
        assert result.id == new_message_id
        assert result.chat_id == test_chat.id
        assert result.sender_id == test_user.id
        assert result.text == "Hello, world!"
        
        # Verify that the repository method was called
        message_repository.create.assert_called_once()
        
        # Verify that the broadcaster was called
        message_broadcaster.broadcast_to_chat.assert_called_once()
        
    async def test_send_message_idempotency(self, message_service, message_repository, chat_repository, message_broadcaster, test_user, test_chat, test_message):
        """Test sending a message with an existing idempotency key."""
        # Setup
        chat_repository.get_by_id.return_value = test_chat
        message_repository.find_by_idempotency_key.return_value = test_message
        
        # Execute
        result = await message_service.send_message(
            chat_id=test_chat.id,
            sender_id=test_user.id,
            text="Hello again!",  # Different text, but same idempotency key
            idempotency_key="test-key-123"
        )
        
        # Verify
        assert result is not None
        assert result.id == test_message.id  # Should return the existing message
        
        # Verify that the repository create method was NOT called (idempotency)
        message_repository.create.assert_not_called()
        
        # Verify that the broadcaster was NOT called
        message_broadcaster.broadcast_to_chat.assert_not_called()
    
    async def test_send_message_chat_not_found(self, message_service, chat_repository):
        """Test sending a message to a non-existent chat."""
        # Setup
        chat_repository.get_by_id.return_value = None
        
        # Execute and verify
        with pytest.raises(ValueError, match="Chat not found"):
            await message_service.send_message(
                chat_id=uuid.uuid4(),
                sender_id=uuid.uuid4(),
                text="Hello, world!",
                idempotency_key="test-key-123"
            )
    
    async def test_send_message_user_not_participant(self, message_service, chat_repository, test_chat):
        """Test sending a message by a user who is not a participant."""
        # Setup
        chat_repository.get_by_id.return_value = test_chat
        non_participant_id = uuid.uuid4()  # User who is not a participant
        
        # Execute and verify
        with pytest.raises(ValueError, match="User is not a participant in this chat"):
            await message_service.send_message(
                chat_id=test_chat.id,
                sender_id=non_participant_id,
                text="Hello, world!",
                idempotency_key="test-key-123"
            )
    
    async def test_get_chat_messages(self, message_service, message_repository, test_chat):
        """Test retrieving chat messages."""
        # Setup
        message_ids = [uuid.uuid4() for _ in range(3)]
        messages = [
            Message(
                id=message_ids[i],
                chat_id=test_chat.id,
                sender_id=test_chat.participants[0].user_id,
                text=f"Message {i}",
                idempotency_key=f"key-{i}",
                created_at=datetime.now(timezone.utc)
            )
            for i in range(3)
        ]
        message_repository.get_chat_messages.return_value = messages
        
        # Execute
        result = await message_service.get_chat_messages(
            chat_id=test_chat.id,
            limit=50,
            before_id=None
        )
        
        # Verify
        assert result is not None
        assert len(result) == 3
        assert result[0].id == message_ids[0]
        
        # Verify repository method was called correctly
        message_repository.get_chat_messages.assert_called_once_with(
            chat_id=test_chat.id,
            limit=50,
            before_id=None
        )
    
    async def test_mark_as_read(self, message_service, message_repository, test_user, test_chat, test_message):
        """Test marking a message as read."""
        # Setup
        message_repository.update_read_status.return_value = True
        
        # Execute
        result = await message_service.mark_as_read(
            message_id=test_message.id,
            user_id=test_user.id
        )
        
        # Verify
        assert result is True
        
        # Verify repository method was called correctly
        message_repository.update_read_status.assert_called_once_with(
            message_id=test_message.id,
            user_id=test_user.id,
            read=True
        )
    
    async def test_mark_all_as_read(self, message_service, message_repository, test_user, test_chat):
        """Test marking all messages in a chat as read."""
        # Setup
        message_repository.mark_all_as_read.return_value = 5  # 5 messages marked as read
        
        # Execute
        result = await message_service.mark_all_as_read(
            chat_id=test_chat.id,
            user_id=test_user.id
        )
        
        # Verify
        assert result == 5
        
        # Verify repository method was called correctly
        message_repository.mark_all_as_read.assert_called_once_with(
            chat_id=test_chat.id,
            user_id=test_user.id
        )
    
    async def test_get_unread_count(self, message_service, message_repository, test_user, test_chat):
        """Test getting the count of unread messages in a chat."""
        # Setup
        message_repository.get_unread_count.return_value = 3
        
        # Execute
        result = await message_service.get_unread_count(
            chat_id=test_chat.id,
            user_id=test_user.id
        )
        
        # Verify
        assert result == 3
        
        # Verify repository method was called correctly
        message_repository.get_unread_count.assert_called_once_with(
            chat_id=test_chat.id,
            user_id=test_user.id
        ) 