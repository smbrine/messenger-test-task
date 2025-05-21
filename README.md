# Messenger Application

A real-time messenger application with features similar to Telegram, built with FastAPI, PostgreSQL 17, SQLAlchemy, WebSockets, and Redis.

## Features

- User management with authentication
- Real-time chat using WebSockets
- Private and group chats
- Message history
- Multiple device support with synchronization
- Message read status
- Idempotent message delivery

## Tech Stack

- **Backend**: FastAPI, Python 3.11+
- **Database**: PostgreSQL 17
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic
- **Caching/Messaging**: Redis
- **Connection**: WebSockets
- **Containerization**: Docker, Docker Compose
- **Testing**: pytest, testcontainers

## Project Structure

The project follows Clean Architecture principles with the following layers:

- **Domain**: Core business entities and logic
- **Application**: Use cases and business rules
- **Infrastructure**: External services and frameworks integration
- **Interface**: API controllers and WebSocket handlers

## Development Setup

### Prerequisites

- Python 3.11+
- Poetry
- Docker and Docker Compose

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/messenger-app.git
   cd messenger-app
   ```

2. Install dependencies with Poetry:
   ```
   poetry install
   ```

3. Start the Docker containers:
   ```
   docker-compose up -d
   ```

4. Apply migrations:
   ```
   poetry run alembic upgrade head
   ```

5. Run the application:
   ```
   poetry run uvicorn src.interface.main:app --reload
   ```

### Running Tests

```
poetry run pytest
```

## API Documentation

API documentation is available at `/docs` when the application is running.

## WebSocket API

Connect to the WebSocket endpoint at `/ws` with a valid authentication token.

Example:
```
ws://localhost:8000/ws?token=your-auth-token
```

## License

This project is licensed under the MIT License. 