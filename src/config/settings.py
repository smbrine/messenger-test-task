"""
Application settings and configuration.
Using a hierarchical settings structure following clean architecture principles.
Settings are loaded from environment variables with sensible defaults.
"""
import typing as t
import os
from dataclasses import dataclass, field
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

@dataclass
class DatabaseSettings:
    """Database connection settings."""
    url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", 
            "postgresql+asyncpg://postgres:postgres@localhost:5432/messenger"
        )
    )
    echo: bool = field(default_factory=lambda: os.getenv("DB_ECHO", "False").lower() == "true")
    pool_size: int = field(default_factory=lambda: int(os.getenv("DB_POOL_SIZE", "5")))
    max_overflow: int = field(default_factory=lambda: int(os.getenv("DB_MAX_OVERFLOW", "10")))
    pool_timeout: int = field(default_factory=lambda: int(os.getenv("DB_POOL_TIMEOUT", "30")))
    pool_recycle: int = field(default_factory=lambda: int(os.getenv("DB_POOL_RECYCLE", "1800")))


@dataclass
class RedisSettings:
    """Redis connection settings."""
    url: str = field(
        default_factory=lambda: os.getenv(
            "REDIS_URL", 
            "redis://localhost:6379/0"
        )
    )
    username: t.Optional[str] = field(default_factory=lambda: os.getenv("REDIS_USERNAME"))
    password: t.Optional[str] = field(default_factory=lambda: os.getenv("REDIS_PASSWORD"))
    max_connections: int = field(default_factory=lambda: int(os.getenv("REDIS_MAX_CONNECTIONS", "10")))
    decode_responses: bool = field(default_factory=lambda: os.getenv("REDIS_DECODE_RESPONSES", "True").lower() == "true")
    message_queue_key_format: str = field(default_factory=lambda: os.getenv("REDIS_MESSAGE_QUEUE_KEY_FORMAT", "user:{user_id}:message_queue"))
    default_queue_ttl: int = field(default_factory=lambda: int(os.getenv("REDIS_DEFAULT_QUEUE_TTL", "86400")))
    draft_key_format: str = field(default_factory=lambda: os.getenv("REDIS_DRAFT_KEY_FORMAT", "user:{user_id}:chat:{chat_id}:draft"))
    draft_ttl: int = field(default_factory=lambda: int(os.getenv("REDIS_DRAFT_TTL", "86400")))

@dataclass
class APISettings:
    """API server settings."""
    title: str = field(default_factory=lambda: os.getenv("API_TITLE", "Messenger API"))
    description: str = field(
        default_factory=lambda: os.getenv(
            "API_DESCRIPTION", 
            "API for messenger application with real-time chat capabilities"
        )
    )
    version: str = field(default_factory=lambda: os.getenv("API_VERSION", "1.0.0"))
    cors_origins: t.List[str] = field(
        default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(",")
    )
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "False").lower() == "true")
    host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))

@dataclass
class JWTSettings:
    """JWT authentication settings."""
    secret_key: str = field(
        default_factory=lambda: os.getenv(
            "JWT_SECRET_KEY", 
            "supersecretkey"  # Default key for development only
        )
    )
    access_token_expire_minutes: int = field(
        default_factory=lambda: int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    )
    refresh_token_expire_days: int = field(
        default_factory=lambda: int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    )
    algorithm: str = field(
        default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256")
    )


@dataclass
class Settings:
    """Application settings."""
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    redis: RedisSettings = field(default_factory=RedisSettings)
    api: APISettings = field(default_factory=APISettings)
    jwt: JWTSettings = field(default_factory=JWTSettings)
    testing: bool = field(default_factory=lambda: os.getenv("TESTING", "False").lower() == "true")


@lru_cache
def get_settings() -> Settings:
    """
    Get application settings with caching for efficiency.
    Returns a singleton instance of Settings.
    """
    return Settings() 