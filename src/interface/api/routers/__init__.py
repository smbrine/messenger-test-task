"""
API router imports.
"""
from src.interface.api.routers.user_router import router as user_router
from src.interface.api.routers.chat_router import router as chat_router
from src.interface.api.routers.message_router import router as message_router
from src.interface.api.routers.auth_router import router as auth_router

__all__ = ["user_router", "chat_router", "message_router", "auth_router"]
