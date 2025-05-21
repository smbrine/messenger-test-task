"""
Tests for the ChatService.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.domain.models.chat import Chat, ChatParticipant, ChatType
from src.application.services.chat_service import ChatService
from src.application.repositories.chat_repository import ChatRepository
from src.application.repositories.user_repository import UserRepository
from src.domain.models.user import User


class TestChatService:
    """Test cases for the ChatService."""
    
    @pytest.fixture
    def mock_chat_repository(self):
        """Fixture for a mock chat repository."""
        repo = AsyncMock(spec=ChatRepository)
        return repo
    
    @pytest.fixture
    def mock_user_repository(self):
        """Fixture for a mock user repository."""
        repo = AsyncMock(spec=UserRepository)
        return repo
    
    @pytest.fixture
    def chat_service(self, mock_chat_repository, mock_user_repository):
        """Fixture for a chat service with mock repositories."""
        return ChatService(
            chat_repository=mock_chat_repository,
            user_repository=mock_user_repository
        )
    
    @pytest.fixture
    def sample_users(self):
        """Fixture for sample users."""
        user1 = User(
            id=uuid.uuid4(),
            username="user1",
            password_hash="hash1"
        )
        user2 = User(
            id=uuid.uuid4(),
            username="user2",
            password_hash="hash2"
        )
        return user1, user2
    
    @pytest.fixture
    def sample_chat(self, sample_users):
        """Fixture for a sample chat."""
        user1, user2 = sample_users
        chat = Chat(
            id=uuid.uuid4(),
            type=ChatType.PRIVATE,
            participants=[
                ChatParticipant(user_id=user1.id, role="member"),
                ChatParticipant(user_id=user2.id, role="member")
            ]
        )
        return chat, user1, user2
    
    @pytest.fixture
    def sample_group_chat(self, sample_users):
        """Fixture for a sample group chat."""
        user1, user2 = sample_users
        chat = Chat(
            id=uuid.uuid4(),
            name="Test Group",
            type=ChatType.GROUP,
            participants=[
                ChatParticipant(user_id=user1.id, role="admin"),
                ChatParticipant(user_id=user2.id, role="member")
            ]
        )
        return chat, user1, user2
    
    async def test_create_private_chat(self, chat_service, mock_chat_repository, sample_users):
        """Test creating a private chat."""
        user1, user2 = sample_users
        
        # Configure mocks
        # First check for existing chat returns None
        mock_chat_repository.find_private_chat.return_value = None
        
        # Create a new chat
        expected_chat = Chat(
            id=uuid.uuid4(),
            type=ChatType.PRIVATE,
            participants=[
                ChatParticipant(user_id=user1.id, role="member"),
                ChatParticipant(user_id=user2.id, role="member")
            ]
        )
        mock_chat_repository.create.return_value = expected_chat
        
        # Call the service method
        result = await chat_service.create_private_chat(user1.id, user2.id)
        
        # Verify the result
        assert result is not None
        assert result.type == ChatType.PRIVATE
        assert len(result.participants) == 2
        assert any(p.user_id == user1.id for p in result.participants)
        assert any(p.user_id == user2.id for p in result.participants)
        
        # Verify repository calls
        mock_chat_repository.find_private_chat.assert_called_once_with(user1.id, user2.id)
        mock_chat_repository.create.assert_called_once()
    
    async def test_create_private_chat_existing(self, chat_service, mock_chat_repository, sample_users):
        """Test creating a private chat when one already exists."""
        user1, user2 = sample_users
        
        # Configure mocks
        existing_chat = Chat(
            id=uuid.uuid4(),
            type=ChatType.PRIVATE,
            participants=[
                ChatParticipant(user_id=user1.id, role="member"),
                ChatParticipant(user_id=user2.id, role="member")
            ]
        )
        mock_chat_repository.find_private_chat.return_value = existing_chat
        
        # Call the service method
        result = await chat_service.create_private_chat(user1.id, user2.id)
        
        # Verify the result
        assert result is not None
        assert result.id == existing_chat.id
        assert result.type == ChatType.PRIVATE
        
        # Verify repository calls
        mock_chat_repository.find_private_chat.assert_called_once_with(user1.id, user2.id)
        # Create should not be called since we found an existing chat
        mock_chat_repository.create.assert_not_called()
    
    async def test_create_group_chat(self, chat_service, mock_chat_repository, sample_users):
        """Test creating a group chat."""
        user1, user2 = sample_users
        
        # Configure mocks
        mock_chat_repository.create.return_value = Chat(
            id=uuid.uuid4(),
            name="Test Group",
            type=ChatType.GROUP,
            participants=[
                ChatParticipant(user_id=user1.id, role="admin"),
                ChatParticipant(user_id=user2.id, role="member")
            ]
        )
        
        # Call the service method
        result = await chat_service.create_group_chat(
            name="Test Group",
            admin_id=user1.id,
            member_ids=[user2.id]
        )
        
        # Verify the result
        assert result is not None
        assert result.type == ChatType.GROUP
        assert result.name == "Test Group"
        assert len(result.participants) == 2
        
        admin_participants = [p for p in result.participants if p.role == "admin"]
        assert len(admin_participants) == 1
        assert admin_participants[0].user_id == user1.id
        
        # Verify repository calls
        mock_chat_repository.create.assert_called_once()
    
    async def test_get_chat(self, chat_service, mock_chat_repository, sample_chat):
        """Test getting a chat by ID."""
        chat, _, _ = sample_chat
        
        # Configure mocks
        mock_chat_repository.get_by_id.return_value = chat
        
        # Call the service method
        result = await chat_service.get_chat(chat.id)
        
        # Verify the result
        assert result == chat
        
        # Verify repository calls
        mock_chat_repository.get_by_id.assert_called_once_with(chat.id)
    
    async def test_get_chat_not_found(self, chat_service, mock_chat_repository):
        """Test getting a non-existent chat."""
        chat_id = uuid.uuid4()
        
        # Configure mocks
        mock_chat_repository.get_by_id.return_value = None
        
        # Call the service method
        result = await chat_service.get_chat(chat_id)
        
        # Verify the result
        assert result is None
        
        # Verify repository calls
        mock_chat_repository.get_by_id.assert_called_once_with(chat_id)
    
    async def test_get_user_chats(self, chat_service, mock_chat_repository, sample_chat):
        """Test getting a user's chats."""
        chat, user1, _ = sample_chat
        
        # Configure mocks
        mock_chat_repository.get_by_participant.return_value = [chat]
        
        # Call the service method
        result = await chat_service.get_user_chats(user1.id)
        
        # Verify the result
        assert result == [chat]
        
        # Verify repository calls
        mock_chat_repository.get_by_participant.assert_called_once_with(user1.id, 50, 0)
    
    async def test_add_participant(self, chat_service, mock_chat_repository, mock_user_repository, sample_group_chat):
        """Test adding a participant to a group chat."""
        chat, _, _ = sample_group_chat
        new_user = User(
            id=uuid.uuid4(),
            username="new_user",
            password_hash="hash3"
        )
        
        # Configure mocks
        mock_chat_repository.get_by_id.return_value = chat
        mock_user_repository.get_by_id.return_value = new_user
        mock_chat_repository.add_participant.return_value = True
        
        # Call the service method
        result = await chat_service.add_participant(chat.id, new_user.id)
        
        # Verify the result
        assert result is True
        
        # Verify repository calls
        mock_chat_repository.get_by_id.assert_called_once_with(chat.id)
        mock_user_repository.get_by_id.assert_called_once_with(new_user.id)
        mock_chat_repository.add_participant.assert_called_once()
    
    async def test_add_participant_to_private_chat(self, chat_service, mock_chat_repository, mock_user_repository, sample_chat):
        """Test that adding a participant to a private chat fails."""
        chat, _, _ = sample_chat
        new_user = User(
            id=uuid.uuid4(),
            username="new_user",
            password_hash="hash3"
        )
        
        # Configure mocks
        mock_chat_repository.get_by_id.return_value = chat
        mock_user_repository.get_by_id.return_value = new_user
        
        # Call the service method and expect an exception
        with pytest.raises(ValueError, match="Cannot add participants to a private chat"):
            await chat_service.add_participant(chat.id, new_user.id)
        
        # Verify repository calls
        mock_chat_repository.get_by_id.assert_called_once_with(chat.id)
        mock_user_repository.get_by_id.assert_called_once_with(new_user.id)
        mock_chat_repository.add_participant.assert_not_called()
    
    async def test_remove_participant(self, chat_service, mock_chat_repository, sample_group_chat):
        """Test removing a participant from a group chat."""
        chat, _, user2 = sample_group_chat
        
        # Configure mocks
        mock_chat_repository.get_by_id.return_value = chat
        mock_chat_repository.remove_participant.return_value = True
        
        # Call the service method
        result = await chat_service.remove_participant(chat.id, user2.id)
        
        # Verify the result
        assert result is True
        
        # Verify repository calls
        mock_chat_repository.get_by_id.assert_called_once_with(chat.id)
        mock_chat_repository.remove_participant.assert_called_once_with(chat.id, user2.id)
    
    async def test_remove_participant_from_private_chat(self, chat_service, mock_chat_repository, sample_chat):
        """Test that removing a participant from a private chat fails."""
        chat, _, user2 = sample_chat
        
        # Configure mocks
        mock_chat_repository.get_by_id.return_value = chat
        
        # Call the service method and expect an exception
        with pytest.raises(ValueError, match="Cannot remove participants from a private chat"):
            await chat_service.remove_participant(chat.id, user2.id)
        
        # Verify repository calls
        mock_chat_repository.get_by_id.assert_called_once_with(chat.id)
        mock_chat_repository.remove_participant.assert_not_called()
    
    async def test_make_admin(self, chat_service, mock_chat_repository, sample_group_chat):
        """Test making a participant an admin in a group chat."""
        chat, _, user2 = sample_group_chat
        
        # Configure mocks
        mock_chat_repository.get_by_id.return_value = chat
        mock_chat_repository.update_participant_role.return_value = True
        
        # Call the service method
        result = await chat_service.make_admin(chat.id, user2.id)
        
        # Verify the result
        assert result is True
        
        # Verify repository calls
        mock_chat_repository.get_by_id.assert_called_once_with(chat.id)
        mock_chat_repository.update_participant_role.assert_called_once_with(chat.id, user2.id, "admin")
    
    async def test_make_admin_in_private_chat(self, chat_service, mock_chat_repository, sample_chat):
        """Test that making a participant an admin in a private chat fails."""
        chat, _, user2 = sample_chat
        
        # Configure mocks
        mock_chat_repository.get_by_id.return_value = chat
        
        # Call the service method and expect an exception
        with pytest.raises(ValueError, match="Cannot change roles in a private chat"):
            await chat_service.make_admin(chat.id, user2.id)
        
        # Verify repository calls
        mock_chat_repository.get_by_id.assert_called_once_with(chat.id)
        mock_chat_repository.update_participant_role.assert_not_called() 