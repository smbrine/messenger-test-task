"""
Tests for Redis-based draft store.
"""
import json
import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock

from src.config.settings import get_settings
from src.domain.models.draft import MessageDraft
from src.infrastructure.redis.draft_store import (
    save_draft, 
    get_draft, 
    delete_draft
)


@pytest.fixture
def test_draft():
    """Fixture for a test draft."""
    return MessageDraft(
        user_id=uuid4(),
        chat_id=uuid4(),
        text="Test draft content",
        updated_at=datetime.now(timezone.utc)
    )

@pytest.mark.asyncio
class TestDraftStore:
    """Tests for draft store functions."""
    
    @patch("src.infrastructure.redis.draft_store.set_key", new_callable=AsyncMock)
    async def test_save_draft(self, mock_set_key, test_draft):
        """Test saving a draft to Redis."""
        # Configure mock
        mock_set_key.return_value = True
        
        # Call function
        result = await save_draft(test_draft)
        
        # Check result
        assert result is True
        
        # Verify mock was called correctly
        settings = get_settings()
        draft_key = settings.redis.draft_key_format
        expected_key = draft_key.format(
            user_id=str(test_draft.user_id),
            chat_id=str(test_draft.chat_id)
        )
        
        # Verify that the function was called
        mock_set_key.assert_called_once()
        
        # Get the actual arguments passed
        args, kwargs = mock_set_key.call_args
        
        # Verify first argument (key)
        assert args[0] == expected_key
        
        # Verify JSON structure
        data = json.loads(args[1])
        assert "text" in data
        assert data["text"] == test_draft.text
        assert "updated_at" in data
        
        # Verify expiry
        settings = get_settings()
        assert kwargs["expiry"] == settings.redis.draft_ttl
    
    @patch("src.infrastructure.redis.draft_store.get_key", new_callable=AsyncMock)
    async def test_get_draft_existing(self, mock_get_key, test_draft):
        """Test getting an existing draft from Redis."""
        # Configure mock
        mock_data = {
            "text": test_draft.text,
            "updated_at": test_draft.updated_at.isoformat()
        }
        mock_get_key.return_value = json.dumps(mock_data)
        
        # Call function
        result = await get_draft(test_draft.user_id, test_draft.chat_id)
        
        # Check result
        assert result is not None
        assert result.user_id == test_draft.user_id
        assert result.chat_id == test_draft.chat_id
        assert result.text == test_draft.text
        
        # Verify mock was called correctly
        settings = get_settings()
        draft_key = settings.redis.draft_key_format
        expected_key = draft_key.format(
            user_id=str(test_draft.user_id),
            chat_id=str(test_draft.chat_id)
        )
        mock_get_key.assert_called_once_with(expected_key)
    
    @patch("src.infrastructure.redis.draft_store.get_key", new_callable=AsyncMock)
    async def test_get_draft_nonexistent(self, mock_get_key):
        """Test getting a nonexistent draft from Redis."""
        # Configure mock
        mock_get_key.return_value = None
        
        # Call function
        user_id = uuid4()
        chat_id = uuid4()
        result = await get_draft(user_id, chat_id)
        
        # Check result
        assert result is None
        
        # Verify mock was called correctly
        settings = get_settings()
        draft_key = settings.redis.draft_key_format
        expected_key = draft_key.format(
            user_id=str(user_id),
            chat_id=str(chat_id)
        )
        mock_get_key.assert_called_once_with(expected_key)
    
    @patch("src.infrastructure.redis.draft_store.get_key", new_callable=AsyncMock)
    async def test_get_draft_invalid_json(self, mock_get_key):
        """Test getting a draft with invalid JSON data."""
        # Configure mock to return invalid JSON
        mock_get_key.return_value = "not valid json"
        
        # Call function
        user_id = uuid4()
        chat_id = uuid4()
        result = await get_draft(user_id, chat_id)
        
        # Check result
        assert result is None
    
    @patch("src.infrastructure.redis.draft_store.delete_key", new_callable=AsyncMock)
    async def test_delete_draft(self, mock_delete_key):
        """Test deleting a draft from Redis."""
        # Configure mock
        mock_delete_key.return_value = 1
        
        # Call function
        user_id = uuid4()
        chat_id = uuid4()
        result = await delete_draft(user_id, chat_id)
        
        # Check result
        assert result == 1
        
        # Verify mock was called correctly
        settings = get_settings()
        draft_key = settings.redis.draft_key_format
        expected_key = draft_key.format(
            user_id=str(user_id),
            chat_id=str(chat_id)
        )
        mock_delete_key.assert_called_once_with(expected_key) 