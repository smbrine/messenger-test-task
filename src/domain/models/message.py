"""
Message domain model.
"""
from datetime import datetime, timezone
from uuid import UUID, uuid4
import typing as t
from pydantic import BaseModel, Field, field_validator


class Message(BaseModel):
    """
    Message domain model representing a message in a chat.
    """
    id: UUID = Field(default_factory=uuid4)
    chat_id: UUID
    sender_id: UUID
    text: str
    idempotency_key: str
    created_at: datetime = None
    updated_at: datetime = None
    
    def __init__(self, **data):
        # Ensure created_at and updated_at are set with proper timezone
        now = datetime.now(timezone.utc)
        if 'created_at' not in data or data['created_at'] is None:
            data['created_at'] = now
        if 'updated_at' not in data or data['updated_at'] is None:
            data['updated_at'] = data['created_at']
        
        super().__init__(**data)
        self.validate()
    
    def validate(self) -> None:
        """
        Validate the message.
        
        Raises:
            ValueError: If message validation fails
        """
        if not self.text or len(self.text.strip()) == 0:
            raise ValueError("Message text cannot be empty")
        
        self.validate_idempotency_key(self.idempotency_key)
    
    @staticmethod
    def validate_idempotency_key(key: str) -> None:
        """
        Validate the idempotency key.
        
        Args:
            key: The idempotency key to validate
            
        Raises:
            ValueError: If the key is invalid
        """
        if not key or len(key.strip()) == 0:
            raise ValueError("Idempotency key cannot be empty")
        if len(key) > 255:
            raise ValueError("Idempotency key too long (max 255 characters)")
    
    def __eq__(self, other: t.Any) -> bool:
        """
        Compare messages for equality.
        
        Args:
            other: The object to compare with
            
        Returns:
            True if equal, False otherwise
        """
        if not isinstance(other, Message):
            return False
        return self.id == other.id
    
    class Config:
        """Pydantic model configuration."""
        frozen = True  # Make the model immutable


class MessageStatus(BaseModel):
    """
    Message status domain model representing the read status of a message for a user.
    """
    message_id: UUID
    user_id: UUID
    read: bool = False
    read_at: t.Optional[datetime] = None
    
    def __init__(self, **data):
        # Ensure read_at is None if read is False
        if 'read' in data and not data['read']:
            data['read_at'] = None
        
        super().__init__(**data)
    
    def mark_as_read(self) -> None:
        """
        Mark the message as read.
        
        Sets the read status to True and sets read_at to the current time
        if not already read.
        """
        if not self.read:
            # Using object.__setattr__ because the model is frozen
            object.__setattr__(self, 'read', True)
            object.__setattr__(self, 'read_at', datetime.now(timezone.utc))
    
    class Config:
        """Pydantic model configuration."""
        frozen = True  # Make the model immutable 