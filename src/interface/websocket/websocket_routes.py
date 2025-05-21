"""
WebSocket routes for the messenger application.
"""
import json
import logging
import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from starlette.websockets import WebSocketState

from src.config.settings import get_settings
from src.domain.models.user import User
from src.domain.models.chat import Chat
from src.domain.models.message import Message
from src.application.services.draft_service import DraftService, get_draft_service
from src.interface.websocket.draft_websocket_handler import DraftWebSocketHandler, get_draft_websocket_handler
from src.interface.websocket.auth import authenticate_websocket
from src.interface.websocket.websocket_manager import manager, ConnectionManager
from src.application.repositories.chat_repository import ChatRepository
from src.infrastructure.repositories.chat_repository import get_chat_repository
from src.application.repositories.message_repository import MessageRepository
from src.infrastructure.repositories.message_repository import get_message_repository
from src.application.services.message_broadcaster import MessageBroadcaster
from src.infrastructure.redis.message_broadcaster import get_message_broadcaster

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat.
    
    Authentication is performed using a JWT token provided in query parameter or cookie.
    """
    # Authenticate the connection
    user_id = await authenticate_websocket(websocket)
    
    if not user_id:
        # Authentication failed - the connection should be closed by the auth function
        return
    
    # Accept the connection and get a connection ID
    connection_id = await manager.connect(websocket, user_id)
    
    # Get the message broadcaster
    broadcaster = await get_message_broadcaster()
    
    # Get the chat repository
    chat_repository = await get_chat_repository()
    
    # Get the message repository
    message_repository = await get_message_repository()
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "system",
            "message": "Connected to WebSocket server",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        # Fetch and send any queued messages for this user
        queued_messages = await broadcaster.get_queued_messages(user_id)
        if queued_messages:
            await websocket.send_json({
                "type": "queued_messages",
                "messages": queued_messages,
                "count": len(queued_messages),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        
        # Main message loop
        while True:
            # Wait for message from client
            data = await websocket.receive_text()
            
            try:
                # Parse message
                message_data = json.loads(data)
                
                # Basic message validation
                if not isinstance(message_data, dict):
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid message format",
                    })
                    continue
                
                # Process message based on type
                message_type = message_data.get("type", "")
                
                if message_type == "chat":
                    # Process chat message
                    chat_id_str = message_data.get("chat_id")
                    content = message_data.get("content", "")
                    
                    if not chat_id_str or not content:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Missing required fields",
                        })
                        continue
                    
                    try:
                        chat_id = UUID(chat_id_str)
                    except ValueError:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid chat_id format",
                        })
                        continue
                    
                    # Get chat details to check if user is a member
                    chat = await chat_repository.get_by_id(chat_id)
                    if not chat:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Chat not found",
                        })
                        continue
                    
                    # Check if user is a participant in the chat
                    is_participant = user_id in [participant.user_id for participant in chat.participants]
                    if not is_participant:
                        await websocket.send_json({
                            "type": "error",
                            "message": "You are not a member of this chat",
                        })
                        continue
                    
                    # Generate a message ID
                    message_id = uuid.uuid4()
                    
                    # Create the message object for broadcasting
                    message_broadcast = {
                        "type": "chat",
                        "message_id": str(message_id),
                        "chat_id": chat_id_str,
                        "sender_id": str(user_id),
                        "content": content,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "read": False
                    }
                    
                    # Create the domain message object to save to repository
                    message = Message(
                        id=message_id,
                        chat_id=chat_id,
                        sender_id=user_id,
                        text=content,
                        idempotency_key=f"ws_{message_id}"  # Use message_id as idempotency key for websocket messages
                    )
                    
                    # Save message to repository
                    await message_repository.create(message)
                    
                    # Get all user IDs in this chat for broadcasting
                    user_ids = [participant.user_id for participant in chat.participants]
                    
                    # Broadcast the message to all users in the chat
                    await broadcaster.broadcast_to_chat(
                        chat_id, 
                        message_broadcast,
                        user_ids,
                        exclude_user_id=user_id  # Don't send to the sender
                    )
                    
                    # Send confirmation to the sender
                    await websocket.send_json({
                        **message_broadcast,
                        "status": "sent"
                    })
                    
                elif message_type == "typing":
                    # Process typing notification
                    chat_id_str = message_data.get("chat_id")
                    is_typing = message_data.get("is_typing", False)
                    
                    if not chat_id_str:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Missing chat_id",
                        })
                        continue
                    
                    try:
                        chat_id = UUID(chat_id_str)
                    except ValueError:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid chat_id format",
                        })
                        continue
                    
                    # Get chat details to check if user is a member
                    chat = await chat_repository.get_by_id(chat_id)
                    if not chat:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Chat not found",
                        })
                        continue
                    
                    # Check if user is a participant in the chat
                    is_participant = user_id in [participant.user_id for participant in chat.participants]
                    if not is_participant:
                        await websocket.send_json({
                            "type": "error",
                            "message": "You are not a member of this chat",
                        })
                        continue
                    
                    # Get all user IDs in this chat for broadcasting
                    user_ids = [participant.user_id for participant in chat.participants]
                    
                    # Create typing notification
                    typing_notification = {
                        "type": "typing",
                        "chat_id": chat_id_str,
                        "user_id": str(user_id),
                        "is_typing": is_typing,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    
                    # Broadcast typing status to all other users in the chat
                    await broadcaster.broadcast_to_chat(
                        chat_id,
                        typing_notification,
                        user_ids,
                        exclude_user_id=user_id  # Don't send to the sender
                    )
                    
                    # Send confirmation to the sender
                    await websocket.send_json({
                        **typing_notification,
                        "status": "sent"
                    })
                    
                elif message_type == "read":
                    # Process read receipt
                    message_id_str = message_data.get("message_id")
                    
                    if not message_id_str:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Missing message_id",
                        })
                        continue
                    
                    try:
                        message_id = UUID(message_id_str)
                    except ValueError:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid message_id format",
                        })
                        continue
                        
                    # Update read status in the repository
                    updated = await message_repository.update_read_status(
                        message_id=message_id,
                        user_id=user_id,
                        read=True
                    )
                    
                    if not updated:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Failed to mark message as read",
                        })
                        continue
                    
                    # Create read receipt
                    read_receipt = {
                        "type": "read",
                        "message_id": message_id_str,
                        "user_id": str(user_id),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    
                    # Send confirmation to the sender
                    await websocket.send_json({
                        **read_receipt,
                        "status": "received"
                    })
                    
                else:
                    # Unknown message type
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                    })
                
            except json.JSONDecodeError:
                # Invalid JSON
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })
            
    except WebSocketDisconnect:
        # Client disconnected
        await manager.disconnect(connection_id) 

@router.websocket("/ws/drafts/{chat_id}")
async def websocket_drafts_endpoint(
    websocket: WebSocket,
    chat_id: UUID,
    user_id: UUID = Depends(authenticate_websocket),
    draft_handler = Depends(get_draft_websocket_handler),
):
    """
    WebSocket endpoint for message draft synchronization.
    
    This endpoint allows real-time synchronization of message drafts across
    multiple tabs or devices for the same user.
    """
    connection_id = None
    try:
        # Handle the connection and get a connection ID
        connection_id = await draft_handler.handle_connection(websocket, chat_id, user_id)
        if not connection_id:
            return
        
        # Main message loop
        while True:
            # Wait for message from client
            data = await websocket.receive_json()
            
            # Process the message
            await draft_handler.process_message(websocket, user_id, chat_id, data)
            
    except WebSocketDisconnect:
        # Client disconnected normally
        logger.info(f"WebSocket client disconnected: {connection_id}")
    finally:
        # Ensure connection is properly closed
        if connection_id:
            await manager.disconnect(connection_id) 