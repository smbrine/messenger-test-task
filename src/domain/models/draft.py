from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel, Field, validator


class MessageDraft(BaseModel):
    """Message draft domain model."""
    user_id: UUID
    chat_id: UUID
    text: str
    updated_at: datetime = None
    
    def __init__(self, **data):
        # Ensure updated_at is set with proper timezone
        if 'updated_at' not in data or data['updated_at'] is None:
            data['updated_at'] = datetime.now(timezone.utc)
        
        super().__init__(**data)
    
    class Config:
        """Pydantic model configuration."""
        frozen = False  # Allow mutable drafts 