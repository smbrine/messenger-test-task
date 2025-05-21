"""
Tests for the ChatRepository interface and implementations.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.domain.models.chat import Chat, ChatParticipant, ChatType
from src.application.repositories.chat_repository import ChatRepository


class TestChatRepository:
    """Test cases for the ChatRepository interface."""
    
    @pytest.fixture
    def mock_chat_repository(self):
        """Fixture for a mock chat repository."""
        repo = AsyncMock(spec=ChatRepository)
        return repo
    
    @pytest.fixture
    def sample_chat(self):
        """Fixture for a sample chat."""
        user_id1 = uuid.uuid4()
        user_id2 = uuid.uuid4()
        chat = Chat(
            id=uuid.uuid4(),
            type=ChatType.PRIVATE,
            participants=[
                ChatParticipant(user_id=user_id1, role="member"),
                ChatParticipant(user_id=user_id2, role="member")
            ]
        )
        return chat, user_id1, user_id2
    
    @pytest.fixture
    def sample_group_chat(self):
        """Fixture for a sample group chat."""
        user_id1 = uuid.uuid4()
        user_id2 = uuid.uuid4()
        chat = Chat(
            id=uuid.uuid4(),
            name="Test Group",
            type=ChatType.GROUP,
            participants=[
                ChatParticipant(user_id=user_id1, role="admin"),
                ChatParticipant(user_id=user_id2, role="member")
            ]
        )
        return chat, user_id1, user_id2
    
    async def test_create_chat(self, mock_chat_repository, sample_chat):
        """Test creating a chat."""
        chat, _, _ = sample_chat
        mock_chat_repository.create.return_value = chat
        
        result = await mock_chat_repository.create(chat)
        
        assert result == chat
        mock_chat_repository.create.assert_called_once_with(chat)
    
    async def test_get_by_id(self, mock_chat_repository, sample_chat):
        """Test retrieving a chat by ID."""
        chat, _, _ = sample_chat
        mock_chat_repository.get_by_id.return_value = chat
        
        result = await mock_chat_repository.get_by_id(chat.id)
        
        assert result == chat
        mock_chat_repository.get_by_id.assert_called_once_with(chat.id)
    
    async def test_get_by_id_not_found(self, mock_chat_repository):
        """Test retrieving a non-existent chat by ID."""
        mock_chat_repository.get_by_id.return_value = None
        chat_id = uuid.uuid4()
        
        result = await mock_chat_repository.get_by_id(chat_id)
        
        assert result is None
        mock_chat_repository.get_by_id.assert_called_once_with(chat_id)
    
    async def test_get_by_participant(self, mock_chat_repository, sample_chat):
        """Test retrieving chats by participant."""
        chat, user_id1, _ = sample_chat
        mock_chat_repository.get_by_participant.return_value = [chat]
        
        result = await mock_chat_repository.get_by_participant(user_id1)
        
        assert result == [chat]
        mock_chat_repository.get_by_participant.assert_called_once()
        args, kwargs = mock_chat_repository.get_by_participant.call_args
        assert args[0] == user_id1
        assert kwargs.get('limit', 50) == 50
        assert kwargs.get('offset', 0) == 0
    
    async def test_get_by_participant_with_pagination(self, mock_chat_repository, sample_chat):
        """Test retrieving chats by participant with pagination."""
        chat, user_id1, _ = sample_chat
        mock_chat_repository.get_by_participant.return_value = [chat]
        
        result = await mock_chat_repository.get_by_participant(user_id1, limit=10, offset=5)
        
        assert result == [chat]
        mock_chat_repository.get_by_participant.assert_called_once()
        args, kwargs = mock_chat_repository.get_by_participant.call_args
        assert args[0] == user_id1
        assert kwargs.get('limit') == 10
        assert kwargs.get('offset') == 5
    
    async def test_update_chat(self, mock_chat_repository, sample_group_chat):
        """Test updating a chat."""
        chat, _, _ = sample_group_chat
        updated_chat = Chat(
            id=chat.id,
            name="Updated Group",
            type=chat.type,
            participants=chat.participants
        )
        mock_chat_repository.update.return_value = updated_chat
        
        result = await mock_chat_repository.update(updated_chat)
        
        assert result == updated_chat
        assert result.name == "Updated Group"
        mock_chat_repository.update.assert_called_once_with(updated_chat)
    
    async def test_update_chat_not_found(self, mock_chat_repository, sample_chat):
        """Test updating a non-existent chat."""
        chat, _, _ = sample_chat
        mock_chat_repository.update.return_value = None
        
        result = await mock_chat_repository.update(chat)
        
        assert result is None
        mock_chat_repository.update.assert_called_once_with(chat)
    
    async def test_delete_chat(self, mock_chat_repository, sample_chat):
        """Test deleting a chat."""
        chat, _, _ = sample_chat
        mock_chat_repository.delete.return_value = True
        
        result = await mock_chat_repository.delete(chat.id)
        
        assert result is True
        mock_chat_repository.delete.assert_called_once_with(chat.id)
    
    async def test_delete_chat_not_found(self, mock_chat_repository):
        """Test deleting a non-existent chat."""
        chat_id = uuid.uuid4()
        mock_chat_repository.delete.return_value = False
        
        result = await mock_chat_repository.delete(chat_id)
        
        assert result is False
        mock_chat_repository.delete.assert_called_once_with(chat_id)
    
    async def test_add_participant(self, mock_chat_repository, sample_group_chat):
        """Test adding a participant to a chat."""
        chat, _, _ = sample_group_chat
        new_participant = ChatParticipant(user_id=uuid.uuid4(), role="member")
        mock_chat_repository.add_participant.return_value = True
        
        result = await mock_chat_repository.add_participant(chat.id, new_participant)
        
        assert result is True
        mock_chat_repository.add_participant.assert_called_once_with(chat.id, new_participant)
    
    async def test_add_participant_chat_not_found(self, mock_chat_repository):
        """Test adding a participant to a non-existent chat."""
        chat_id = uuid.uuid4()
        new_participant = ChatParticipant(user_id=uuid.uuid4(), role="member")
        mock_chat_repository.add_participant.return_value = False
        
        result = await mock_chat_repository.add_participant(chat_id, new_participant)
        
        assert result is False
        mock_chat_repository.add_participant.assert_called_once_with(chat_id, new_participant)
    
    async def test_remove_participant(self, mock_chat_repository, sample_group_chat):
        """Test removing a participant from a chat."""
        chat, _, user_id2 = sample_group_chat
        mock_chat_repository.remove_participant.return_value = True
        
        result = await mock_chat_repository.remove_participant(chat.id, user_id2)
        
        assert result is True
        mock_chat_repository.remove_participant.assert_called_once_with(chat.id, user_id2)
    
    async def test_remove_participant_not_found(self, mock_chat_repository, sample_group_chat):
        """Test removing a non-existent participant from a chat."""
        chat, _, _ = sample_group_chat
        user_id = uuid.uuid4()
        mock_chat_repository.remove_participant.return_value = False
        
        result = await mock_chat_repository.remove_participant(chat.id, user_id)
        
        assert result is False
        mock_chat_repository.remove_participant.assert_called_once_with(chat.id, user_id)
    
    async def test_update_participant_role(self, mock_chat_repository, sample_group_chat):
        """Test updating a participant's role in a chat."""
        chat, _, user_id2 = sample_group_chat
        mock_chat_repository.update_participant_role.return_value = True
        
        result = await mock_chat_repository.update_participant_role(chat.id, user_id2, "admin")
        
        assert result is True
        mock_chat_repository.update_participant_role.assert_called_once_with(chat.id, user_id2, "admin")
    
    async def test_update_participant_role_not_found(self, mock_chat_repository, sample_group_chat):
        """Test updating the role of a non-existent participant in a chat."""
        chat, _, _ = sample_group_chat
        user_id = uuid.uuid4()
        mock_chat_repository.update_participant_role.return_value = False
        
        result = await mock_chat_repository.update_participant_role(chat.id, user_id, "admin")
        
        assert result is False
        mock_chat_repository.update_participant_role.assert_called_once_with(chat.id, user_id, "admin") 