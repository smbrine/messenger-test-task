"""
Web interface router for messenger application.
"""
import typing as t
from pathlib import Path
import uuid

from fastapi import APIRouter, Request, Depends, HTTPException, status, Path as PathParam
from fastapi.security.utils import get_authorization_scheme_param
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from src.interface.api.dependencies import get_current_user, get_chat_service, get_message_service
from src.interface.api.models.user import UserResponse
from src.interface.web.helpers import generate_avatar_initials, truncate_text
from src.application.services.chat_service import ChatService
from src.application.services.message_service import MessageService

# Create router
router = APIRouter()

# Setup templates
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

async def get_current_user_or_redirect(
    request: Request,
    current_user: t.Optional[UserResponse] = Depends(get_current_user),
) -> t.Optional[UserResponse]:
    """
    Get the current user or redirect to login page if not authenticated.
    Used for web UI routes that require authentication.
    """
    # Try to get Authorization from cookies if not in headers
    if not current_user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)
    return current_user

# Homepage - redirects to login if not authenticated
@router.get("/", response_class=HTMLResponse)
async def index(request: Request, current_user: t.Optional[UserResponse] = Depends(get_current_user)):
    if current_user:
        return RedirectResponse(url="/web/chats", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

# Login page
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html", {"request": request, "page_title": "Login"}
    )

# Register page
@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        "register.html", {"request": request, "page_title": "Register"}
    )

# Dashboard page - requires authentication
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: UserResponse = Depends(get_current_user_or_redirect)):
    user_data = {
        "name": current_user.name,
        "username": current_user.username,
        "id": str(current_user.id),
        "initials": generate_avatar_initials(current_user.name)
    }
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "page_title": "Dashboard", 
            "user": user_data,
            "helper_functions": {
                "generate_avatar_initials": generate_avatar_initials,
                "truncate_text": truncate_text
            },
            "api_endpoints": {
                "users": "/api/users",
                "chats": "/api/chats",
                "messages": "/api/messages"
            }
        }
    )

# Users page - requires authentication
@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, current_user: UserResponse = Depends(get_current_user_or_redirect)):
    user_data = {
        "name": current_user.name,
        "username": current_user.username,
        "id": str(current_user.id),
        "initials": generate_avatar_initials(current_user.name)
    }
    return templates.TemplateResponse(
        "users.html", 
        {
            "request": request, 
            "page_title": "Users", 
            "user": user_data,
            "helper_functions": {
                "generate_avatar_initials": generate_avatar_initials,
                "truncate_text": truncate_text
            },
            "api_endpoints": {
                "users": "/api/users",
                "chats": "/api/chats",
            }
        }
    )

# Chats page - requires authentication
@router.get("/chats", response_class=HTMLResponse)
async def chats_page(
    request: Request, 
    current_user: UserResponse = Depends(get_current_user_or_redirect), 
    chat_id: t.Optional[str] = None
):
    user_data = {
        "name": current_user.name,
        "username": current_user.username,
        "id": str(current_user.id),
        "initials": generate_avatar_initials(current_user.name)
    }
    
    # Handle chat_id from the query string and ensure it's a string
    query_chat_id = request.query_params.get('chat_id')
    if query_chat_id:
        try:
            # Verify it's a valid UUID and then use the original string
            uuid.UUID(query_chat_id)
            chat_id = query_chat_id
        except ValueError:
            # Invalid UUID - ignore it
            pass
    
    return templates.TemplateResponse(
        "chats.html", 
        {
            "request": request, 
            "page_title": "Chats", 
            "user": user_data,
            "helper_functions": {
                "generate_avatar_initials": generate_avatar_initials,
                "truncate_text": truncate_text
            },
            "api_endpoints": {
                "users": "/api/users",
                "chats": "/api/chats",
                "messages": "/api/messages",
                "chat_participants": "/api/chats/{chat_id}/participants",
            },
            "chat_id": chat_id
        }
    )

# Chat detail page - redirects to chats page
@router.get("/chats/{chat_id}", response_class=HTMLResponse)
async def chat_detail(
    request: Request, 
    chat_id: uuid.UUID = PathParam(..., description="The ID of the chat to view"),
    current_user: UserResponse = Depends(get_current_user_or_redirect)
):
    # Convert UUID to string and redirect to the main chats page with the chat_id query parameter
    return RedirectResponse(url=f"/web/chats?chat_id={chat_id}", status_code=status.HTTP_302_FOUND) 