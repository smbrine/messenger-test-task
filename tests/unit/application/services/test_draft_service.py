"""
Tests for the draft service.
"""
import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock, MagicMock

from src.domain.models.draft import MessageDraft
from src.application.services.draft_service import DraftService
from src.application.repositories.draft_repository import get_draft_repository

@pytest.fixture
def draft_service():
    """Fixture for a draft service."""
    return DraftService(get_draft_repository())


@pytest.mark.asyncio
class TestDraftService:
    """Tests for the draft service."""
    
    @patch("src.application.services.draft_service.manager", new_callable=MagicMock)
    async def test_save_user_draft(self, mock_manager, draft_service: DraftService):
        """Test saving a user draft."""
        # Configure mocks
        draft_service.repository.save = AsyncMock(return_value=True)
        mock_manager.broadcast_to_user = AsyncMock(return_value=1)
        
        # Call function
        user_id = uuid4()
        chat_id = uuid4()
        text = "Test draft"
        result = await draft_service.save_user_draft(user_id, chat_id, text)
        
        # Check result
        assert result is not None
        assert result.user_id == user_id
        assert result.chat_id == chat_id
        assert result.text == text
        
        # Verify save was called
        draft_service.repository.save.assert_called_once()
        args, kwargs = draft_service.repository.save.call_args
        assert args[0].user_id == user_id
        assert args[0].chat_id == chat_id
        assert args[0].text == text
        
        # Verify broadcast was called
        mock_manager.broadcast_to_user.assert_called_once()
        args, kwargs = mock_manager.broadcast_to_user.call_args
        assert args[0] == user_id
        assert args[1]["type"] == "draft_update"
        assert args[1]["chat_id"] == str(chat_id)
        assert args[1]["text"] == text
        
    async def test_get_user_draft(self, draft_service: DraftService):
        """Test getting a user draft."""
        # Configure mock
        user_id = uuid4()
        chat_id = uuid4()
        mock_draft = MessageDraft(
            user_id=user_id,
            chat_id=chat_id,
            text="Test draft"
        )
        draft_service.repository.get = AsyncMock(return_value=mock_draft)
        
        # Call function
        result = await draft_service.get_user_draft(user_id, chat_id)
        
        # Check result
        assert result is not None
        assert result.user_id == user_id
        assert result.chat_id == chat_id
        assert result.text == "Test draft"
        
        # Verify mock was called
        draft_service.repository.get.assert_called_once_with(user_id, chat_id)
        
    async def test_get_user_draft_not_found(self, draft_service: DraftService):
        """Test getting a user draft that doesn't exist."""
        # Configure mock
        draft_service.repository.get = AsyncMock(return_value=None)
        
        # Call function
        user_id = uuid4()
        chat_id = uuid4()
        result = await draft_service.get_user_draft(user_id, chat_id)
        
        # Check result
        assert result is None
        
        # Verify mock was called
        draft_service.repository.get.assert_called_once_with(user_id, chat_id)
        
    @patch("src.application.services.draft_service.manager", new_callable=MagicMock)
    async def test_delete_user_draft(self, mock_manager, draft_service: DraftService):
        """Test deleting a user draft."""
        # Configure mocks
        draft_service.repository.delete = AsyncMock(return_value=True)
        mock_manager.broadcast_to_user = AsyncMock(return_value=1)
        
        # Call function
        user_id = uuid4()
        chat_id = uuid4()
        result = await draft_service.delete_user_draft(user_id, chat_id)
        
        # Check result
        assert result is True
        
        # Verify delete was called
        draft_service.repository.delete.assert_called_once_with(user_id, chat_id)
        
        # Verify broadcast was called
        mock_manager.broadcast_to_user.assert_called_once()
        args, kwargs = mock_manager.broadcast_to_user.call_args
        assert args[0] == user_id
        assert args[1]["type"] == "draft_delete"
        assert args[1]["chat_id"] == str(chat_id)
        
    @patch("src.application.services.draft_service.manager", new_callable=MagicMock)
    async def test_delete_user_draft_not_found(self, mock_manager, draft_service: DraftService):
        """Test deleting a user draft that doesn't exist."""
        # Configure mocks
        draft_service.repository.delete = AsyncMock(return_value=False)
        mock_manager.broadcast_to_user = AsyncMock(return_value=0)
        
        # Call function
        user_id = uuid4()
        chat_id = uuid4()
        result = await draft_service.delete_user_draft(user_id, chat_id)
        
        # Check result
        assert result is False
        
        # Verify delete was called
        draft_service.repository.delete.assert_called_once_with(user_id, chat_id)
        
        # Verify broadcast was NOT called
        mock_manager.broadcast_to_user.assert_not_called()
        
    @patch("src.application.services.draft_service.manager", new_callable=MagicMock)
    async def test_broadcast_draft_update(self, mock_manager, draft_service: DraftService):
        """Test broadcasting a draft update."""
        # Configure mock
        mock_manager.broadcast_to_user = AsyncMock(return_value=2)
        
        # Create a draft
        user_id = uuid4()
        chat_id = uuid4()
        draft = MessageDraft(
            user_id=user_id,
            chat_id=chat_id,
            text="Test draft"
        )
        
        # Call function
        result = await draft_service._broadcast_draft_update(draft)
        
        # Check result
        assert result == 2
        
        # Verify broadcast was called
        mock_manager.broadcast_to_user.assert_called_once()
        args, kwargs = mock_manager.broadcast_to_user.call_args
        assert args[0] == user_id
        assert args[1]["type"] == "draft_update"
        assert args[1]["chat_id"] == str(chat_id)
        assert args[1]["text"] == "Test draft"
        
    @patch("src.application.services.draft_service.manager", new_callable=MagicMock)
    async def test_broadcast_draft_deletion(self, mock_manager, draft_service: DraftService):
        """Test broadcasting a draft deletion."""
        # Configure mock
        mock_manager.broadcast_to_user = AsyncMock(return_value=2)
        
        # Call function
        user_id = uuid4()
        chat_id = uuid4()
        result = await draft_service._broadcast_draft_deletion(user_id, chat_id)
        
        # Check result
        assert result == 2
        
        # Verify broadcast was called
        mock_manager.broadcast_to_user.assert_called_once()
        args, kwargs = mock_manager.broadcast_to_user.call_args
        assert args[0] == user_id
        assert args[1]["type"] == "draft_delete"
        assert args[1]["chat_id"] == str(chat_id) 