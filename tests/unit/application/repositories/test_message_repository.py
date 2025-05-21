"""
Tests for the MessageRepository.
"""
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.user import User
from src.domain.models.chat import Chat, ChatType, ChatParticipant
from src.domain.models.message import Message, MessageStatus
from src.application.repositories.message_repository import MessageRepository
from src.infrastructure.repositories.message_repository import SQLAlchemyMessageRepository
from src.application.repositories.user_repository import UserRepository
from src.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from src.application.repositories.chat_repository import ChatRepository
from src.infrastructure.repositories.chat_repository import SQLAlchemyChatRepository


@pytest.mark.asyncio
class TestMessageRepository:
    """Test cases for the MessageRepository interface and its implementations."""
    
    @pytest_asyncio.fixture
    async def session(self, db_session):
        """Fixture for the database session."""
        yield db_session
            
    @pytest_asyncio.fixture
    async def repository(self, session: AsyncSession):
        """Fixture for the message repository."""
        return SQLAlchemyMessageRepository(session)
    
    @pytest_asyncio.fixture
    async def user_repository(self, session: AsyncSession):
        """Fixture for the user repository."""
        return SQLAlchemyUserRepository(session)
    
    @pytest_asyncio.fixture
    async def chat_repository(self, session: AsyncSession):
        """Fixture for the chat repository."""
        return SQLAlchemyChatRepository(session)
    
    @pytest_asyncio.fixture
    async def test_users(self, user_repository: UserRepository):
        """Fixture for test users."""
        users = [
            User(
                username="sender",
                name="Sender User",
                password_hash="hashed_password_1",
                phone="+1234567890",
            ),
            User(
                username="receiver",
                name="Receiver User",
                password_hash="hashed_password_2",
                phone="+2345678901",
            )
        ]
        
        created_users = []
        for user in users:
            created_user = await user_repository.create(user)
            created_users.append(created_user)
        
        return created_users
    
    @pytest_asyncio.fixture
    async def test_chat(self, chat_repository: ChatRepository, test_users: list[User]):
        """Fixture for a test chat."""
        chat = Chat(
            name=None,  # Private chat doesn't need a name
            type=ChatType.PRIVATE,
            participants=[
                ChatParticipant(user_id=test_users[0].id, role="member"),
                ChatParticipant(user_id=test_users[1].id, role="member"),
            ]
        )
        
        return await chat_repository.create(chat)
    
    @pytest_asyncio.fixture
    async def test_message(self, test_chat: Chat, test_users: list[User]):
        """Fixture for a test message."""
        return Message(
            chat_id=test_chat.id,
            sender_id=test_users[0].id,
            text="Hello, world!",
            idempotency_key="test-idempotency-key-1",
        )
    
    async def test_create_message(self, repository: MessageRepository, test_message: Message):
        """Test creating a message."""
        # Create a message through the repository
        created_message = await repository.create(test_message)
        
        # Verify the created message has the correct properties
        assert created_message.chat_id == test_message.chat_id
        assert created_message.sender_id == test_message.sender_id
        assert created_message.text == test_message.text
        assert created_message.idempotency_key == test_message.idempotency_key
        assert isinstance(created_message.id, UUID)
        assert isinstance(created_message.created_at, datetime)
        assert isinstance(created_message.updated_at, datetime)
    
    async def test_get_message_by_id(self, repository: MessageRepository, test_message: Message):
        """Test retrieving a message by ID."""
        # Create a message first
        created_message = await repository.create(test_message)
        
        # Retrieve the message by ID
        retrieved_message = await repository.get_by_id(created_message.id)
        
        # Verify the retrieved message matches the created message
        assert retrieved_message is not None
        assert retrieved_message.id == created_message.id
        assert retrieved_message.chat_id == created_message.chat_id
        assert retrieved_message.sender_id == created_message.sender_id
        assert retrieved_message.text == created_message.text
        assert retrieved_message.idempotency_key == created_message.idempotency_key
    
    async def test_get_non_existent_message(self, repository: MessageRepository):
        """Test retrieving a non-existent message."""
        # Generate a random UUID that shouldn't exist in the database
        random_id = uuid.uuid4()
        
        # Attempt to retrieve a message with the random ID
        retrieved_message = await repository.get_by_id(random_id)
        
        # Verify that no message was found
        assert retrieved_message is None
    
    async def test_get_chat_messages(self, repository: MessageRepository, test_chat: Chat, test_users: list[User]):
        """Test retrieving messages for a chat."""
        # Create multiple messages in the same chat
        messages = [
            Message(
                chat_id=test_chat.id,
                sender_id=test_users[0].id,
                text=f"Message {i}",
                idempotency_key=f"test-key-{i}",
                created_at=datetime.now(timezone.utc) - timedelta(minutes=i)  # Older as i increases
            )
            for i in range(1, 6)  # 5 messages
        ]
        
        created_messages = []
        for message in messages:
            created_message = await repository.create(message)
            created_messages.append(created_message)
        
        # Retrieve messages for the chat
        retrieved_messages = await repository.get_chat_messages(test_chat.id, limit=3)
        
        # Verify we got the expected number of messages
        assert len(retrieved_messages) == 3
        
        # Messages should be in reverse chronological order (newest first)
        assert retrieved_messages[0].text == "Message 1"
        assert retrieved_messages[1].text == "Message 2"
        assert retrieved_messages[2].text == "Message 3"
        
        # Test pagination with before_id
        retrieved_messages_page2 = await repository.get_chat_messages(
            test_chat.id, 
            limit=3,
            before_id=retrieved_messages[2].id
        )
        
        # Should get the remaining messages
        assert len(retrieved_messages_page2) == 2
        assert retrieved_messages_page2[0].text == "Message 4"
        assert retrieved_messages_page2[1].text == "Message 5"
    
    async def test_find_by_idempotency_key(self, repository: MessageRepository, test_message: Message):
        """Test finding a message by idempotency key."""
        # Create a message first
        created_message = await repository.create(test_message)
        
        # Find the message by idempotency key
        found_message = await repository.find_by_idempotency_key(
            test_message.chat_id,
            test_message.sender_id,
            test_message.idempotency_key
        )
        
        # Verify the found message matches the created message
        assert found_message is not None
        assert found_message.id == created_message.id
        
        # Try to find a message with a non-existent idempotency key
        non_existent_message = await repository.find_by_idempotency_key(
            test_message.chat_id,
            test_message.sender_id,
            "non-existent-key"
        )
        
        # Verify that no message was found
        assert non_existent_message is None
    
    async def test_update_read_status(self, repository: MessageRepository, test_message: Message, test_users: list[User]):
        """Test updating read status for a message."""
        # Create a message first
        created_message = await repository.create(test_message)
        
        # Update read status for the second user (receiver)
        result = await repository.update_read_status(
            created_message.id,
            test_users[1].id,
            True
        )
        
        # Verify the update was successful
        assert result is True
        
        # Verify the read status by getting unread count
        unread_count = await repository.get_unread_count(
            test_message.chat_id,
            test_users[1].id
        )
        
        # Unread count should be 0 since we marked the message as read
        assert unread_count == 0
    
    async def test_get_unread_count(self, repository: MessageRepository, test_chat: Chat, test_users: list[User]):
        """Test getting unread message count for a user in a chat."""
        # Create multiple messages
        messages = [
            Message(
                chat_id=test_chat.id,
                sender_id=test_users[0].id,
                text=f"Message {i}",
                idempotency_key=f"test-key-{i}",
            )
            for i in range(1, 4)  # 3 messages
        ]
        
        for message in messages:
            await repository.create(message)
        
        # Initially, all messages should be unread for user 2 (receiver)
        unread_count = await repository.get_unread_count(
            test_chat.id,
            test_users[1].id
        )
        
        # Verify the unread count is correct
        assert unread_count == 3
        
        # Mark one message as read
        await repository.update_read_status(
            messages[0].id,
            test_users[1].id,
            True
        )
        
        # Check unread count again
        unread_count = await repository.get_unread_count(
            test_chat.id,
            test_users[1].id
        )
        
        # Verify the unread count is updated
        assert unread_count == 2
    
    async def test_mark_all_as_read(self, repository: MessageRepository, test_chat: Chat, test_users: list[User]):
        """Test marking all messages in a chat as read for a user."""
        # Create multiple messages
        messages = [
            Message(
                chat_id=test_chat.id,
                sender_id=test_users[0].id,
                text=f"Message {i}",
                idempotency_key=f"test-key-{i}",
            )
            for i in range(1, 6)  # 5 messages
        ]
        
        for message in messages:
            await repository.create(message)
        
        # Initially, all messages should be unread for user 2 (receiver)
        unread_count = await repository.get_unread_count(
            test_chat.id,
            test_users[1].id
        )
        
        # Verify the unread count is correct
        assert unread_count == 5
        
        # Mark all messages as read
        marked_count = await repository.mark_all_as_read(
            test_chat.id,
            test_users[1].id
        )
        
        # Verify the correct number of messages were marked as read
        assert marked_count == 5
        
        # Check unread count again
        unread_count = await repository.get_unread_count(
            test_chat.id,
            test_users[1].id
        )
        
        # Verify all messages are now read
        assert unread_count == 0 