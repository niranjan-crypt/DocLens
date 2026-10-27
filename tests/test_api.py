"""
Tests for FastAPI REST endpoints using TestClient.
"""
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["database_connected"] is True


def test_documents_endpoint():
    response = client.get("/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_feedback_endpoint():
    payload = {"query_log_id": 1, "rating": 1}
    response = client.post("/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
