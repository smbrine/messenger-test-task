"""
API router for chat endpoints.
"""
import uuid
import typing as t
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from src.application.services.chat_service import ChatService
from src.interface.api.dependencies import get_chat_service, get_current_user
from src.domain.models.user import User
from src.domain.models.chat import Chat, ChatType
from src.interface.api.models.chat import ChatResponse, PrivateChatRequest, GroupChatRequest, AddParticipantRequest, SuccessResponse, ParticipantResponse


router = APIRouter()


def chat_to_response(chat: Chat) -> ChatResponse:
    """Convert a chat domain model to a response model."""
    return ChatResponse(
        id=str(chat.id),
        name=chat.name,
        type=chat.type.value,
        participants=[
            ParticipantResponse(
                user_id=str(p.user_id),
                role=p.role
            )
            for p in chat.participants
        ]
    )


@router.post("/private", response_model=ChatResponse)
async def create_private_chat(
    request: PrivateChatRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
) -> ChatResponse:
    """
    Create a private chat with another user.
    """
    try:
        other_user_id = uuid.UUID(request.user_id)
        chat = await chat_service.create_private_chat(current_user.id, other_user_id)
        return chat_to_response(chat)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/group", response_model=ChatResponse)
async def create_group_chat(
    request: GroupChatRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
) -> ChatResponse:
    """
    Create a group chat with the current user as admin.
    """
    try:
        member_ids = [uuid.UUID(member_id) for member_id in request.member_ids]
        chat = await chat_service.create_group_chat(
            name=request.name,
            admin_id=current_user.id,
            member_ids=member_ids
        )
        return chat_to_response(chat)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=t.List[ChatResponse])
async def get_user_chats(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
) -> t.List[ChatResponse]:
    """
    Get all chats where the current user is a participant.
    """
    chats = await chat_service.get_user_chats(current_user.id, limit, offset)
    return [chat_to_response(chat) for chat in chats]


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
) -> ChatResponse:
    """
    Get a specific chat by ID.
    """
    chat = await chat_service.get_chat(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Check if the current user is a participant
    if not any(p.user_id == current_user.id for p in chat.participants):
        raise HTTPException(status_code=403, detail="Not a participant in this chat")
    
    return chat_to_response(chat)


@router.post("/{chat_id}/participants", response_model=SuccessResponse)
async def add_participant(
    chat_id: uuid.UUID = Path(...),
    request: AddParticipantRequest = None,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
) -> SuccessResponse:
    """
    Add a participant to a chat.
    """
    # Check if the current user is a participant and has permission
    chat = await chat_service.get_chat(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    current_participant = next((p for p in chat.participants if p.user_id == current_user.id), None)
    if current_participant is None:
        raise HTTPException(status_code=403, detail="Not a participant in this chat")
    
    # For group chats, only admins can add members
    if chat.type == ChatType.GROUP and current_participant.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can add participants")
    
    try:
        user_id = uuid.UUID(request.user_id)
        success = await chat_service.add_participant(chat_id, user_id)
        return SuccessResponse(success=success)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{chat_id}/participants/{user_id}", response_model=SuccessResponse)
async def remove_participant(
    chat_id: uuid.UUID = Path(...),
    user_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
) -> SuccessResponse:
    """
    Remove a participant from a chat.
    """
    # Check if the current user is a participant and has permission
    chat = await chat_service.get_chat(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    current_participant = next((p for p in chat.participants if p.user_id == current_user.id), None)
    if current_participant is None:
        raise HTTPException(status_code=403, detail="Not a participant in this chat")
    
    # For group chats, only admins can remove members
    if chat.type == ChatType.GROUP and current_participant.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can remove participants")
    
    try:
        success = await chat_service.remove_participant(chat_id, user_id)
        return SuccessResponse(success=success)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{chat_id}/admins", response_model=SuccessResponse)
async def make_admin(
    chat_id: uuid.UUID = Path(...),
    request: AddParticipantRequest = None,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
) -> SuccessResponse:
    """
    Make a participant an admin in a chat.
    """
    # Check if the current user is a participant and has permission
    chat = await chat_service.get_chat(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    current_participant = next((p for p in chat.participants if p.user_id == current_user.id), None)
    if current_participant is None:
        raise HTTPException(status_code=403, detail="Not a participant in this chat")
    
    # Only admins can make others admins
    if current_participant.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can make others admins")
    
    try:
        user_id = uuid.UUID(request.user_id)
        success = await chat_service.make_admin(chat_id, user_id)
        return SuccessResponse(success=success)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) 