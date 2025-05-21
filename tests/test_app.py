"""
Tests for the FastAPI application.
"""
import typing as t
import warnings
import pytest
from fastapi.testclient import TestClient

from src.interface.main import create_app


@pytest.fixture
def client():
    """
    Create a test client for the FastAPI application.
    """
    # Filter out the specific deprecation warning from httpx
    warnings.filterwarnings(
        "ignore", 
        message="The 'app' shortcut is now deprecated.*", 
        category=DeprecationWarning
    )
    
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_health_endpoint(client):
    """
    Test the health check endpoint.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok" 