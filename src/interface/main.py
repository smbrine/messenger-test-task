"""
FastAPI application factory and entry point.
"""
import typing as t
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from src.interface.web.middleware import TokenMiddleware

from src.interface.api.routers import user_router, chat_router, message_router, auth_router
from src.interface.websocket import websocket_routes
from src.interface.web.router import router as web_router
from src.config.settings import get_settings


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.api.title,
        description=settings.api.description,
        version=settings.api.version,
        debug=settings.api.debug,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add token middleware to handle cookie authentication
    app.add_middleware(TokenMiddleware)

    @app.get("/")
    async def root() -> dict[str, str]:
        return RedirectResponse(url="/web")

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    # Add API routers
    app.include_router(user_router, prefix="/api", tags=["Users"])
    app.include_router(chat_router, prefix="/api", tags=["Chats"])
    app.include_router(message_router, prefix="/api", tags=["Messages"])
    app.include_router(auth_router, prefix="/api", tags=["Auth"])
    
    # Add WebSocket routes
    app.include_router(websocket_routes.router, tags=["WebSocket"])
    
    # Add Web UI routes
    app.include_router(web_router, prefix="/web", tags=["Web UI"])
    
    # Mount static files
    static_dir = Path(__file__).parent / "web" / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


app = create_app() 