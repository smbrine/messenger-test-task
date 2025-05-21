"""
Tests for the Message domain model.
"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from src.domain.models.message import Message, MessageStatus


class TestMessageModel:
    """Test cases for the Message domain model."""

    def test_message_creation_valid(self):
        """Test creating a valid message."""
        message_id = uuid.uuid4()
        chat_id = uuid.uuid4()
        sender_id = uuid.uuid4()
        message = Message(
            id=message_id,
            chat_id=chat_id,
            sender_id=sender_id,
            text="Hello, world!",
            idempotency_key="test-key-123",
        )
        
        assert message.id == message_id
        assert message.chat_id == chat_id
        assert message.sender_id == sender_id
        assert message.text == "Hello, world!"
        assert message.idempotency_key == "test-key-123"
        assert isinstance(message.created_at, datetime)
        assert isinstance(message.updated_at, datetime)
        assert message.created_at.tzinfo == timezone.utc
        assert message.updated_at.tzinfo == timezone.utc

    def test_message_creation_with_default_id(self):
        """Test creating a message with default UUID."""
        message = Message(
            chat_id=uuid.uuid4(),
            sender_id=uuid.uuid4(),
            text="Hello, world!",
            idempotency_key="test-key-123",
        )
        assert isinstance(message.id, uuid.UUID)

    def test_message_creation_with_custom_timestamps(self):
        """Test creating a message with custom timestamps."""
        created_at = datetime.now(timezone.utc) - timedelta(days=1)
        updated_at = datetime.now(timezone.utc)
        
        message = Message(
            chat_id=uuid.uuid4(),
            sender_id=uuid.uuid4(),
            text="Hello, world!",
            idempotency_key="test-key-123",
            created_at=created_at,
            updated_at=updated_at,
        )
        
        assert message.created_at == created_at
        assert message.updated_at == updated_at

    def test_empty_message_text(self):
        """Test that message text cannot be empty."""
        with pytest.raises(ValueError, match="Message text cannot be empty"):
            Message(
                chat_id=uuid.uuid4(),
                sender_id=uuid.uuid4(),
                text="",  # Empty text
                idempotency_key="test-key-123",
            )
        
        with pytest.raises(ValueError, match="Message text cannot be empty"):
            Message(
                chat_id=uuid.uuid4(),
                sender_id=uuid.uuid4(),
                text="   ",  # Whitespace only
                idempotency_key="test-key-123",
            )

    def test_empty_idempotency_key(self):
        """Test that idempotency key cannot be empty."""
        with pytest.raises(ValueError, match="Idempotency key cannot be empty"):
            Message(
                chat_id=uuid.uuid4(),
                sender_id=uuid.uuid4(),
                text="Hello, world!",
                idempotency_key="",  # Empty key
            )
        
        with pytest.raises(ValueError, match="Idempotency key cannot be empty"):
            Message(
                chat_id=uuid.uuid4(),
                sender_id=uuid.uuid4(),
                text="Hello, world!",
                idempotency_key="   ",  # Whitespace only
            )

    def test_idempotency_key_too_long(self):
        """Test that idempotency key has length limitation."""
        with pytest.raises(ValueError, match="Idempotency key too long"):
            Message(
                chat_id=uuid.uuid4(),
                sender_id=uuid.uuid4(),
                text="Hello, world!",
                idempotency_key="a" * 256,  # Key too long
            )

    def test_message_equality(self):
        """Test message equality comparison."""
        message_id = uuid.uuid4()
        message1 = Message(
            id=message_id,
            chat_id=uuid.uuid4(),
            sender_id=uuid.uuid4(),
            text="Hello, world!",
            idempotency_key="test-key-123",
        )
        message2 = Message(
            id=message_id,  # Same ID
            chat_id=uuid.uuid4(),  # Different chat_id
            sender_id=uuid.uuid4(),  # Different sender_id
            text="Different text",  # Different text
            idempotency_key="different-key",  # Different key
        )
        message3 = Message(
            id=uuid.uuid4(),  # Different ID
            chat_id=message1.chat_id,  # Same chat_id
            sender_id=message1.sender_id,  # Same sender_id
            text=message1.text,  # Same text
            idempotency_key=message1.idempotency_key,  # Same key
        )
        
        assert message1 == message2  # Should be equal (same ID)
        assert message1 != message3  # Should be different (different ID)
        assert message1 != "not_a_message"  # Should be different (different type)


class TestMessageStatusModel:
    """Test cases for the MessageStatus domain model."""

    def test_message_status_creation(self):
        """Test creating a message status entity."""
        message_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        status = MessageStatus(
            message_id=message_id,
            user_id=user_id,
        )
        
        assert status.message_id == message_id
        assert status.user_id == user_id
        assert status.read is False
        assert status.read_at is None

    def test_message_status_creation_with_read(self):
        """Test creating a message status entity with read status."""
        read_at = datetime.now(timezone.utc)
        
        status = MessageStatus(
            message_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            read=True,
            read_at=read_at,
        )
        
        assert status.read is True
        assert status.read_at == read_at

    def test_mark_as_read(self):
        """Test marking a message as read."""
        status = MessageStatus(
            message_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        
        # Initially not read
        assert status.read is False
        assert status.read_at is None
        
        # Mark as read
        status.mark_as_read()
        
        # Should now be read
        assert status.read is True
        assert status.read_at is not None
        assert status.read_at.tzinfo == timezone.utc

    def test_read_at_not_set_when_read_is_false(self):
        """Test that read_at is None when read is False."""
        read_at = datetime.now(timezone.utc)
        
        # Try to create with read=False but read_at set
        status = MessageStatus(
            message_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            read=False,
            read_at=read_at,  # This should be ignored
        )
        
        assert status.read is False
        assert status.read_at is None  # Should be None despite passing a value 