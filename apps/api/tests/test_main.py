"""
Test the main FastAPI application and core API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Offline LLM Assistant"
    assert data["version"] == "1.0.0"
    assert data["status"] == "running"
    assert data["network_mode"] == "air-gapped"


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["service"] == "offline-llm-assistant"
    assert "components" in data


def test_get_models():
    """Test the models endpoint."""
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "model_name" in data[0]


def test_chat_completion():
    """Test the chat completion endpoint."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "llama-2-7b-chat",
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "stream": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["object"] == "chat.completion"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert len(data["choices"][0]["message"]["content"]) > 0


def test_create_summary():
    """Test the summary creation endpoint."""
    response = client.post(
        "/v1/summaries",
        json={
            "content": "This is an air-gapped system designed for secure document intelligence.",
            "summary_type": "quick"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "summary" in data
    assert "model_used" in data
    assert data["summary_type"] == "quick"


def test_rewrite_text():
    """Test the rewriting and grammar endpoint."""
    response = client.post(
        "/v1/rewrite",
        json={
            "text": "the system are working good and do not has bug",
            "mode": "grammar"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "rewritten_text" in data
    assert data["mode"] == "grammar"


def test_collections_crud():
    """Test collection creation and listing."""
    # List collections
    res = client.get("/v1/collections/")
    assert res.status_code == 200

    # Create collection
    create_res = client.post(
        "/v1/collections/",
        json={
            "name": "Test Engineering Docs",
            "description": "Technical specifications",
            "classification": "internal",
            "access_policy": "authenticated"
        }
    )
    assert create_res.status_code == 201
    col_data = create_res.json()
    assert col_data["name"] == "Test Engineering Docs"
    col_id = col_data["id"]

    # Get single collection
    get_res = client.get(f"/v1/collections/{col_id}")
    assert get_res.status_code == 200


def test_admin_stats_and_config():
    """Test admin stats and configuration endpoints."""
    stats_res = client.get("/v1/admin/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "users" in stats
    assert "documents" in stats
    assert "collections" in stats

    config_res = client.get("/v1/admin/config")
    assert config_res.status_code == 200
    config = config_res.json()
    assert config["network_mode"] == "air-gapped"
    assert config["features"]["chat_completions"] is True