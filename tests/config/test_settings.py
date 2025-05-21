"""
Tests for the configuration settings module.
"""
import os
import pytest

from src.config.settings import get_settings, Settings


def test_settings_default_values():
    """Test that settings have correct default values."""
    # Save original values if they exist
    original_env = os.environ.get("ENVIRONMENT")
    original_testing = os.environ.get("TESTING")
    
    try:
        # Set environment to None to test default values
        if "ENVIRONMENT" in os.environ:
            os.environ.pop("ENVIRONMENT")
        if "TESTING" in os.environ:
            os.environ.pop("TESTING")
        
        # Clear cache to ensure we get a fresh instance
        get_settings.cache_clear()
        
        # Get settings
        settings = get_settings()
        
        # Check default values
        assert settings.environment == "development"
        assert settings.testing is False
        assert settings.db.url == "postgresql+asyncpg://postgres:postgres@localhost:5432/messenger"
        assert settings.redis.url == "redis://localhost:6379/0"
        assert settings.api.title == "Messenger API"
        assert settings.api.cors_origins == ["*"]
    finally:
        # Restore original values if they existed
        if original_env is not None:
            os.environ["ENVIRONMENT"] = original_env
        elif "ENVIRONMENT" in os.environ:
            os.environ.pop("ENVIRONMENT")
            
        if original_testing is not None:
            os.environ["TESTING"] = original_testing
        elif "TESTING" in os.environ:
            os.environ.pop("TESTING")
        
        # Clear cache again
        get_settings.cache_clear()


def test_settings_from_environment():
    """Test that settings are loaded from environment variables."""
    # Save original values
    original_values = {}
    for key in ["ENVIRONMENT", "TESTING", "DATABASE_URL", "REDIS_URL", "API_TITLE", "CORS_ORIGINS"]:
        if key in os.environ:
            original_values[key] = os.environ[key]
    
    try:
        # Set environment variables
        os.environ["ENVIRONMENT"] = "production"
        os.environ["TESTING"] = "True"
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@testdb:5432/testdb"
        os.environ["REDIS_URL"] = "redis://testredis:6379/1"
        os.environ["API_TITLE"] = "Test API"
        os.environ["CORS_ORIGINS"] = "https://example.com,https://test.com"
        
        # Clear cache to ensure we get a fresh instance
        get_settings.cache_clear()
        
        # Get settings
        settings = get_settings()
        
        # Check values from environment
        assert settings.environment == "production"
        assert settings.testing is True
        assert settings.db.url == "postgresql+asyncpg://user:pass@testdb:5432/testdb"
        assert settings.redis.url == "redis://testredis:6379/1"
        assert settings.api.title == "Test API"
        assert settings.api.cors_origins == ["https://example.com", "https://test.com"]
    finally:
        # Restore original values
        for key in ["ENVIRONMENT", "TESTING", "DATABASE_URL", "REDIS_URL", "API_TITLE", "CORS_ORIGINS"]:
            if key in original_values:
                os.environ[key] = original_values[key]
            elif key in os.environ:
                os.environ.pop(key)
        
        # Clear cache again
        get_settings.cache_clear()


def test_settings_caching():
    """Test that settings are cached properly."""
    # Save original value if it exists
    original_title = os.environ.get("API_TITLE")
    
    try:
        # Get settings twice
        settings1 = get_settings()
        settings2 = get_settings()
        
        # Check that we got the same instance
        assert settings1 is settings2
        
        # Change an environment variable
        os.environ["API_TITLE"] = "Changed Title"
        
        # Get settings again without clearing cache
        settings3 = get_settings()
        
        # Should still be the same instance with original values
        assert settings3 is settings1
        assert settings3.api.title == settings1.api.title
        
        # Clear cache
        get_settings.cache_clear()
        
        # Get settings again
        settings4 = get_settings()
        
        # Should be a new instance with updated values
        assert settings4 is not settings1
        assert settings4.api.title == "Changed Title"
    finally:
        # Restore original value
        if original_title is not None:
            os.environ["API_TITLE"] = original_title
        elif "API_TITLE" in os.environ:
            os.environ.pop("API_TITLE")
        
        # Clear cache
        get_settings.cache_clear() 