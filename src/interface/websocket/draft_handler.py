"""
WebSocket handler for draft synchronization.
"""
import json
import logging
import typing as t
from uuid import UUID
from datetime import datetime, timezone

from fastapi import WebSocket, status, Depends
from starlette.websockets import WebSocketDisconnect

from src.domain.models.draft import MessageDraft
from src.domain.exceptions.repository_exceptions import RepositoryError
from src.application.services.draft_service import DraftService, get_draft_service
from src.application.repositories.chat_repository import ChatRepository, get_chat_repository
from src.interface.websocket.websocket_manager import ConnectionManager, manager

# Configure logger
logger = logging.getLogger(__name__)


class DraftWebSocketHandler:
    """Handler for draft WebSocket connections and messages."""
    
    def __init__(
        self,
        draft_service: DraftService,
        chat_repository: ChatRepository,
        connection_manager: ConnectionManager
    ):
        """
        Initialize the draft WebSocket handler.
        
        Args:
            draft_service: Service for managing drafts
            chat_repository: Repository for accessing chat data
            connection_manager: Manager for WebSocket connections
        """
        self.draft_service = draft_service
        self.chat_repository = chat_repository
        self.connection_manager = connection_manager
    
    async def validate_chat_access(self, chat_id: UUID, user_id: UUID) -> bool:
        """
        Validate that the user has access to the specified chat.
        
        Args:
            chat_id: The UUID of the chat
            user_id: The UUID of the user
            
        Returns:
            True if the user has access, False otherwise
        """
        try:
            # Get chat details
            chat = await self.chat_repository.get_by_id(chat_id)
            if not chat:
                logger.warning(f"Chat {chat_id} not found for user {user_id}")
                return False
            
            # Check if user is a participant
            is_participant = any(
                participant.user_id == user_id 
                for participant in chat.participants
            )
            
            if not is_participant:
                logger.warning(f"User {user_id} is not a member of chat {chat_id}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating chat access: {e}")
            return False
    
    async def handle_connection(
        self, 
        websocket: WebSocket, 
        chat_id: UUID, 
        user_id: UUID
    ) -> t.Optional[str]:
        """
        Handle a new WebSocket connection for draft synchronization.
        
        Args:
            websocket: The WebSocket connection
            chat_id: The UUID of the chat
            user_id: The UUID of the user
            
        Returns:
            The connection ID if successfully connected, None otherwise
        """
        # Validate access to the chat
        has_access = await self.validate_chat_access(chat_id, user_id)
        if not has_access:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, 
                reason="Not authorized to access this chat"
            )
            return None
        
        # Accept the connection
        connection_id = await self.connection_manager.connect(websocket, user_id)
        
        try:
            # Send initial draft if it exists
            draft = await self.draft_service.get_user_draft(user_id, chat_id)
            if draft:
                await websocket.send_json({
                    "type": "draft_init",
                    "chat_id": str(chat_id),
                    "text": draft.text,
                    "updated_at": draft.updated_at.isoformat()
                })
            
            return connection_id
        except Exception as e:
            logger.error(f"Error during draft connection initialization: {e}")
            await self.connection_manager.disconnect(connection_id)
            await websocket.close(
                code=status.WS_1011_INTERNAL_ERROR, 
                reason="Error initializing connection"
            )
            return None
    
    async def handle_draft_update(
        self, 
        user_id: UUID, 
        chat_id: UUID, 
        text: str
    ) -> bool:
        """
        Handle a draft update message.
        
        Args:
            user_id: The UUID of the user
            chat_id: The UUID of the chat
            text: The draft text
            
        Returns:
            True if the update was successful, False otherwise
        """
        try:
            draft = await self.draft_service.save_user_draft(user_id, chat_id, text)
            return draft is not None
        except RepositoryError as e:
            logger.error(f"Repository error saving draft: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving draft: {e}")
            return False
    
    async def handle_draft_delete(
        self, 
        user_id: UUID, 
        chat_id: UUID
    ) -> bool:
        """
        Handle a draft deletion message.
        
        Args:
            user_id: The UUID of the user
            chat_id: The UUID of the chat
            
        Returns:
            True if the deletion was successful, False otherwise
        """
        try:
            return await self.draft_service.delete_user_draft(user_id, chat_id)
        except RepositoryError as e:
            logger.error(f"Repository error deleting draft: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting draft: {e}")
            return False
    
    async def process_message(
        self, 
        websocket: WebSocket, 
        user_id: UUID, 
        chat_id: UUID, 
        data: dict
    ) -> None:
        """
        Process an incoming WebSocket message.
        
        Args:
            websocket: The WebSocket connection
            user_id: The UUID of the user
            chat_id: The UUID of the chat
            data: The message data
        """
        message_type = data.get("type", "")
        
        if message_type == "draft_update":
            # Handle draft update
            text = data.get("text", "")
            success = await self.handle_draft_update(user_id, chat_id, text)
            
            if not success:
                await websocket.send_json({
                    "type": "error",
                    "message": "Failed to save draft",
                })
        
        elif message_type == "draft_delete":
            # Handle draft deletion
            success = await self.handle_draft_delete(user_id, chat_id)
            
            if not success:
                await websocket.send_json({
                    "type": "error",
                    "message": "Failed to delete draft",
                })
        
        else:
            # Unknown message type
            await websocket.send_json({
                "type": "error",
                "message": f"Unknown message type: {message_type}",
            })
    
    async def handle_connection_error(
        self, 
        connection_id: t.Optional[str], 
        error: Exception
    ) -> None:
        """
        Handle a WebSocket connection error.
        
        Args:
            connection_id: The connection ID, if available
            error: The exception that occurred
        """
        logger.error(f"Draft WebSocket error: {error}")
        
        if connection_id:
            try:
                await self.connection_manager.disconnect(connection_id)
            except Exception as e:
                logger.error(f"Error disconnecting connection: {e}")


def get_draft_websocket_handler(
    draft_service: DraftService = Depends(get_draft_service),
    chat_repository: ChatRepository = Depends(get_chat_repository),
    connection_manager: ConnectionManager = Depends(lambda: manager),
) -> DraftWebSocketHandler:
    """
    Get a draft WebSocket handler instance.
    
    Args:
        draft_service: Service for managing drafts
        chat_repository: Repository for accessing chat data
        connection_manager: Manager for WebSocket connections
        
    Returns:
        A draft WebSocket handler instance
    """
    return DraftWebSocketHandler(
        draft_service=draft_service,
        chat_repository=chat_repository,
        connection_manager=connection_manager
    ) 