"""
SQLAlchemy implementation of the MessageRepository.
"""
import typing as t
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, update, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.message import Message, MessageStatus
from src.application.repositories.message_repository import MessageRepository
from src.infrastructure.database.database import get_session
from src.infrastructure.database.models.message import MessageModel, MessageStatusModel


class SQLAlchemyMessageRepository(MessageRepository):
    """
    SQLAlchemy implementation of the MessageRepository interface.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.
        
        Args:
            session: The SQLAlchemy async session to use for database operations
        """
        self.session = session
    
    def _map_to_domain(self, model: MessageModel) -> Message:
        """
        Map a database model to a domain entity.
        
        Args:
            model: The database model to map
            
        Returns:
            The corresponding domain entity
        """
        return Message(
            id=model.id,
            chat_id=model.chat_id,
            sender_id=model.sender_id,
            text=model.text,
            idempotency_key=model.idempotency_key,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    def _map_status_to_domain(self, model: MessageStatusModel) -> MessageStatus:
        """
        Map a status database model to a domain entity.
        
        Args:
            model: The database model to map
            
        Returns:
            The corresponding domain entity
        """
        return MessageStatus(
            message_id=model.message_id,
            user_id=model.user_id,
            read=model.read,
            read_at=model.read_at,
        )
    
    def _map_to_model(self, entity: Message) -> MessageModel:
        """
        Map a domain entity to a database model.
        
        Args:
            entity: The domain entity to map
            
        Returns:
            The corresponding database model
        """
        return MessageModel(
            id=entity.id,
            chat_id=entity.chat_id,
            sender_id=entity.sender_id,
            text=entity.text,
            idempotency_key=entity.idempotency_key,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
    
    def _map_status_to_model(self, entity: MessageStatus) -> MessageStatusModel:
        """
        Map a status domain entity to a database model.
        
        Args:
            entity: The domain entity to map
            
        Returns:
            The corresponding database model
        """
        return MessageStatusModel(
            message_id=entity.message_id,
            user_id=entity.user_id,
            read=entity.read,
            read_at=entity.read_at,
        )
    
    async def create(self, message: Message) -> Message:
        """
        Create a new message in the database.
        
        Args:
            message: The message to create
            
        Returns:
            The created message with database-generated ID
        """
        # Create a model from the entity
        model = self._map_to_model(message)
        
        # Add the model to the session and flush to get the ID
        self.session.add(model)
        await self.session.flush()
        
        # Commit the transaction to ensure it's saved to the database
        await self.session.commit()
        
        # Map the model back to an entity and return it
        return self._map_to_domain(model)
    
    async def get_by_id(self, message_id: UUID) -> t.Optional[Message]:
        """
        Retrieve a message by ID.
        
        Args:
            message_id: The UUID of the message to retrieve
            
        Returns:
            The message if found, None otherwise
        """
        # Build a query to find the message by ID
        query = select(MessageModel).where(MessageModel.id == message_id)
        
        # Execute the query
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        # Map the model to an entity if found
        if model is not None:
            return self._map_to_domain(model)
        
        return None
    
    async def get_chat_messages(
        self, 
        chat_id: UUID, 
        limit: int = 50, 
        before_id: t.Optional[UUID] = None
    ) -> t.List[Message]:
        """
        Get messages for a chat with pagination.
        
        Args:
            chat_id: The UUID of the chat
            limit: Maximum number of messages to return
            before_id: If provided, only return messages created before this message ID
            
        Returns:
            A list of messages in the chat
        """
        # Start with base query for chat
        query = select(MessageModel).where(MessageModel.chat_id == chat_id)
        
        # Add pagination with cursor if provided
        if before_id is not None:
            # Get the created_at value of the cursor message
            cursor_query = select(MessageModel.created_at).where(MessageModel.id == before_id)
            cursor_result = await self.session.execute(cursor_query)
            cursor_timestamp = cursor_result.scalar_one_or_none()
            
            if cursor_timestamp:
                # Get messages created before the cursor message
                query = query.where(MessageModel.created_at < cursor_timestamp)
        
        # Order by created_at descending (newest first)
        query = query.order_by(desc(MessageModel.created_at))
        
        # Add limit
        query = query.limit(limit)
        
        # Execute the query
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        # Map the models to entities
        return [self._map_to_domain(model) for model in models]
    
    async def find_by_idempotency_key(
        self, 
        chat_id: UUID, 
        sender_id: UUID, 
        idempotency_key: str
    ) -> t.Optional[Message]:
        """
        Find a message by its idempotency key.
        
        Args:
            chat_id: The UUID of the chat
            sender_id: The UUID of the message sender
            idempotency_key: The idempotency key to search for
            
        Returns:
            The message if found, None otherwise
        """
        # Build a query to find the message by idempotency key
        query = select(MessageModel).where(
            and_(
                MessageModel.chat_id == chat_id,
                MessageModel.sender_id == sender_id,
                MessageModel.idempotency_key == idempotency_key
            )
        )
        
        # Execute the query
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        # Map the model to an entity if found
        if model is not None:
            return self._map_to_domain(model)
        
        return None
    
    async def update_read_status(
        self, 
        message_id: UUID, 
        user_id: UUID, 
        read: bool = True
    ) -> bool:
        """
        Update read status for a message.
        
        Args:
            message_id: The UUID of the message
            user_id: The UUID of the user
            read: The new read status
            
        Returns:
            True if the status was updated, False if the message doesn't exist
        """
        # Check if the message exists
        message_query = select(MessageModel).where(MessageModel.id == message_id)
        message_result = await self.session.execute(message_query)
        message_model = message_result.scalar_one_or_none()
        
        if message_model is None:
            return False
        
        # Check if a status record already exists
        status_query = select(MessageStatusModel).where(
            and_(
                MessageStatusModel.message_id == message_id,
                MessageStatusModel.user_id == user_id
            )
        )
        status_result = await self.session.execute(status_query)
        status_model = status_result.scalar_one_or_none()
        
        if status_model is None:
            # Create a new status record
            read_at = datetime.now(timezone.utc) if read else None
            status_model = MessageStatusModel(
                message_id=message_id,
                user_id=user_id,
                read=read,
                read_at=read_at
            )
            self.session.add(status_model)
        else:
            # Update the existing status record
            status_model.read = read
            status_model.read_at = datetime.now(timezone.utc) if read else None
        
        await self.session.flush()
        
        # Commit the transaction to ensure it's saved to the database
        await self.session.commit()
        
        return True
    
    async def get_unread_count(
        self, 
        chat_id: UUID, 
        user_id: UUID
    ) -> int:
        """
        Get count of unread messages in a chat for a user.
        
        Args:
            chat_id: The UUID of the chat
            user_id: The UUID of the user
            
        Returns:
            The count of unread messages
        """
        # Get all message IDs for the chat
        messages_query = select(MessageModel.id).where(MessageModel.chat_id == chat_id)
        messages_result = await self.session.execute(messages_query)
        message_ids = messages_result.scalars().all()
        
        if not message_ids:
            return 0
        
        # Count messages that don't have a read status for this user or have read=False
        status_query = select(func.count()).where(
            and_(
                MessageModel.chat_id == chat_id,
                or_(
                    # No status record exists
                    ~MessageModel.id.in_(
                        select(MessageStatusModel.message_id).where(
                            and_(
                                MessageStatusModel.user_id == user_id,
                                MessageStatusModel.read == True,
                                MessageStatusModel.message_id.in_(message_ids)
                            )
                        )
                    )
                )
            )
        )
        
        result = await self.session.execute(status_query)
        return result.scalar_one()
    
    async def mark_all_as_read(
        self,
        chat_id: UUID,
        user_id: UUID
    ) -> int:
        """
        Mark all messages in a chat as read for a user.
        
        Args:
            chat_id: The UUID of the chat
            user_id: The UUID of the user
            
        Returns:
            The number of messages marked as read
        """
        # Get all message IDs for the chat
        message_query = select(MessageModel.id).where(MessageModel.chat_id == chat_id)
        message_result = await self.session.execute(message_query)
        message_ids = message_result.scalars().all()
        
        if not message_ids:
            return 0
        
        # Get existing status records for these messages
        status_query = select(MessageStatusModel).where(
            and_(
                MessageStatusModel.message_id.in_(message_ids),
                MessageStatusModel.user_id == user_id
            )
        )
        status_result = await self.session.execute(status_query)
        existing_statuses = {status.message_id: status for status in status_result.scalars().all()}
        
        # Count of messages that will be marked as read
        marked_count = 0
        
        # Current time for read_at
        now = datetime.now(timezone.utc)
        
        # Update existing status records or create new ones
        for message_id in message_ids:
            if message_id in existing_statuses:
                # Update if not already read
                status = existing_statuses[message_id]
                if not status.read:
                    status.read = True
                    status.read_at = now
                    marked_count += 1
            else:
                # Create new status record
                status = MessageStatusModel(
                    message_id=message_id,
                    user_id=user_id,
                    read=True,
                    read_at=now
                )
                self.session.add(status)
                marked_count += 1
        
        await self.session.flush()
        return marked_count 
    
async def get_message_repository() -> MessageRepository:
    """
    Factory function to create a chat repository instance.
    
    Returns:
        A chat repository implementation
    """
    session = await get_session()
    return SQLAlchemyMessageRepository(session) 