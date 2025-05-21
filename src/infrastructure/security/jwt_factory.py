"""
Factory function for JWT service.
"""
from src.application.security.jwt_interface import JWTService
from src.infrastructure.security.jwt import JoseJWTService


def get_jwt_service() -> JWTService:
    """
    Get a JWT service implementation.
    
    Returns:
        A JWT service implementation
    """
    return JoseJWTService() 