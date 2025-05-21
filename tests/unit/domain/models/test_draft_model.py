"""
Tests for the draft model in the domain layer.
"""
import pytest
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta

from src.domain.models.draft import MessageDraft


def test_create_message_draft():
    """Test creating a message draft."""
    user_id = uuid4()
    chat_id = uuid4()
    text = "Hello, world!"
    
    draft = MessageDraft(
        user_id=user_id,
        chat_id=chat_id,
        text=text
    )
    
    assert draft.user_id == user_id
    assert draft.chat_id == chat_id
    assert draft.text == text
    assert draft.updated_at is not None
    assert draft.updated_at.tzinfo == timezone.utc


def test_create_message_draft_with_custom_updated_at():
    """Test creating a message draft with a custom updated_at time."""
    user_id = uuid4()
    chat_id = uuid4()
    text = "Hello, world!"
    updated_at = datetime.now(timezone.utc) - timedelta(hours=1)
    
    draft = MessageDraft(
        user_id=user_id,
        chat_id=chat_id,
        text=text,
        updated_at=updated_at
    )
    
    assert draft.updated_at == updated_at


def test_message_draft_is_mutable():
    """Test that message draft can be modified after creation."""
    draft = MessageDraft(
        user_id=uuid4(),
        chat_id=uuid4(),
        text="Initial text"
    )
    
    # Update text
    new_text = "Updated text"
    draft.text = new_text
    
    assert draft.text == new_text 