"""
Test for the weather data harvester worker
"""
import datetime
import json
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from frcm.worker.harvester import WeatherHarvester, MetNoAPIError
from frcm.worker.locations import Location, LocationConfig
from frcm.datamodel.model import WeatherDataPoint


def test_location_creation():
    """Test Location model creation"""
    location = Location(
        name="Bergen",
        latitude=60.3913,
        longitude=5.3221,
        altitude=12
    )
    assert location.name == "Bergen"
    assert location.latitude == 60.3913
    assert location.longitude == 5.3221
    assert location.altitude == 12
    assert "Bergen" in str(location)


def test_location_config_from_json(tmp_path):
    """Test LocationConfig loading from JSON"""
    config_data = {
        "locations": [
            {
                "name": "Bergen",
                "latitude": 60.3913,
                "longitude": 5.3221,
                "altitude": 12
            },
            {
                "name": "Oslo",
                "latitude": 59.9139,
                "longitude": 10.7522,
                "altitude": 23
            }
        ]
    }
    
    config_file = tmp_path / "test_locations.json"
    with open(config_file, 'w') as f:
        json.dump(config_data, f)
    
    config = LocationConfig.from_json_file(str(config_file))
    assert len(config.locations) == 2
    assert config.locations[0].name == "Bergen"
    assert config.locations[1].name == "Oslo"


def test_weather_harvester_initialization():
    """Test WeatherHarvester initialization"""
    harvester = WeatherHarvester()
    assert harvester.user_agent == "firegurad/0.1.0 github.com/isak148/firegurad"
    
    custom_ua = "custom/1.0"
    harvester_custom = WeatherHarvester(user_agent=custom_ua)
    assert harvester_custom.user_agent == custom_ua


def test_weather_harvester_parse_met_response():
    """Test parsing of MET API response"""
    harvester = WeatherHarvester()
    
    # Mock MET API response
    mock_response = {
        "properties": {
            "timeseries": [
                {
                    "time": "2024-01-01T00:00:00Z",
                    "data": {
                        "instant": {
                            "details": {
                                "air_temperature": -5.0,
                                "relative_humidity": 80.0,
                                "wind_speed": 2.5
                            }
                        }
                    }
                },
                {
                    "time": "2024-01-01T01:00:00Z",
                    "data": {
                        "instant": {
                            "details": {
                                "air_temperature": -4.5,
                                "relative_humidity": 82.0,
                                "wind_speed": 2.8
                            }
                        }
                    }
                }
            ]
        }
    }
    
    weather_data = harvester._parse_met_response(mock_response, max_hours=24)
    
    assert len(weather_data.data) == 2
    assert weather_data.data[0].temperature == -5.0
    assert weather_data.data[0].humidity == 80.0
    assert weather_data.data[0].wind_speed == 2.5
    assert weather_data.data[1].temperature == -4.5


def test_weather_harvester_parse_empty_response():
    """Test parsing of empty MET API response"""
    harvester = WeatherHarvester()
    
    mock_response = {
        "properties": {
            "timeseries": []
        }
    }
    
    with pytest.raises(MetNoAPIError, match="No valid weather data points"):
        harvester._parse_met_response(mock_response, max_hours=24)


@patch('requests.Session.get')
def test_weather_harvester_fetch_success(mock_get):
    """Test successful weather data fetching"""
    harvester = WeatherHarvester()
    location = Location(name="Bergen", latitude=60.3913, longitude=5.3221)
    
    # Mock successful API response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "properties": {
            "timeseries": [
                {
                    "time": "2024-01-01T00:00:00Z",
                    "data": {
                        "instant": {
                            "details": {
                                "air_temperature": -5.0,
                                "relative_humidity": 80.0,
                                "wind_speed": 2.5
                            }
                        }
                    }
                }
            ]
        }
    }
    mock_get.return_value = mock_response
    
    weather_data = harvester.fetch_weather_data(location, hours=24)
    
    assert len(weather_data.data) == 1
    assert weather_data.data[0].temperature == -5.0
    mock_get.assert_called_once()


@patch('requests.Session.get')
def test_weather_harvester_fetch_failure(mock_get):
    """Test weather data fetching failure"""
    harvester = WeatherHarvester()
    location = Location(name="Bergen", latitude=60.3913, longitude=5.3221)
    
    # Mock failed API response
    import requests
    mock_get.side_effect = requests.exceptions.RequestException("Network error")
    
    with pytest.raises(MetNoAPIError, match="Failed to fetch weather data"):
        harvester.fetch_weather_data(location, hours=24)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
