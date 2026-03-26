"""
Tests for the MET Frost API client module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from datetime import datetime, timedelta
from frcm.met_integration.frost_client import FrostClient


class TestFrostClient:
    """Test cases for the FrostClient class."""
    
    def test_init_with_client_id(self):
        """Test that the client initializes with required client_id."""
        client_id = "test-client-id"
        client = FrostClient(client_id=client_id)
        assert client.client_id == client_id
        assert client.user_agent == "firegurad/0.1.0 github.com/isak148/firegurad"
        assert client.session.auth == (client_id, '')
    
    def test_init_custom_user_agent(self):
        """Test that the client can be initialized with a custom user agent."""
        custom_ua = "test-app/1.0.0"
        client = FrostClient(client_id="test-id", user_agent=custom_ua)
        assert client.user_agent == custom_ua
        assert client.session.headers['User-Agent'] == custom_ua
    
    def test_fetch_historical_observations_invalid_latitude(self):
        """Test that invalid latitude raises ValueError."""
        client = FrostClient(client_id="test-id")
        start_time = datetime.now() - timedelta(days=7)
        end_time = datetime.now()
        
        with pytest.raises(ValueError, match="Invalid latitude"):
            client.fetch_historical_observations(
                latitude=91.0,
                longitude=10.0,
                start_time=start_time,
                end_time=end_time
            )
        
        with pytest.raises(ValueError, match="Invalid latitude"):
            client.fetch_historical_observations(
                latitude=-91.0,
                longitude=10.0,
                start_time=start_time,
                end_time=end_time
            )
    
    def test_fetch_historical_observations_invalid_longitude(self):
        """Test that invalid longitude raises ValueError."""
        client = FrostClient(client_id="test-id")
        start_time = datetime.now() - timedelta(days=7)
        end_time = datetime.now()
        
        with pytest.raises(ValueError, match="Invalid longitude"):
            client.fetch_historical_observations(
                latitude=60.0,
                longitude=181.0,
                start_time=start_time,
                end_time=end_time
            )
        
        with pytest.raises(ValueError, match="Invalid longitude"):
            client.fetch_historical_observations(
                latitude=60.0,
                longitude=-181.0,
                start_time=start_time,
                end_time=end_time
            )
    
    @patch('requests.Session.get')
    def test_fetch_historical_observations_success(self, mock_get):
        """Test successful historical data fetch."""
        observation_row = {
            "referenceTime": "2026-02-05T12:00:00.000Z",
            "observations": [
                {"elementId": "air_temperature", "value": 5.2},
                {"elementId": "relative_humidity", "value": 85.0},
                {"elementId": "wind_speed", "value": 3.5}
            ]
        }

        def make_response(url, **kwargs):
            mock_resp = Mock()
            mock_resp.status_code = 200
            if 'availableTimeSeries' in url:
                mock_resp.json.return_value = {"data": [{"sourceId": "SN18700:0"}]}
            elif 'sources' in url:
                mock_resp.json.return_value = {"data": [{"id": "SN18700"}]}
            else:
                mock_resp.json.return_value = {"data": [observation_row]}
            return mock_resp

        mock_get.side_effect = make_response

        client = FrostClient(client_id="test-id")
        start_time = datetime.now() - timedelta(days=1)
        end_time = datetime.now()

        result = client.fetch_historical_observations(
            latitude=60.39,
            longitude=5.32,
            start_time=start_time,
            end_time=end_time
        )

        assert 'data' in result
        assert len(result['data']) > 0
        assert mock_get.call_count > 0

        # Verify that availableTimeSeries was queried with geometry and element params
        avail_calls = [
            c for c in mock_get.call_args_list
            if 'availableTimeSeries' in c.args[0]
        ]
        assert len(avail_calls) > 0
        assert 'geometry' in avail_calls[0].kwargs['params']
        assert 'air_temperature' in avail_calls[0].kwargs['params']['elements']
    
    @patch('requests.Session.get')
    def test_fetch_historical_observations_timeout(self, mock_get):
        """Test timeout handling."""
        mock_get.side_effect = requests.exceptions.Timeout()
        
        client = FrostClient(client_id="test-id")
        start_time = datetime.now() - timedelta(days=1)
        end_time = datetime.now()
        
        with pytest.raises(requests.exceptions.Timeout):
            client.fetch_historical_observations(
                latitude=60.39,
                longitude=5.32,
                start_time=start_time,
                end_time=end_time
            )
    
    @patch('requests.Session.get')
    def test_fetch_historical_observations_http_error(self, mock_get):
        """Test HTTP error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Internal Server Error", "reason": ""}}
        mock_get.return_value = mock_response
        
        client = FrostClient(client_id="test-id")
        start_time = datetime.now() - timedelta(days=1)
        end_time = datetime.now()
        
        with pytest.raises(ValueError):
            client.fetch_historical_observations(
                latitude=60.39,
                longitude=5.32,
                start_time=start_time,
                end_time=end_time
            )
    
    @patch('requests.Session.get')
    def test_fetch_historical_observations_invalid_client_id(self, mock_get):
        """Test handling of invalid client ID (401 error)."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"message": "Unauthorized", "reason": "Invalid credentials"}}
        mock_get.return_value = mock_response
        
        client = FrostClient(client_id="invalid-id")
        start_time = datetime.now() - timedelta(days=1)
        end_time = datetime.now()
        
        with pytest.raises(ValueError, match="Invalid Frost API client ID"):
            client.fetch_historical_observations(
                latitude=60.39,
                longitude=5.32,
                start_time=start_time,
                end_time=end_time
            )
    
    def test_context_manager(self):
        """Test that FrostClient can be used as a context manager."""
        client_id = "test-id"
        
        with FrostClient(client_id=client_id) as client:
            assert client.client_id == client_id
            assert client.session is not None
    
    @patch('requests.Session.get')
    def test_custom_elements(self, mock_get):
        """Test fetching with custom weather elements."""
        def make_response(url, **kwargs):
            mock_resp = Mock()
            mock_resp.status_code = 200
            if 'availableTimeSeries' in url:
                mock_resp.json.return_value = {"data": [{"sourceId": "SN18700:0"}]}
            else:
                mock_resp.json.return_value = {"data": []}
            return mock_resp

        mock_get.side_effect = make_response

        client = FrostClient(client_id="test-id")
        start_time = datetime.now() - timedelta(days=1)
        end_time = datetime.now()
        
        custom_elements = ['air_temperature', 'wind_speed']
        result = client.fetch_historical_observations(
            latitude=60.39,
            longitude=5.32,
            start_time=start_time,
            end_time=end_time,
            elements=custom_elements
        )
        
        assert 'data' in result
        # Verify custom elements were used in API calls
        all_params = [c.kwargs.get('params', {}) for c in mock_get.call_args_list]
        elements_used = {p['elements'] for p in all_params if 'elements' in p}
        assert any('air_temperature' in e for e in elements_used)
        assert any('wind_speed' in e for e in elements_used)
        # Verify default-only element was not requested
        assert not any('relative_humidity' in e for e in elements_used)
