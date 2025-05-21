"""
SQLAlchemy implementation of the ChatRepository.
"""
import uuid
import typing as t
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.domain.models.chat import Chat, ChatParticipant, ChatType
from src.application.repositories.chat_repository import ChatRepository
from src.infrastructure.database.models.chat import ChatModel, ChatParticipantModel, ChatTypeEnum
from src.infrastructure.database.database import get_session


class SQLAlchemyChatRepository(ChatRepository):
    """
    SQLAlchemy implementation of the ChatRepository interface.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.
        
        Args:
            session: The SQLAlchemy async session to use for database operations
        """
        self.session = session
    
    def _map_chat_type_to_enum(self, chat_type: ChatType) -> ChatTypeEnum:
        """
        Map domain ChatType to database enum.
        
        Args:
            chat_type: The domain chat type
            
        Returns:
            The corresponding database enum
        """
        if chat_type == ChatType.PRIVATE:
            return ChatTypeEnum.PRIVATE
        return ChatTypeEnum.GROUP
    
    def _map_enum_to_chat_type(self, enum_type: ChatTypeEnum) -> ChatType:
        """
        Map database enum to domain ChatType.
        
        Args:
            enum_type: The database enum
            
        Returns:
            The corresponding domain chat type
        """
        if enum_type == ChatTypeEnum.PRIVATE:
            return ChatType.PRIVATE
        return ChatType.GROUP
    
    def _map_to_domain_participant(self, model: ChatParticipantModel) -> ChatParticipant:
        """
        Map a database participant model to a domain entity.
        
        Args:
            model: The database model to map
            
        Returns:
            The corresponding domain entity
        """
        return ChatParticipant(
            user_id=model.user_id,
            role=model.role,
        )
    
    def _map_to_domain(self, model: ChatModel) -> Chat:
        """
        Map a database model to a domain entity.
        
        Args:
            model: The database model to map
            
        Returns:
            The corresponding domain entity
        """
        return Chat(
            id=model.id,
            name=model.name,
            type=self._map_enum_to_chat_type(model.type),
            participants=[self._map_to_domain_participant(p) for p in model.participants],
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    def _map_to_model_participant(self, chat_id: uuid.UUID, entity: ChatParticipant) -> ChatParticipantModel:
        """
        Map a domain participant entity to a database model.
        
        Args:
            chat_id: The UUID of the chat this participant belongs to
            entity: The domain entity to map
            
        Returns:
            The corresponding database model
        """
        return ChatParticipantModel(
            chat_id=chat_id,
            user_id=entity.user_id,
            role=entity.role,
        )
    
    def _map_to_model(self, entity: Chat) -> t.Tuple[ChatModel, t.List[ChatParticipantModel]]:
        """
        Map a domain entity to a database model.
        
        Args:
            entity: The domain entity to map
            
        Returns:
            A tuple containing the chat model and participant models
        """
        chat_model = ChatModel(
            id=entity.id,
            name=entity.name,
            type=self._map_chat_type_to_enum(entity.type),
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
        
        participant_models = [
            self._map_to_model_participant(entity.id, p) for p in entity.participants
        ]
        
        return chat_model, participant_models
    
    async def create(self, chat: Chat) -> Chat:
        """
        Create a new chat in the database.
        
        Args:
            chat: The chat to create
            
        Returns:
            The created chat with database-generated ID
        """
        # Create models from the entity
        chat_model, participant_models = self._map_to_model(chat)
        
        # Add the models to the session
        self.session.add(chat_model)
        await self.session.flush()
        
        # Add participants
        for participant_model in participant_models:
            self.session.add(participant_model)
        
        await self.session.flush()
        
        # Refresh to get the relationships
        await self.session.refresh(chat_model, ["participants"])
        
        # Map the model back to an entity and return it
        return self._map_to_domain(chat_model)
    
    async def get_by_id(self, chat_id: uuid.UUID) -> t.Optional[Chat]:
        """
        Retrieve a chat by ID.
        
        Args:
            chat_id: The UUID of the chat to retrieve
            
        Returns:
            The chat if found, None otherwise
        """
        # Build a query to find the chat by ID with participants loaded
        query = (
            select(ChatModel)
            .options(selectinload(ChatModel.participants))
            .where(ChatModel.id == chat_id)
        )
        
        # Execute the query
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        
        # Map the model to an entity if found
        if model is not None:
            return self._map_to_domain(model)
        
        return None
    
    async def get_by_participant(self, user_id: uuid.UUID, limit: int = 50, offset: int = 0) -> t.List[Chat]:
        """
        Retrieve chats where a user is a participant.
        
        Args:
            user_id: The UUID of the user
            limit: Maximum number of chats to return
            offset: Number of chats to skip
            
        Returns:
            A list of chats where the user is a participant
        """
        # Build a query to find chats where the user is a participant
        query = (
            select(ChatModel)
            .join(ChatParticipantModel)
            .options(selectinload(ChatModel.participants))
            .where(ChatParticipantModel.user_id == user_id)
            .limit(limit)
            .offset(offset)
        )
        
        # Execute the query
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        # Map the models to entities
        return [self._map_to_domain(model) for model in models]
    
    async def find_private_chat(self, user1_id: uuid.UUID, user2_id: uuid.UUID) -> t.Optional[Chat]:
        """
        Find a private chat between two specific users.
        
        Args:
            user1_id: The UUID of the first user
            user2_id: The UUID of the second user
            
        Returns:
            The chat if found, None otherwise
        """
        # Find chat IDs where both users are participants
        participant_query = (
            select(ChatParticipantModel.chat_id)
            .where(ChatParticipantModel.user_id.in_([user1_id, user2_id]))
            .group_by(ChatParticipantModel.chat_id)
            .having(func.count(ChatParticipantModel.user_id.distinct()) == 2)
        )
        
        # Execute the query to get chat IDs
        participant_result = await self.session.execute(participant_query)
        chat_ids = participant_result.scalars().all()
        
        # If no chats found with both users, return None
        if not chat_ids:
            return None
        
        # Find private chats among the found chat IDs
        chat_query = (
            select(ChatModel)
            .options(selectinload(ChatModel.participants))
            .where(
                and_(
                    ChatModel.id.in_(chat_ids),
                    ChatModel.type == ChatTypeEnum.PRIVATE
                )
            )
        )
        
        # Execute the query to get chat models
        chat_result = await self.session.execute(chat_query)
        chat_model = chat_result.scalars().first()
        
        # Map the model to an entity if found
        if chat_model is not None:
            return self._map_to_domain(chat_model)
        
        return None
    
    async def update(self, chat: Chat) -> t.Optional[Chat]:
        """
        Update a chat in the database.
        
        Args:
            chat: The chat to update
            
        Returns:
            The updated chat if found and updated, None otherwise
        """
        # Check if the chat exists
        existing = await self.get_by_id(chat.id)
        if not existing:
            return None
        
        # Update the chat (but not participants)
        update_stmt = (
            update(ChatModel)
            .where(ChatModel.id == chat.id)
            .values(
                name=chat.name,
                type=self._map_chat_type_to_enum(chat.type),
            )
        )
        
        await self.session.execute(update_stmt)
        await self.session.flush()
        
        # Get the updated chat
        return await self.get_by_id(chat.id)
    
    async def delete(self, chat_id: uuid.UUID) -> bool:
        """
        Delete a chat from the database.
        
        Args:
            chat_id: The UUID of the chat to delete
            
        Returns:
            True if the chat was found and deleted, False otherwise
        """
        # Delete all participants first
        delete_participants = (
            delete(ChatParticipantModel)
            .where(ChatParticipantModel.chat_id == chat_id)
        )
        participant_result = await self.session.execute(delete_participants)
        
        # Delete the chat
        delete_chat = (
            delete(ChatModel)
            .where(ChatModel.id == chat_id)
        )
        chat_result = await self.session.execute(delete_chat)
        
        # Return True if the chat was deleted
        return chat_result.rowcount > 0
    
    async def add_participant(self, chat_id: uuid.UUID, participant: ChatParticipant) -> bool:
        """
        Add a participant to a chat.
        
        Args:
            chat_id: The UUID of the chat
            participant: The participant to add
            
        Returns:
            True if the participant was added, False otherwise
        """
        # Check if the chat exists
        existing = await self.get_by_id(chat_id)
        if not existing:
            return False
        
        # Check if the participant is already in the chat
        for p in existing.participants:
            if p.user_id == participant.user_id:
                return False
        
        # Add the participant
        participant_model = self._map_to_model_participant(chat_id, participant)
        self.session.add(participant_model)
        await self.session.flush()
        
        return True
    
    async def remove_participant(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Remove a participant from a chat.
        
        Args:
            chat_id: The UUID of the chat
            user_id: The UUID of the user to remove
            
        Returns:
            True if the participant was removed, False otherwise
        """
        # Delete the participant
        delete_stmt = (
            delete(ChatParticipantModel)
            .where(
                and_(
                    ChatParticipantModel.chat_id == chat_id,
                    ChatParticipantModel.user_id == user_id
                )
            )
        )
        
        result = await self.session.execute(delete_stmt)
        
        # Return True if the participant was deleted
        return result.rowcount > 0
    
    async def update_participant_role(self, chat_id: uuid.UUID, user_id: uuid.UUID, new_role: str) -> bool:
        """
        Update the role of a chat participant.
        
        Args:
            chat_id: The UUID of the chat
            user_id: The UUID of the user
            new_role: The new role for the participant
            
        Returns:
            True if the participant's role was updated, False otherwise
        """
        # Update the participant's role
        update_stmt = (
            update(ChatParticipantModel)
            .where(
                and_(
                    ChatParticipantModel.chat_id == chat_id,
                    ChatParticipantModel.user_id == user_id
                )
            )
            .values(role=new_role)
        )
        
        result = await self.session.execute(update_stmt)
        
        # Return True if the participant was updated
        return result.rowcount > 0


async def get_chat_repository() -> ChatRepository:
    """
    Factory function to create a chat repository instance.
    
    Returns:
        A chat repository implementation
    """
    session = await get_session()
    return SQLAlchemyChatRepository(session) 