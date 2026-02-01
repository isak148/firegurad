"""
Tests for the MET API data transformation module.
"""

import pytest
import datetime
from frcm.met_integration.transform import transform_met_to_weather_data, fetch_and_transform_weather_data
from frcm.datamodel.model import WeatherData, WeatherDataPoint


class TestTransformMETToWeatherData:
    """Test cases for the transform_met_to_weather_data function."""
    
    def test_transform_valid_response(self):
        """Test transformation of a valid MET API response."""
        met_response = {
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
                    },
                    {
                        'time': '2026-01-07T01:00:00Z',
                        'data': {
                            'instant': {
                                'details': {
                                    'air_temperature': -9.7,
                                    'relative_humidity': 84.0,
                                    'wind_speed': 0.3
                                }
                            }
                        }
                    }
                ]
            }
        }
        
        result = transform_met_to_weather_data(met_response)
        
        assert isinstance(result, WeatherData)
        assert len(result.data) == 2
        
        # Check first data point
        first_point = result.data[0]
        assert isinstance(first_point, WeatherDataPoint)
        assert first_point.temperature == -9.7
        assert first_point.humidity == 85.0
        assert first_point.wind_speed == 0.8
        assert first_point.timestamp == datetime.datetime(2026, 1, 7, 0, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Check second data point
        second_point = result.data[1]
        assert second_point.temperature == -9.7
        assert second_point.humidity == 84.0
        assert second_point.wind_speed == 0.3
        assert second_point.timestamp == datetime.datetime(2026, 1, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
    
    def test_transform_missing_properties(self):
        """Test that missing 'properties' field raises ValueError."""
        met_response = {'some_field': 'some_value'}
        
        with pytest.raises(ValueError, match="missing 'properties' field"):
            transform_met_to_weather_data(met_response)
    
    def test_transform_missing_timeseries(self):
        """Test that missing 'timeseries' field raises ValueError."""
        met_response = {'properties': {'some_field': 'some_value'}}
        
        with pytest.raises(ValueError, match="missing 'timeseries' field"):
            transform_met_to_weather_data(met_response)
    
    def test_transform_empty_timeseries(self):
        """Test that empty timeseries raises ValueError."""
        met_response = {'properties': {'timeseries': []}}
        
        with pytest.raises(ValueError, match="contains no timeseries data"):
            transform_met_to_weather_data(met_response)
    
    def test_transform_missing_required_fields(self):
        """Test that missing required fields in data points are handled gracefully."""
        met_response = {
            'properties': {
                'timeseries': [
                    {
                        'time': '2026-01-07T00:00:00Z',
                        'data': {
                            'instant': {
                                'details': {
                                    'air_temperature': -9.7,
                                    # missing humidity and wind_speed
                                }
                            }
                        }
                    },
                    {
                        'time': '2026-01-07T01:00:00Z',
                        'data': {
                            'instant': {
                                'details': {
                                    'air_temperature': -9.7,
                                    'relative_humidity': 84.0,
                                    'wind_speed': 0.3
                                }
                            }
                        }
                    }
                ]
            }
        }
        
        result = transform_met_to_weather_data(met_response)
        
        # Should only include the valid data point (second one)
        assert len(result.data) == 1
        assert result.data[0].temperature == -9.7
        assert result.data[0].humidity == 84.0
        assert result.data[0].wind_speed == 0.3
    
    def test_transform_all_invalid_data_points(self):
        """Test that all invalid data points raises ValueError."""
        met_response = {
            'properties': {
                'timeseries': [
                    {
                        'time': '2026-01-07T00:00:00Z',
                        'data': {
                            'instant': {
                                'details': {
                                    'air_temperature': -9.7,
                                    # missing required fields
                                }
                            }
                        }
                    }
                ]
            }
        }
        
        with pytest.raises(ValueError, match="No valid weather data points could be extracted"):
            transform_met_to_weather_data(met_response)
    
    def test_transform_handles_timezone_conversion(self):
        """Test that timestamps with Z suffix are correctly converted."""
        met_response = {
            'properties': {
                'timeseries': [
                    {
                        'time': '2026-01-07T12:30:00Z',
                        'data': {
                            'instant': {
                                'details': {
                                    'air_temperature': 5.0,
                                    'relative_humidity': 70.0,
                                    'wind_speed': 2.5
                                }
                            }
                        }
                    }
                ]
            }
        }
        
        result = transform_met_to_weather_data(met_response)
        
        assert result.data[0].timestamp.tzinfo is not None
        assert result.data[0].timestamp == datetime.datetime(2026, 1, 7, 12, 30, 0, tzinfo=datetime.timezone.utc)
    
    def test_transform_handles_numeric_types(self):
        """Test that various numeric types are handled correctly."""
        met_response = {
            'properties': {
                'timeseries': [
                    {
                        'time': '2026-01-07T00:00:00Z',
                        'data': {
                            'instant': {
                                'details': {
                                    'air_temperature': -9,  # int
                                    'relative_humidity': 85,  # int
                                    'wind_speed': 0.8  # float
                                }
                            }
                        }
                    }
                ]
            }
        }
        
        result = transform_met_to_weather_data(met_response)
        
        assert result.data[0].temperature == -9.0
        assert result.data[0].humidity == 85.0
        assert result.data[0].wind_speed == 0.8


class TestFetchAndTransformWeatherData:
    """Test cases for the fetch_and_transform_weather_data convenience function."""
    
    def test_fetch_and_transform_integration(self, mocker):
        """Test the integrated fetch and transform function."""
        # Mock the METClient at the module level
        mock_client = mocker.MagicMock()
        mock_client.fetch_weather_data.return_value = {
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
        mock_client.__enter__ = mocker.MagicMock(return_value=mock_client)
        mock_client.__exit__ = mocker.MagicMock(return_value=False)
        
        # Patch the client at the import location
        mocker.patch('frcm.met_integration.client.METClient', return_value=mock_client)
        
        result = fetch_and_transform_weather_data(60.39, 5.32, 50)
        
        assert isinstance(result, WeatherData)
        assert len(result.data) == 1
        mock_client.fetch_weather_data.assert_called_once_with(60.39, 5.32, 50)
