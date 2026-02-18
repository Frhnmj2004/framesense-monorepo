"""Smoke test for health endpoint."""
import pytest
from fastapi.testclient import TestClient

from api.routes import router


def test_health_endpoint():
    """Test health check endpoint."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
