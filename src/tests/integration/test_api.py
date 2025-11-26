"""
Integration tests for the Cheese App API
Tests the full API endpoints with FastAPI TestClient
Based on L18, Slide 11-12 - Integration tests
"""

import pytest
from fastapi.testclient import TestClient
from rag.main import app

client = TestClient(app)


class TestAPIEndpoints:
    """Integration tests for API endpoints"""

    def test_root_endpoint(self):
        """Test the root endpoint returns welcome message"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Formula One Penalty" in data["message"]

    def test_root_returns_json(self):
        """Test that root returns JSON content type"""
        response = client.get("/")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_invalid_route_returns_404(self):
        """Test that invalid routes return 404"""
        response = client.get("/this-route-does-not-exist")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test that POST to GET-only endpoint returns 405"""
        response = client.post("/")
        assert response.status_code == 405

    def test_method_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"
        assert "healthy" in response.text

class TestCORS:
    """Tests for CORS configuration"""

    def test_cors_enabled(self):
        """Test that CORS headers are present"""
        response = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_allows_all_origins(self):
        """Test that CORS allows all origins"""
        response = client.get("/", headers={"Origin": "http://example.com"})
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "*"


@pytest.mark.asyncio
async def test_api_health_check():
    """Test that the API is healthy and responding"""
    response = client.get("/")
    assert response.status_code == 200
    # API should respond quickly
    assert (
        response.elapsed.total_seconds() < 1 if hasattr(response, "elapsed") else True
    )
