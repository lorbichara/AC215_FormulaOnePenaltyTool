"""
Integration tests for FastAPI endpoints
Tests the actual API endpoints with HTTP requests
"""

import pytest
import requests

# Base URL for the API (assumes API is running)
API_BASE_URL = "http://localhost:9000"


def is_api_running():
    """Check if API is accessible"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except Exception as e:
        print(f"An error occurred: {e}")
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

    def test_query(self):
        """Test llm query endpoint"""
        response = requests.get(
            f"{API_BASE_URL}/query?prompt=Is the Car 30 infringement in 2024 Abu Dhabi Grand Prix a fair penalty"
        )
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
