"""
Middleware for handling JWT tokens from cookies or headers.
"""
import typing as t

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class TokenMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract JWT tokens from cookies or Authorization header.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process each request to extract JWT token from cookie or Authorization header.
        
        If a token is found in a cookie named 'token', add it to the request headers
        as a Bearer token for authentication.
        """
        # Check for token in cookies
        token = request.cookies.get("token")
        
        # If token exists in cookies, add it to authorization header
        if token:
            # Modify request scope to include authorization header
            request.scope["headers"].append(
                (b"authorization", f"Bearer {token}".encode())
            )
        
        # Continue with the request
        response = await call_next(request)
        return response 