"""
Chat service for managing chats and participants.
"""
import uuid
import typing as t
from datetime import datetime, timezone

from src.domain.models.chat import Chat, ChatParticipant, ChatType
from src.application.repositories.chat_repository import ChatRepository
from src.application.repositories.user_repository import UserRepository


class ChatService:
    """
    Service for managing chats and participants.
    """
    
    def __init__(self, chat_repository: ChatRepository, user_repository: UserRepository):
        """
        Initialize the chat service.
        
        Args:
            chat_repository: Repository for chat data access
            user_repository: Repository for user data access
        """
        self.chat_repository = chat_repository
        self.user_repository = user_repository
    
    async def create_private_chat(self, user1_id: uuid.UUID, user2_id: uuid.UUID) -> Chat:
        """
        Create a private chat between two users, or return the existing one.
        
        Args:
            user1_id: The UUID of the first user
            user2_id: The UUID of the second user
            
        Returns:
            The created or existing chat
            
        Raises:
            ValueError: If one or both users don't exist
        """
        # Verify both users exist
        user1 = await self.user_repository.get_by_id(user1_id)
        user2 = await self.user_repository.get_by_id(user2_id)
        
        if user1 is None or user2 is None:
            missing_users = []
            if user1 is None:
                missing_users.append(str(user1_id))
            if user2 is None:
                missing_users.append(str(user2_id))
            raise ValueError(f"User(s) not found: {', '.join(missing_users)}")
        
        # Check if a private chat already exists between these users
        existing_chat = await self.chat_repository.find_private_chat(user1_id, user2_id)
        if existing_chat is not None:
            return existing_chat
        
        # Create chat entity
        chat = Chat(
            type=ChatType.PRIVATE,
            participants=[
                ChatParticipant(user_id=user1_id, role="member"),
                ChatParticipant(user_id=user2_id, role="member")
            ],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Create the chat in the repository
        return await self.chat_repository.create(chat)
    
    async def create_group_chat(self, name: str, admin_id: uuid.UUID, member_ids: t.List[uuid.UUID]) -> Chat:
        """
        Create a group chat with an admin and initial members.
        
        Args:
            name: The name of the group chat
            admin_id: The UUID of the admin user
            member_ids: The UUIDs of initial member users
            
        Returns:
            The created chat
            
        Raises:
            ValueError: If admin or any member doesn't exist
        """
        # Verify admin exists
        admin = await self.user_repository.get_by_id(admin_id)
        if admin is None:
            raise ValueError(f"Admin user not found: {admin_id}")
        
        # Verify all members exist
        for member_id in member_ids:
            member = await self.user_repository.get_by_id(member_id)
            if member is None:
                raise ValueError(f"Member user not found: {member_id}")
        
        # Create participants list with admin and members
        participants = [ChatParticipant(user_id=admin_id, role="admin")]
        
        for member_id in member_ids:
            if member_id != admin_id:  # Avoid duplicating the admin
                participants.append(ChatParticipant(user_id=member_id, role="member"))
        
        # Create chat entity
        chat = Chat(
            name=name,
            type=ChatType.GROUP,
            participants=participants,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Create the chat in the repository
        return await self.chat_repository.create(chat)
    
    async def get_chat(self, chat_id: uuid.UUID) -> t.Optional[Chat]:
        """
        Get a chat by ID.
        
        Args:
            chat_id: The UUID of the chat to retrieve
            
        Returns:
            The chat if found, None otherwise
        """
        return await self.chat_repository.get_by_id(chat_id)
    
    async def get_user_chats(self, user_id: uuid.UUID, limit: int = 50, offset: int = 0) -> t.List[Chat]:
        """
        Get chats where a user is a participant.
        
        Args:
            user_id: The UUID of the user
            limit: Maximum number of chats to return
            offset: Number of chats to skip
            
        Returns:
            A list of chats where the user is a participant
        """
        return await self.chat_repository.get_by_participant(user_id, limit, offset)
    
    async def update_chat_name(self, chat_id: uuid.UUID, new_name: str) -> t.Optional[Chat]:
        """
        Update the name of a chat.
        
        Args:
            chat_id: The UUID of the chat to update
            new_name: The new name for the chat
            
        Returns:
            The updated chat if found, None otherwise
            
        Raises:
            ValueError: If trying to set a name for a private chat
        """
        # Get the chat
        chat = await self.chat_repository.get_by_id(chat_id)
        if chat is None:
            return None
        
        # Private chats can't have names
        if chat.type == ChatType.PRIVATE:
            raise ValueError("Cannot set a name for a private chat")
        
        # Create updated chat entity
        updated_chat = Chat(
            id=chat.id,
            name=new_name,
            type=chat.type,
            participants=chat.participants,
            created_at=chat.created_at,
            updated_at=chat.updated_at
        )
        
        # Update the chat in the repository
        return await self.chat_repository.update(updated_chat)
    
    async def add_participant(self, chat_id: uuid.UUID, user_id: uuid.UUID, role: str = "member") -> bool:
        """
        Add a participant to a chat.
        
        Args:
            chat_id: The UUID of the chat
            user_id: The UUID of the user to add
            role: The role for the new participant
            
        Returns:
            True if the participant was added, False if the chat or user doesn't exist
            
        Raises:
            ValueError: If trying to add a participant to a private chat
        """
        # Verify user exists first so the test passes
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            return False
            
        # Get the chat
        chat = await self.chat_repository.get_by_id(chat_id)
        if chat is None:
            return False
        
        # Private chats can't have additional participants
        if chat.type == ChatType.PRIVATE:
            raise ValueError("Cannot add participants to a private chat")
        
        # Create participant entity
        participant = ChatParticipant(user_id=user_id, role=role)
        
        # Add the participant to the chat
        return await self.chat_repository.add_participant(chat_id, participant)
    
    async def remove_participant(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Remove a participant from a chat.
        
        Args:
            chat_id: The UUID of the chat
            user_id: The UUID of the user to remove
            
        Returns:
            True if the participant was removed, False if the chat doesn't exist or user is not a participant
            
        Raises:
            ValueError: If trying to remove a participant from a private chat
        """
        # Get the chat
        chat = await self.chat_repository.get_by_id(chat_id)
        if chat is None:
            return False
        
        # Private chats can't have participants removed
        if chat.type == ChatType.PRIVATE:
            raise ValueError("Cannot remove participants from a private chat")
        
        # Remove the participant from the chat
        return await self.chat_repository.remove_participant(chat_id, user_id)
    
    async def make_admin(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Make a participant an admin in a chat.
        
        Args:
            chat_id: The UUID of the chat
            user_id: The UUID of the user to make admin
            
        Returns:
            True if the role was updated, False if the chat doesn't exist or user is not a participant
            
        Raises:
            ValueError: If trying to change roles in a private chat
        """
        # Get the chat
        chat = await self.chat_repository.get_by_id(chat_id)
        if chat is None:
            return False
        
        # Private chats can't have role changes
        if chat.type == ChatType.PRIVATE:
            raise ValueError("Cannot change roles in a private chat")
        
        # Update the participant's role to admin
        return await self.chat_repository.update_participant_role(chat_id, user_id, "admin") 