# Technical Specification for Senior Backend Developer Position at WinDI

## Project Description
The product being developed is a messenger with message exchange capabilities and the ability to create group chats, similar to Telegram.

The candidate must demonstrate strong knowledge in:
- Python (FastAPI, asyncio);
- SQLAlchemy (ORM, asynchronous operations);
- WebSockets (real-time interaction implementation);
- Docker and Docker Compose (service deployment in containers);
- Preventing message duplication during concurrent sending.

---

## Test Task

### Task
Develop a mini-application that implements chat functionality with message sending, storage in a database, and group chat creation.

---

## Functional Requirements

### 1. Chat (WebSocket)
- Implement user connection via WebSocket.
- Real-time exchange of text messages between users.
- Ability to create group chats.
- Messages must be stored in PostgreSQL.
- Each message should include:
  - Message ID  
  - Chat ID  
  - Sender ID  
  - Text  
  - Timestamp  
  - Read status
- Implement "read" status processing (the sender is notified when the message is read by the recipient or all group members).
- Prevent message duplication during concurrent sending.

### 2. Message History
- Implement a REST endpoint to retrieve message history by chat ID:
  - Method: `GET /history/{chat_id}`
  - Query parameters: `chat_id` — chat ID (required), `limit` and `offset` for pagination (optional).
  - Messages must be sorted by timestamp (ascending).

---

## Technical Requirements

### 1. Backend:
- Use FastAPI to implement REST API and WebSocket.
- Asynchronous operations using asyncio.
- PostgreSQL as the main database.
- SQLAlchemy (ORM usage, asynchronous queries).
- Containerization (Docker, Docker Compose).
- Automatic documentation (Swagger / OpenAPI).

### 2. Database Structure:
- `users` (id, name, email, password)
- `chats` (id, name, type: private/group)
- `groups` (id, name, creator, participants list)
- `messages` (id, chat_id, sender_id, text, timestamp, read)

---

## Expected Result

1. A GitHub repository containing:
   - The project's source code.
   - A `README.md` file describing:
     - How to run the project via Docker;
     - API request examples;
     - Command to create test data.

2. A working application that runs via Docker.

3. Compliance with all stated requirements.

---

## Evaluation Criteria

### 1. Architectural Design:
- Separation of logic into layers (controllers, services, repositories);
- Use of Dependency Injection.

### 2. Code Quality:
- Clean, readable code;
- No anti-patterns.

### 3. Performance:
- Efficient SQL queries;
- WebSocket performance optimization.

### 4. Requirement Compliance:
- Correct functionality of chat and group chats;
- Proper error handling and logging;
- Prevention of message duplication during concurrent sending.

---

## Additional Task (Optional, but a Plus)
- Implement the ability to connect from multiple devices simultaneously (like Telegram Web).
- Add authorization using JWT (OAuth 2.0 / FastAPI Security).
- Implement unit tests using Pytest.
