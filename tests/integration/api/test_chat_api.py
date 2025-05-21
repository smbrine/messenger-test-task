"""
Tests for the chat API endpoints.
"""
import uuid
import pytest
from httpx import AsyncClient

from src.domain.models.chat import ChatType


async def test_create_private_chat(test_client: AsyncClient, test_user_token, test_user2_token, test_user, test_user2):
    """Test creating a private chat."""
    # Create a private chat directly with user IDs
    user_id = test_user.id
    user2_id = test_user2.id
    
    response = await test_client.post(
        "/api/chats/private",
        json={"user_id": str(user2_id)},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    # Print response content if not 200
    if response.status_code != 200:
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == ChatType.PRIVATE.value
    assert len(data["participants"]) == 2
    assert any(p["user_id"] == str(user_id) for p in data["participants"])
    assert any(p["user_id"] == str(user2_id) for p in data["participants"])


async def test_create_group_chat(test_client: AsyncClient, test_user_token, test_user2_token, test_user, test_user2):
    """Test creating a group chat."""
    # Create a group chat directly with user IDs
    user_id = test_user.id
    user2_id = test_user2.id
    
    response = await test_client.post(
        "/api/chats/group",
        json={
            "name": "Test Group",
            "member_ids": [str(user2_id)]
        },
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == ChatType.GROUP.value
    assert data["name"] == "Test Group"
    assert len(data["participants"]) == 2
    
    # Verify that the creator is an admin
    admin_participants = [p for p in data["participants"] if p["role"] == "admin"]
    assert len(admin_participants) == 1
    assert admin_participants[0]["user_id"] == str(user_id)
    
    # Verify that the second user is a member
    member_participants = [p for p in data["participants"] if p["user_id"] == str(user2_id)]
    assert len(member_participants) == 1
    assert member_participants[0]["role"] == "member"


async def test_get_chat(test_client: AsyncClient, test_user_token, test_user2_token, test_user, test_user2):
    """Test getting a chat by ID."""
    # First create a chat
    user_id = test_user.id
    user2_id = test_user2.id
    
    # Create a private chat
    create_response = await test_client.post(
        "/api/chats/private",
        json={"user_id": str(user2_id)},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert create_response.status_code == 200
    chat = create_response.json()
    
    # Get the chat by ID
    response = await test_client.get(
        f"/api/chats/{chat['id']}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == chat["id"]
    assert data["type"] == ChatType.PRIVATE.value
    assert len(data["participants"]) == 2


async def test_get_user_chats(test_client: AsyncClient, test_user_token, test_user2_token, test_user, test_user2):
    """Test getting all chats for a user."""
    # First create a chat
    user_id = test_user.id
    user2_id = test_user2.id
    
    # Create a private chat
    create_response = await test_client.post(
        "/api/chats/private",
        json={"user_id": str(user2_id)},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert create_response.status_code == 200
    
    # Create a group chat
    group_response = await test_client.post(
        "/api/chats/group",
        json={
            "name": "Test Group",
            "member_ids": [str(user2_id)]
        },
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert group_response.status_code == 200
    
    # Get the user's chats
    response = await test_client.get(
        "/api/chats",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2  # Could be more if there are other chats in the test database


async def test_add_participant(test_client: AsyncClient, test_user_token, test_user2_token, test_user3_token, test_user, test_user2, test_user3):
    """Test adding a participant to a group chat."""
    # Get user info to extract IDs
    user_id = test_user.id
    user2_id = test_user2.id
    user3_id = test_user3.id
    
    # Create a group chat with user and user2
    create_response = await test_client.post(
        "/api/chats/group",
        json={
            "name": "Test Group",
            "member_ids": [str(user2_id)]
        },
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert create_response.status_code == 200
    chat = create_response.json()
    
    # Add user3 to the group chat
    response = await test_client.post(
        f"/api/chats/{chat['id']}/participants",
        json={"user_id": str(user3_id)},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # Verify user3 is now in the chat
    get_response = await test_client.get(
        f"/api/chats/{chat['id']}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert get_response.status_code == 200
    updated_chat = get_response.json()
    assert len(updated_chat["participants"]) == 3
    assert any(p["user_id"] == str(user3_id) for p in updated_chat["participants"])


async def test_remove_participant(test_client: AsyncClient, test_user_token, test_user2_token, test_user3_token, test_user, test_user2, test_user3):
    """Test removing a participant from a group chat."""
    # Get user info to extract IDs
    user_id = test_user.id
    user2_id = test_user2.id
    user3_id = test_user3.id
    
    # Create a group chat with all three users
    create_response = await test_client.post(
        "/api/chats/group",
        json={
            "name": "Test Group",
            "member_ids": [str(user2_id), str(user3_id)]
        },
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert create_response.status_code == 200
    chat = create_response.json()
    
    # Remove user3 from the group chat
    response = await test_client.delete(
        f"/api/chats/{chat['id']}/participants/{user3_id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # Verify user3 is no longer in the chat
    get_response = await test_client.get(
        f"/api/chats/{chat['id']}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert get_response.status_code == 200
    updated_chat = get_response.json()
    assert len(updated_chat["participants"]) == 2
    assert not any(p["user_id"] == str(user3_id) for p in updated_chat["participants"])


async def test_make_admin(test_client: AsyncClient, test_user_token, test_user2_token, test_user, test_user2):
    """Test making a participant an admin in a group chat."""
    # Get user info to extract IDs
    user_id = test_user.id
    user2_id = test_user2.id
    
    # Create a group chat
    create_response = await test_client.post(
        "/api/chats/group",
        json={
            "name": "Test Group",
            "member_ids": [str(user2_id)]
        },
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert create_response.status_code == 200
    chat = create_response.json()
    
    # Make user2 an admin
    response = await test_client.post(
        f"/api/chats/{chat['id']}/admins",
        json={"user_id": str(user2_id)},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # Verify user2 is now an admin
    get_response = await test_client.get(
        f"/api/chats/{chat['id']}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert get_response.status_code == 200
    updated_chat = get_response.json()
    user2_participants = [p for p in updated_chat["participants"] if p["user_id"] == str(user2_id)]
    assert len(user2_participants) == 1
    assert user2_participants[0]["role"] == "admin" 