"""
SQLAlchemy chat and chat participant models for database operations.
"""
from datetime import datetime, timezone
import uuid
import enum
from sqlalchemy import Column, String, Enum, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from src.infrastructure.database.database import Base


class ChatTypeEnum(enum.Enum):
    """
    Enum representing the type of chat in the database.
    """
    PRIVATE = "private"
    GROUP = "group"


class ChatModel(Base):
    """
    Chat database model using SQLAlchemy ORM.
    """
    __tablename__ = "chats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=True)
    type = Column(Enum(ChatTypeEnum), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))  
    
    # Relationships
    participants = relationship("ChatParticipantModel", back_populates="chat", cascade="all, delete-orphan")


class ChatParticipantModel(Base):
    """
    Chat participant database model using SQLAlchemy ORM.
    """
    __tablename__ = "chat_participants"
    
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(20), nullable=False, default="member")
    
    # Relationships
    chat = relationship("ChatModel", back_populates="participants")
    
    # Constraint to ensure a user is only in a chat once
    __table_args__ = (
        UniqueConstraint("chat_id", "user_id", name="uq_chat_participant"),
    ) 