"""
Tests for the Chat domain model.
"""
import uuid
import pytest
from pydantic import ValidationError

from src.domain.models.chat import Chat, ChatParticipant, ChatType


class TestChatModel:
    """Test cases for the Chat domain model."""

    def test_chat_creation_valid_private(self):
        """Test creating a valid private chat."""
        chat = Chat(
            id=uuid.uuid4(),
            type=ChatType.PRIVATE,
            participants=[
                ChatParticipant(
                    user_id=uuid.uuid4(),
                    role="member"
                ),
                ChatParticipant(
                    user_id=uuid.uuid4(),
                    role="member"
                )
            ]
        )
        assert chat.type == ChatType.PRIVATE
        assert len(chat.participants) == 2
        assert chat.name is None
        assert isinstance(chat.id, uuid.UUID)

    def test_chat_creation_valid_group(self):
        """Test creating a valid group chat."""
        chat = Chat(
            id=uuid.uuid4(),
            name="Test Group",
            type=ChatType.GROUP,
            participants=[
                ChatParticipant(
                    user_id=uuid.uuid4(),
                    role="admin"
                ),
                ChatParticipant(
                    user_id=uuid.uuid4(),
                    role="member"
                )
            ]
        )
        assert chat.type == ChatType.GROUP
        assert chat.name == "Test Group"
        assert len(chat.participants) == 2
        assert isinstance(chat.id, uuid.UUID)

    def test_chat_creation_with_default_id(self):
        """Test creating a chat with a default UUID."""
        chat = Chat(
            type=ChatType.PRIVATE,
            participants=[
                ChatParticipant(
                    user_id=uuid.uuid4(),
                    role="member"
                ),
                ChatParticipant(
                    user_id=uuid.uuid4(),
                    role="member"
                )
            ]
        )
        assert isinstance(chat.id, uuid.UUID)

    def test_chat_creation_missing_name_for_group_chat(self):
        """Test that creating a group chat without a name raises ValidationError."""
        with pytest.raises(ValidationError):
            Chat(
                type=ChatType.GROUP,
                participants=[
                    ChatParticipant(
                        user_id=uuid.uuid4(),
                        role="admin"
                    )
                ]
            )

    def test_private_chat_with_too_many_participants(self):
        """Test that creating a private chat with more than 2 participants raises ValidationError."""
        with pytest.raises(ValidationError):
            Chat(
                type=ChatType.PRIVATE,
                participants=[
                    ChatParticipant(
                        user_id=uuid.uuid4(),
                        role="member"
                    ),
                    ChatParticipant(
                        user_id=uuid.uuid4(),
                        role="member"
                    ),
                    ChatParticipant(
                        user_id=uuid.uuid4(),
                        role="member"
                    )
                ]
            )

    def test_chat_without_participants(self):
        """Test that creating a chat without participants raises ValidationError."""
        with pytest.raises(ValidationError):
            Chat(
                type=ChatType.PRIVATE,
                participants=[]
            )

    def test_chat_equality(self):
        """Test chat equality comparison."""
        chat_id = uuid.uuid4()
        user_id1 = uuid.uuid4()
        user_id2 = uuid.uuid4()
        
        chat1 = Chat(
            id=chat_id,
            type=ChatType.PRIVATE,
            participants=[
                ChatParticipant(
                    user_id=user_id1,
                    role="member"
                ),
                ChatParticipant(
                    user_id=user_id2,
                    role="member"
                )
            ]
        )
        
        chat2 = Chat(
            id=chat_id,
            type=ChatType.PRIVATE,
            participants=[
                ChatParticipant(
                    user_id=user_id1,
                    role="member"
                ),
                ChatParticipant(
                    user_id=user_id2,
                    role="member"
                )
            ]
        )
        
        chat3 = Chat(
            id=uuid.uuid4(),
            type=ChatType.PRIVATE,
            participants=[
                ChatParticipant(
                    user_id=user_id1,
                    role="member"
                ),
                ChatParticipant(
                    user_id=user_id2,
                    role="member"
                )
            ]
        )
        
        assert chat1 == chat2
        assert chat1 != chat3
        assert chat1 != "not_a_chat"


class TestChatParticipantModel:
    """Test cases for the ChatParticipant domain model."""

    def test_participant_creation_valid(self):
        """Test creating a valid chat participant."""
        user_id = uuid.uuid4()
        participant = ChatParticipant(
            user_id=user_id,
            role="admin"
        )
        assert participant.user_id == user_id
        assert participant.role == "admin"

    def test_participant_invalid_role(self):
        """Test that creating a participant with invalid role raises ValidationError."""
        with pytest.raises(ValidationError):
            ChatParticipant(
                user_id=uuid.uuid4(),
                role="invalid_role"
            )

    def test_participant_equality(self):
        """Test participant equality comparison."""
        user_id = uuid.uuid4()
        participant1 = ChatParticipant(
            user_id=user_id,
            role="admin"
        )
        
        participant2 = ChatParticipant(
            user_id=user_id,
            role="admin"
        )
        
        participant3 = ChatParticipant(
            user_id=uuid.uuid4(),
            role="admin"
        )
        
        assert participant1 == participant2
        assert participant1 != participant3
        assert participant1 != "not_a_participant" 