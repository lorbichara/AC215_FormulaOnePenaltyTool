"""
Integration tests for FastAPI endpoints
Tests the actual API endpoints with HTTP requests
"""

import pytest
import requests
import time


# Base URL for the API (assumes API is running)
API_BASE_URL = "http://localhost:9000"

def is_api_running():
    """Check if API is accessible"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


@pytest.mark.skipif(not is_api_running(), reason="API not running at localhost:9000")
class TestAPIEndpoints:
    """Integration tests for API endpoints"""

    def test_root_endpoint(self):
        """Test the root endpoint returns welcome message"""
        response = requests.get(f"{API_BASE_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Formula One Penalty" in data["message"]

    def test_health_check(self):
        """Test health check endpoint"""
        response = requests.get(f"{API_BASE_URL}/health")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"
        assert "healthy" in response.text

    def test_chunk(self):
        """Test chunking endpoint"""
        response = requests.get(f"{API_BASE_URL}/chunk?limit=1")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"
        assert "Chunking for decision files done" in response.text
        assert "Chunking for regulation files done" in response.text

    def test_embed(self):
        """Test generate embeddings endpoint"""
        response = requests.get(f"{API_BASE_URL}/embed?limit=1")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"
        assert "Embedding for decision files done" in response.text
        assert "Embedding for regulation files done" in response.text

    def test_store(self):
        """Test generate embeddings endpoint"""
        response = requests.get(f"{API_BASE_URL}/store?testing=True")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"
        assert "Storing of embeddings of decision files in chromadb done" in response.text
        assert "Storing of embeddings of regulation files in chromadb done" in response.text

    def test_query(self):
        """Test llm query endpoint"""
        response = requests.get(f"{API_BASE_URL}/query?prompt=Is the Car 30 infringement in 2024 Abu Dhabi Grand Prix a fair penalty")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"
