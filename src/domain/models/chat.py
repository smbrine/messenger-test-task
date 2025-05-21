"""
Chat domain model.
"""
from datetime import datetime, timezone
import uuid
import enum
import typing as t
from pydantic import BaseModel, Field, field_validator, model_validator


class ChatType(str, enum.Enum):
    """
    Enum representing the type of chat.
    """
    PRIVATE = "private"
    GROUP = "group"


class ChatParticipant(BaseModel):
    """
    Represents a participant in a chat.
    """
    user_id: uuid.UUID
    role: str = "member"  # Default role is 'member'
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        """
        Validate that the role is either 'admin' or 'member'.
        
        Args:
            v: The role to validate
            
        Returns:
            The validated role
        
        Raises:
            ValueError: If the role is not valid
        """
        valid_roles = ["admin", "member"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v
    
    def __eq__(self, other: t.Any) -> bool:
        """
        Compare participants for equality.
        
        Args:
            other: The object to compare with
            
        Returns:
            True if equal, False otherwise
        """
        if not isinstance(other, ChatParticipant):
            return False
        return self.user_id == other.user_id
    
    class Config:
        """Pydantic model configuration."""
        frozen = True  # Make the model immutable


class Chat(BaseModel):
    """
    Chat domain model representing a chat in the system.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: t.Optional[str] = None
    type: ChatType
    participants: t.List[ChatParticipant]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @model_validator(mode='after')
    def validate_chat(self) -> 'Chat':
        """
        Validate chat based on its type.
        
        Returns:
            The validated chat
            
        Raises:
            ValueError: If validation fails
        """
        # Group chats must have a name
        if self.type == ChatType.GROUP and not self.name:
            raise ValueError("Group chats must have a name")
        
        # Private chats must have exactly 2 participants
        if self.type == ChatType.PRIVATE and len(self.participants) != 2:
            raise ValueError("Private chats must have exactly 2 participants")
        
        # All chats must have at least one participant
        if not self.participants:
            raise ValueError("Chat must have at least one participant")
        
        # Group chats must have at least one admin
        if self.type == ChatType.GROUP and not any(p.role == "admin" for p in self.participants):
            raise ValueError("Group chats must have at least one admin")
        
        return self
    
    def __eq__(self, other: t.Any) -> bool:
        """
        Compare chats for equality.
        
        Args:
            other: The object to compare with
            
        Returns:
            True if equal, False otherwise
        """
        if not isinstance(other, Chat):
            return False
        return self.id == other.id
    
    class Config:
        """Pydantic model configuration."""
        frozen = True  # Make the model immutable 