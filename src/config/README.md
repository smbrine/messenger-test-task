# Configuration Module

This module centralizes all application configuration settings according to clean architecture principles. The configuration is structured hierarchically to separate concerns and improve maintainability.

## Usage

```python
from src.config.settings import get_settings

# Get application settings
settings = get_settings()

# Access specific settings
db_url = settings.db.url
redis_url = settings.redis.url
app_title = settings.api.title
```

## Environment Variables

The application can be configured using environment variables. Below is a list of available environment variables and their default values:

### Application Environment
- `ENVIRONMENT`: Application environment (default: "development")
- `TESTING`: Flag to indicate testing mode (default: "False")
- `DEBUG`: Enable debug mode (default: "False")

### Database Configuration
- `DATABASE_URL`: Database connection URL (default: "postgresql+asyncpg://postgres:postgres@localhost:5432/messenger")
- `DB_ECHO`: Enable SQL query logging (default: "False")
- `DB_POOL_SIZE`: Database connection pool size (default: "5")
- `DB_MAX_OVERFLOW`: Maximum number of connections to overflow (default: "10")
- `DB_POOL_TIMEOUT`: Connection timeout in seconds (default: "30")
- `DB_POOL_RECYCLE`: Connection recycle time in seconds (default: "1800")

### Redis Configuration
- `REDIS_URL`: Redis connection URL (default: "redis://localhost:6379/0")
- `REDIS_USERNAME`: Redis username for authentication (default: None)
- `REDIS_PASSWORD`: Redis password for authentication (default: None)
- `REDIS_MAX_CONNECTIONS`: Maximum number of Redis connections (default: "10")
- `REDIS_DECODE_RESPONSES`: Automatically decode Redis responses (default: "True")

### API Configuration
- `API_TITLE`: API title (default: "Messenger API")
- `API_DESCRIPTION`: API description (default: "API for messenger application with real-time chat capabilities")
- `API_VERSION`: API version (default: "1.0.0")
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins (default: "*")

## Clean Architecture

This configuration module follows clean architecture principles by:

1. **Separation of Concerns**: Configuration is separated from business logic
2. **Dependency Rule**: Core business logic does not depend on configuration details
3. **Testability**: Configuration can be easily mocked for testing
4. **Single Source of Truth**: All configuration is centralized in one module

## Testing

During testing, environment variables are automatically set and cleared to ensure isolation between tests. The `get_settings()` function is cached to improve performance, and the cache is cleared between tests to ensure fresh settings. 