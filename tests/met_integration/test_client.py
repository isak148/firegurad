"""
Tests for the MET API client module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from frcm.met_integration.client import METClient


class TestMETClient:
    """Test cases for the METClient class."""
    
    def test_init_default_user_agent(self):
        """Test that the client initializes with a default user agent."""
        client = METClient()
        assert client.user_agent == "firegurad/0.1.0 github.com/isak148/firegurad"
        assert client.session.headers['User-Agent'] == client.user_agent
    
    def test_init_custom_user_agent(self):
        """Test that the client can be initialized with a custom user agent."""
        custom_ua = "test-app/1.0.0"
        client = METClient(user_agent=custom_ua)
        assert client.user_agent == custom_ua
        assert client.session.headers['User-Agent'] == custom_ua
    
    def test_fetch_weather_data_invalid_latitude(self):
        """Test that invalid latitude raises ValueError."""
        client = METClient()
        
        with pytest.raises(ValueError, match="Invalid latitude"):
            client.fetch_weather_data(latitude=91.0, longitude=10.0)
        
        with pytest.raises(ValueError, match="Invalid latitude"):
            client.fetch_weather_data(latitude=-91.0, longitude=10.0)
    
    def test_fetch_weather_data_invalid_longitude(self):
        """Test that invalid longitude raises ValueError."""
        client = METClient()
        
        with pytest.raises(ValueError, match="Invalid longitude"):
            client.fetch_weather_data(latitude=60.0, longitude=181.0)
        
        with pytest.raises(ValueError, match="Invalid longitude"):
            client.fetch_weather_data(latitude=60.0, longitude=-181.0)
    
    @patch('requests.Session.get')
    def test_fetch_weather_data_success(self, mock_get):
        """Test successful weather data fetch."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'properties': {
                'timeseries': [
                    {
                        'time': '2026-01-07T00:00:00Z',
                        'data': {
                            'instant': {
                                'details': {
                                    'air_temperature': -9.7,
                                    'relative_humidity': 85.0,
                                    'wind_speed': 0.8
                                }
                            }
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        client = METClient()
        result = client.fetch_weather_data(latitude=60.39, longitude=5.32)
        
        assert result == mock_response.json.return_value
        mock_get.assert_called_once()
        
        # Verify the parameters passed to the request
        call_args = mock_get.call_args
        assert call_args[1]['params']['lat'] == 60.39
        assert call_args[1]['params']['lon'] == 5.32
        assert call_args[1]['params']['altitude'] == 0
    
    @patch('requests.Session.get')
    def test_fetch_weather_data_with_altitude(self, mock_get):
        """Test weather data fetch with custom altitude."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'properties': {'timeseries': []}}
        mock_get.return_value = mock_response
        
        client = METClient()
        client.fetch_weather_data(latitude=60.39, longitude=5.32, altitude=50)
        
        call_args = mock_get.call_args
        assert call_args[1]['params']['altitude'] == 50
    
    @patch('requests.Session.get')
    def test_fetch_weather_data_http_error(self, mock_get):
        """Test that HTTP errors are properly raised."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        client = METClient()
        with pytest.raises(requests.exceptions.HTTPError):
            client.fetch_weather_data(latitude=60.39, longitude=5.32)
    
    @patch('requests.Session.get')
    def test_fetch_weather_data_timeout(self, mock_get):
        """Test that timeout errors are properly raised."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        client = METClient()
        with pytest.raises(requests.exceptions.Timeout):
            client.fetch_weather_data(latitude=60.39, longitude=5.32)
    
    @patch('requests.Session.get')
    def test_fetch_weather_data_request_exception(self, mock_get):
        """Test that general request exceptions are properly raised."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        
        client = METClient()
        with pytest.raises(requests.exceptions.RequestException):
            client.fetch_weather_data(latitude=60.39, longitude=5.32)
    
    def test_context_manager(self):
        """Test that the client can be used as a context manager."""
        with METClient() as client:
            assert client.session is not None
        # Session should be closed after exiting the context
    
    def test_close(self):
        """Test that close method works correctly."""
        client = METClient()
        with patch.object(client.session, 'close') as mock_close:
            client.close()
            mock_close.assert_called_once()
