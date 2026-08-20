"""
Unit tests for the summarization endpoint and service.
"""
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture
def client():
    """Create a test client with overridden dependencies."""
    # We need to patch the dependencies before importing the app
    with patch('apps.api.database.SessionLocal') as mock_session_local, \
         patch('apps.api.routers.summaries.LlamaService') as mock_llama_service_class:

        # Set up the mock session
        mock_session = MagicMock(spec=Session)
        mock_model_profile = MagicMock()
        mock_model_profile.id = 1
        mock_model_profile.model_name = "llama-2-7b-chat"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_model_profile

        mock_session_local.return_value = mock_session

        # Set up the mock LlamaService instance
        mock_instance = MagicMock()
        mock_instance.generate_summary = AsyncMock()
        mock_instance.close = AsyncMock()
        mock_llama_service_class.return_value = mock_instance

        # Now import the app
        from apps.api.main import app
        from apps.api.database import get_db

        # Override the get_db dependency
        app.dependency_overrides[get_db] = lambda: mock_session

        with TestClient(app) as test_client:
            yield test_client, mock_instance

        # Clean up
        from apps.api.main import app
        app.dependency_overrides.clear()


def test_create_summary_structured(client):
    """Test creating a structured summary."""
    test_client, mock_llama_service = client
    # Setup mock to return a structured summary
    mock_llama_service.generate_summary.return_value = {
        "summary": "This is a structured summary.",
        "model_used": "llama-2-7b-chat",
        "summary_type": "structured"
    }

    # Make request
    response = test_client.post(
        "/v1/summaries",
        json={
            "content": "This is a test document for summarization.",
            "summary_type": "structured"
        }
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "This is a structured summary."
    assert data["model_used"] == "llama-2-7b-chat"
    assert data["metadata"]["summary_type"] == "structured"
    assert "id" in data
    assert "created_at" in data

    # Verify the service was called correctly
    mock_llama_service.generate_summary.assert_awaited_once_with(
        content="This is a test document for summarization.",
        summary_type="structured",
        model_id=1,  # This is the ID of the mocked active model
        temperature=0.3
    )
    mock_llama_service.close.assert_awaited_once()


def test_create_summary_quick(client):
    """Test creating a quick summary."""
    test_client, mock_llama_service = client
    # Setup mock to return a quick summary and print arguments
    def side_effect(*args, **kwargs):
        print(f"Arguments: args={args}, kwargs={kwargs}")
        return {
            "summary": "This is a quick summary.",
            "model_used": "llama-2-7b-chat",
            "summary_type": "quick"
        }
    mock_llama_service.generate_summary.side_effect = side_effect

    # Make request
    response = test_client.post(
        "/v1/summaries",
        json={
            "content": "This is a test document for summarization.",
            "summary_type": "quick",
            "model": "llama-2-7b-chat",
            "temperature": 0.5
        }
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "This is a quick summary."
    assert data["model_used"] == "llama-2-7b-chat"
    assert data["metadata"]["summary_type"] == "quick"

    # Verify the service was called correctly
    mock_llama_service.generate_summary.assert_awaited_once_with(
        content="This is a test document for summarization.",
        summary_type="quick",
        model_id=1,  # This is the ID of the mocked model
        temperature=0.5
    )


def test_create_summary_long_document(client):
    """Test creating a long-document summary."""
    test_client, mock_llama_service = client
    # Setup mock to return a long-document summary
    mock_llama_service.generate_summary.return_value = {
        "summary": "This is a long document summary.",
        "model_used": "llama-2-7b-chat",
        "summary_type": "long-document"
    }

    # Make request with long content
    long_content = "This is a very long document. " * 100  # Make it long enough to trigger long-document handling

    response = test_client.post(
        "/v1/summaries",
        json={
            "content": long_content,
            "summary_type": "long-document"
        }
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "This is a long document summary."
    assert data["model_used"] == "llama-2-7b-chat"
    assert data["metadata"]["summary_type"] == "long-document"

    # Verify the service was called correctly
    mock_llama_service.generate_summary.assert_awaited_once_with(
        content=long_content,
        summary_type="long-document",
        model_id=1,  # This is the ID of the mocked active model
        temperature=0.3
    )


def test_create_summary_handles_service_error(client):
    """Test that the endpoint handles errors from the llama service."""
    test_client, mock_llama_service = client
    # Setup mock to return an error
    mock_llama_service.generate_summary.return_value = {
        "error": "Failed to generate summary"
    }

    # Make request
    response = test_client.post(
        "/v1/summaries",
        json={
            "content": "This is a test document.",
            "summary_type": "structured"
        }
    )

    # Assertions
    assert response.status_code == 500
    assert "Failed to generate summary" in response.json()["detail"]


def test_create_summary_handles_exception(client):
    """Test that the endpoint handles exceptions from the llama service."""
    test_client, mock_llama_service = client
    # Setup mock to raise an exception
    mock_llama_service.generate_summary.side_effect = Exception("Service error")

    # Make request
    response = test_client.post(
        "/v1/summaries",
        json={
            "content": "This is a test document.",
            "summary_type": "structured"
        }
    )

    # Assertions
    assert response.status_code == 500
    assert "Service error" in response.json()["detail"]


def test_create_summary_invalid_summary_type(client):
    """Test that invalid summary types default to structured."""
    test_client, mock_llama_service = client
    # Setup mock to return a structured summary (since invalid type defaults to structured)
    mock_llama_service.generate_summary.return_value = {
        "summary": "This is a summary.",
        "model_used": "llama-2-7b-chat",
        "summary_type": "structured"
    }

    # Make request with invalid summary type
    response = test_client.post(
        "/v1/summaries",
        json={
            "content": "This is a test document.",
            "summary_type": "invalid-type"
        }
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"]["summary_type"] == "structured"  # Should have defaulted to structured

    # Verify the service was called with structured (the default)
    mock_llama_service.generate_summary.assert_awaited_once_with(
        content="This is a test document.",
        summary_type="structured",
        model_id=1,  # This is the ID of the mocked active model
        temperature=0.3
    )