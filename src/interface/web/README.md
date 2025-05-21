# Web Interface for Messenger Application

This module provides a simple web interface for the messenger application. It's designed to be a frontend to the API endpoints.

## Features

- **Authentication**: Login and registration functionality
- **Dashboard**: Overview of recent chats and users
- **Users List**: Browse and search users
- **Chats Interface**: View and interact with chats, send messages

## Architecture

- Uses Jinja2 templates for server-side rendering
- Bootstrap 5 for UI components and styling
- Custom CSS for styling
- JavaScript for frontend interactivity
- JWT authentication with token storage in localStorage

## Pages

1. **Login Page** (`/web/login`)
   - Email and password login form
   - Link to registration page

2. **Registration Page** (`/web/register`)
   - Registration form with name, username, email, and password
   - Link back to login page

3. **Dashboard** (`/web/dashboard`)
   - Overview showing recent chats and users
   - Quick action buttons

4. **Users List** (`/web/users`)
   - List of users with search and pagination
   - Ability to start chats with users

5. **Chats** (`/web/chats`)
   - Chat sidebar with list of conversations
   - Chat window with message history and input field
   - Ability to create new private or group chats

## Notes

- This is a placeholder implementation that will be replaced with real functionality once WebSockets are fully implemented
- Authentication uses the existing API endpoints via fetch requests
- Design is responsive and mobile-friendly

## Future Improvements

1. WebSocket integration for real-time messaging
2. Real user list from API
3. Real chats list from API
4. Message history loading from API
5. Message read status indicators 