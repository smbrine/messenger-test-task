"""
Message API endpoints.
"""
import typing as t
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from pydantic import BaseModel, Field

from src.domain.models.user import User
from src.interface.api.dependencies import get_current_user, get_message_service, get_read_status_manager
from src.application.services.message_service import MessageService
from src.application.services.read_status_manager import ReadStatusManager

router = APIRouter()


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


@router.get("/{chat_id}", response_model=t.List[MessageResponse])
async def get_chat_messages(
    chat_id: uuid.UUID = Path(..., description="The ID of the chat to get messages from"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of messages to return"),
    before_id: uuid.UUID = Query(None, description="The ID of the message before which to start the pagination"),
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """
    Get messages for a chat with pagination.
    """
    try:
        messages = await message_service.get_chat_messages(
            chat_id=chat_id, 
            limit=limit, 
            before_id=before_id
        )
        
        # Get unread count to determine read status
        unread_count = await message_service.get_unread_count(chat_id, current_user.id)
        
        # Convert to response models
        response = []
        for message in messages:
            # For now we'll set is_read based on whether the sender is the current user
            # In a more complete implementation, we would check each message's read status
            is_read = message.sender_id == current_user.id
            
            response.append(MessageResponse(
                id=str(message.id),
                chat_id=str(message.chat_id),
                sender_id=str(message.sender_id),
                text=message.text,
                created_at=message.created_at.isoformat() if message.created_at else None,
                updated_at=message.updated_at.isoformat() if message.updated_at else None,
                is_read=is_read
            ))
        
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{chat_id}", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    message_request: MessageRequest,
    chat_id: uuid.UUID = Path(..., description="The ID of the chat to send a message to"),
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """
    Send a message to a chat.
    """
    try:
        message = await message_service.send_message(
            chat_id=chat_id,
            sender_id=current_user.id,
            text=message_request.text,
            idempotency_key=message_request.idempotency_key
        )
        
        return MessageResponse(
            id=str(message.id),
            chat_id=str(message.chat_id),
            sender_id=str(message.sender_id),
            text=message.text,
            created_at=message.created_at.isoformat() if message.created_at else None,
            updated_at=message.updated_at.isoformat() if message.updated_at else None,
            is_read=True  # Message is read by sender
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{message_id}/read", response_model=ReadStatusResponse)
async def mark_message_as_read(
    message_id: uuid.UUID = Path(..., description="The ID of the message to mark as read"),
    current_user: User = Depends(get_current_user),
    read_status_manager: ReadStatusManager = Depends(get_read_status_manager),
    message_service: MessageService = Depends(get_message_service)
):
    """
    Mark a single message as read by current user.
    """
    try:
        # First get the message to determine its chat ID
        message = await message_service.message_repository.get_by_id(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Mark the message as read
        success = await read_status_manager.mark_as_read(
            message_id=message_id,
            user_id=current_user.id,
            chat_id=message.chat_id
        )
        
        return ReadStatusResponse(marked_count=1 if success else 0, success=success)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/read/batch", response_model=ReadStatusResponse)
async def mark_messages_as_read(
    read_request: ReadMessageRequest,
    current_user: User = Depends(get_current_user),
    read_status_manager: ReadStatusManager = Depends(get_read_status_manager),
    message_service: MessageService = Depends(get_message_service)
):
    """
    Mark multiple messages as read by current user.
    """
    # Convert string IDs to UUIDs
    try:
        message_ids = [uuid.UUID(msg_id) for msg_id in read_request.message_ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID format")
        
    if not message_ids:
        return ReadStatusResponse(marked_count=0, success=True)
    
    try:
        # Get the first message to determine its chat_id
        first_message = await message_service.message_repository.get_by_id(message_ids[0])
        if not first_message:
            raise HTTPException(status_code=404, detail="Message not found")
            
        chat_id = first_message.chat_id
        
        # Mark messages as read
        count = await read_status_manager.mark_multiple_as_read(
            message_ids=message_ids,
            user_id=current_user.id,
            chat_id=chat_id
        )
        
        return ReadStatusResponse(marked_count=count, success=count > 0)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{chat_id}/read_all", response_model=ReadStatusResponse)
async def mark_all_chat_messages_as_read(
    chat_id: uuid.UUID = Path(..., description="The ID of the chat"),
    current_user: User = Depends(get_current_user),
    read_status_manager: ReadStatusManager = Depends(get_read_status_manager)
):
    """
    Mark all messages in a chat as read by current user.
    """
    try:
        count = await read_status_manager.mark_all_as_read(
            chat_id=chat_id,
            user_id=current_user.id
        )
        
        return ReadStatusResponse(marked_count=count, success=count > 0)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{chat_id}/unread_count", response_model=dict)
async def get_unread_message_count(
    chat_id: uuid.UUID = Path(..., description="The ID of the chat"),
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """
    Get count of unread messages in a chat for the current user.
    """
    try:
        count = await message_service.get_unread_count(
            chat_id=chat_id,
            user_id=current_user.id
        )
        
        return {"unread_count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) 