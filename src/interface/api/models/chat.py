"""
Chat API models.
"""
import typing as t
from pydantic import BaseModel


class ParticipantResponse(BaseModel):
    """Participant response model."""
    user_id: str
    role: str


class ChatResponse(BaseModel):
    """Chat response model."""
    id: str
    name: t.Optional[str] = None
    type: str
    participants: t.List[ParticipantResponse]


class PrivateChatRequest(BaseModel):
    """Request model for creating a private chat."""
    user_id: str


class GroupChatRequest(BaseModel):
    """Request model for creating a group chat."""
    name: str
    member_ids: t.List[str]


class AddParticipantRequest(BaseModel):
    """Request model for adding a participant to a chat."""
    user_id: str


class SuccessResponse(BaseModel):
    """Response model for success/failure operations."""
    success: bool
