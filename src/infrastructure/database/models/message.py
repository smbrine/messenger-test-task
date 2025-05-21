"""
SQLAlchemy message and message status models for database operations.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Text, String, Boolean, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from src.infrastructure.database.database import Base


class MessageModel(Base):
    """
    Message database model using SQLAlchemy ORM.
    """
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    idempotency_key = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), 
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    statuses = relationship("MessageStatusModel", back_populates="message", cascade="all, delete-orphan")
    
    # Indexes for efficient queries
    __table_args__ = (
        # Index for retrieving messages by chat with creation timestamp
        Index("ix_messages_chat_id_created_at", "chat_id", "created_at"),
        
        # Unique constraint for idempotency key
        UniqueConstraint("chat_id", "sender_id", "idempotency_key", name="uq_message_idempotency"),
    )


class MessageStatusModel(Base):
    """
    Message status database model using SQLAlchemy ORM.
    """
    __tablename__ = "message_status"
    
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    message = relationship("MessageModel", back_populates="statuses")
    
    # Index for efficiently retrieving unread messages
    __table_args__ = (
        Index("ix_message_status_user_id_read", "user_id", "read"),
    ) 