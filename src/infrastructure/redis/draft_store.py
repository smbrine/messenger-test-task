"""
Redis-based draft store for saving and retrieving message drafts.
"""
import json
import typing as t
from uuid import UUID
from datetime import datetime, timezone

from src.config.settings import get_settings
from src.domain.models.draft import MessageDraft
from src.infrastructure.redis.redis import set_key, get_key, delete_key

async def save_draft(draft: MessageDraft) -> bool:
    """
    Save a user's message draft for a specific chat.
    
    Args:
        draft: The message draft to save
        
    Returns:
        True if successful, False otherwise
    """
    settings = get_settings()
    key = settings.redis.draft_key_format.format(
        user_id=str(draft.user_id),
        chat_id=str(draft.chat_id)
    )
    
    # Update the timestamp
    draft.updated_at = datetime.now(timezone.utc)
    
    # Convert to JSON-serializable dict
    draft_data = {
        "text": draft.text,
        "updated_at": draft.updated_at.isoformat()
    }
    
    return await set_key(key, json.dumps(draft_data), expiry=settings.redis.draft_ttl)


async def get_draft(user_id: UUID, chat_id: UUID) -> t.Optional[MessageDraft]:
    """
    Get a user's message draft for a specific chat.
    
    Args:
        user_id: The UUID of the user
        chat_id: The UUID of the chat
        
    Returns:
        The message draft or None if not found
    """
    settings = get_settings()
    key = settings.redis.draft_key_format.format(
        user_id=str(user_id),
        chat_id=str(chat_id)
    )
    
    draft_json = await get_key(key)
    if not draft_json:
        return None
    
    try:
        draft_data = json.loads(draft_json)
        
        return MessageDraft(
            user_id=user_id,
            chat_id=chat_id,
            text=draft_data["text"],
            updated_at=datetime.fromisoformat(draft_data["updated_at"])
        )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        # Log the error but continue execution
        print(f"Error parsing draft data: {e}")
        return None


async def delete_draft(user_id: UUID, chat_id: UUID) -> int:
    """
    Delete a user's message draft for a specific chat.
    
    Args:
        user_id: The UUID of the user
        chat_id: The UUID of the chat
        
    Returns:
        1 if the draft was deleted, 0 if it didn't exist
    """
    settings = get_settings()
    key = settings.redis.draft_key_format.format(
        user_id=str(user_id),
        chat_id=str(chat_id)
    )
    
    return await delete_key(key) 