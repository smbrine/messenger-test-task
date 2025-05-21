"""
SQLAlchemy user model for database operations.
"""
import uuid
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID

from src.infrastructure.database.database import Base


class UserModel(Base):
    """
    User database model using SQLAlchemy ORM.
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=True)
    password_hash = Column(Text, nullable=False)
    phone = Column(String(20), unique=True, nullable=True, index=True) 