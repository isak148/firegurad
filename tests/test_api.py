"""Tests for FRCM API authentication and endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import datetime

from frcm.api.app import app
from frcm.datamodel.model import WeatherDataPoint, WeatherData, FireRisk, FireRiskPrediction


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


@pytest.fixture
def sample_weather_data():
    """Create sample weather data for testing."""
    data_points = [
        WeatherDataPoint(
            timestamp=datetime.datetime(2026, 1, 9, i, 0, 0),
            temperature=5.0 + i * 0.1,
            humidity=0.85 - i * 0.01,
            wind_speed=3.0 + i * 0.05
        )
        for i in range(10)
    ]
    return WeatherData(data=data_points)


class TestPublicEndpoints:
    """Test public endpoints that don't require authentication."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "status" in data
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    def test_api_info_endpoint(self, client):
        """Test API info endpoint."""
        response = client.get("/api-info")
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        assert "authentication" in data
        assert "input_format" in data
        assert "output_format" in data


class TestAuthenticationDisabled:
    """Test API behavior when authentication is disabled."""
    
    @patch("frcm.api.auth.settings")
    @patch("frcm.api.config.settings")
    def test_calculate_without_api_key_when_auth_disabled(self, mock_config_settings, mock_auth_settings, client, sample_weather_data):
        """Test that calculation works without API key when auth is disabled."""
        mock_config_settings.is_auth_enabled = False
        mock_config_settings.API_KEYS = []
        mock_auth_settings.is_auth_enabled = False
        mock_auth_settings.API_KEYS = []
        
        response = client.post(
            "/calculate",
            json=sample_weather_data.model_dump(mode='json')
        )
        assert response.status_code == 200
        result = response.json()
        assert "firerisks" in result
        assert len(result["firerisks"]) > 0


class TestAuthenticationEnabled:
    """Test API behavior when authentication is enabled."""
    
    @patch("frcm.api.auth.settings")
    def test_calculate_without_api_key_when_auth_enabled(self, mock_settings, client, sample_weather_data):
        """Test that calculation fails without API key when auth is enabled."""
        mock_settings.is_auth_enabled = True
        mock_settings.API_KEYS = ["test-key-1", "test-key-2"]
        
        response = client.post(
            "/calculate",
            json=sample_weather_data.model_dump(mode='json')
        )
        assert response.status_code == 401
        assert "Missing API key" in response.json()["detail"]
    
    @patch("frcm.api.auth.settings")
    def test_calculate_with_invalid_api_key(self, mock_settings, client, sample_weather_data):
        """Test that calculation fails with invalid API key."""
        mock_settings.is_auth_enabled = True
        mock_settings.API_KEYS = ["test-key-1", "test-key-2"]
        
        response = client.post(
            "/calculate",
            json=sample_weather_data.model_dump(mode='json'),
            headers={"X-API-Key": "invalid-key"}
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    @patch("frcm.api.auth.settings")
    def test_calculate_with_valid_api_key(self, mock_settings, client, sample_weather_data):
        """Test that calculation succeeds with valid API key."""
        mock_settings.is_auth_enabled = True
        mock_settings.API_KEYS = ["test-key-1", "test-key-2"]
        
        response = client.post(
            "/calculate",
            json=sample_weather_data.model_dump(mode='json'),
            headers={"X-API-Key": "test-key-1"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "firerisks" in result
        assert len(result["firerisks"]) > 0
        
        # Verify structure of fire risk predictions
        for risk in result["firerisks"]:
            assert "timestamp" in risk
            assert "ttf" in risk
            assert isinstance(risk["ttf"], (int, float))


class TestCalculateEndpoint:
    """Test the calculate endpoint functionality."""
    
    @patch("frcm.api.auth.settings")
    @patch("frcm.api.config.settings")
    def test_calculate_with_empty_data(self, mock_config_settings, mock_auth_settings, client):
        """Test that calculation fails with empty data."""
        mock_config_settings.is_auth_enabled = False
        mock_config_settings.API_KEYS = []
        mock_auth_settings.is_auth_enabled = False
        mock_auth_settings.API_KEYS = []
        
        response = client.post(
            "/calculate",
            json={"data": []}
        )
        # Should return either 400 (our validation) or 500 (compute error)
        assert response.status_code in [400, 500]
    
    @patch("frcm.api.auth.settings")
    @patch("frcm.api.config.settings")
    def test_calculate_with_invalid_data_format(self, mock_config_settings, mock_auth_settings, client):
        """Test that calculation fails with invalid data format."""
        mock_config_settings.is_auth_enabled = False
        mock_config_settings.API_KEYS = []
        mock_auth_settings.is_auth_enabled = False
        mock_auth_settings.API_KEYS = []
        
        response = client.post(
            "/calculate",
            json={"invalid": "data"}
        )
        assert response.status_code == 422  # Validation error
    
    @patch("frcm.api.auth.settings")
    @patch("frcm.api.config.settings")
    def test_calculate_with_valid_data(self, mock_config_settings, mock_auth_settings, client, sample_weather_data):
        """Test successful calculation with valid data."""
        mock_config_settings.is_auth_enabled = False
        mock_config_settings.API_KEYS = []
        mock_auth_settings.is_auth_enabled = False
        mock_auth_settings.API_KEYS = []
        
        response = client.post(
            "/calculate",
            json=sample_weather_data.model_dump(mode='json')
        )
        assert response.status_code == 200
        result = response.json()
        
        # Verify response structure
        assert "firerisks" in result
        firerisks = result["firerisks"]
        assert len(firerisks) > 0
        
        # Verify each fire risk has required fields
        for risk in firerisks:
            assert "timestamp" in risk
            assert "ttf" in risk
            # TTF should be positive
            assert risk["ttf"] > 0

