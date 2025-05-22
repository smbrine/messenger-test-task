from pydantic import BaseModel, Field
import typing as t


class MessageRequest(BaseModel):
    """Message request model for sending messages."""
    text: str = Field(..., min_length=1, max_length=4000)
    idempotency_key: str = Field(..., min_length=3, max_length=64)


class MessageResponse(BaseModel):
    """Message response model."""
    id: str
    chat_id: str
    sender_id: str
    text: str
    created_at: str
    updated_at: str
    is_read: bool = False


class ReadMessageRequest(BaseModel):
    """Request model for marking messages as read."""
    message_ids: t.List[str]


class ReadStatusResponse(BaseModel):
    """Response model for read status operations."""
    marked_count: int
    success: bool