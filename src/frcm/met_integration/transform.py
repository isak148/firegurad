"""
Data transformation module for converting MET API responses to WeatherData format.

This module handles the conversion of JSON responses from the MET Locationforecast API
into the WeatherData format used by the fire risk calculation model.
"""

import datetime
from typing import Dict, Any, List
import logging
from frcm.datamodel.model import WeatherData, WeatherDataPoint

logger = logging.getLogger(__name__)


def _normalize_frost_element_id(element_id: str) -> str:
    """Map derived Frost element expressions to canonical model element IDs."""
    if not element_id:
        return ""

    normalized = element_id.strip()
    if normalized.startswith("mean(air_temperature"):
        return "air_temperature"
    if normalized.startswith("mean(relative_humidity"):
        return "relative_humidity"
    if normalized.startswith("mean(wind_speed"):
        return "wind_speed"
    return normalized


def transform_met_to_weather_data(met_response: Dict[str, Any]) -> WeatherData:
    """
    Transform MET API JSON response to WeatherData format.
    
    The MET Locationforecast API returns data in the following structure:
    {
        "properties": {
            "timeseries": [
                {
                    "time": "2026-01-07T00:00:00Z",
                    "data": {
                        "instant": {
                            "details": {
                                "air_temperature": -9.7,
                                "relative_humidity": 85.0,
                                "wind_speed": 0.8
                            }
                        }
                    }
                },
                ...
            ]
        }
    }
    
    Args:
        met_response: JSON response from MET API as a dictionary
    
    Returns:
        WeatherData object containing the transformed data points
    
    Raises:
        ValueError: If the response format is invalid or missing required fields
        KeyError: If required fields are missing from the response
    """
    try:
        # Extract the timeseries from the response
        if 'properties' not in met_response:
            raise ValueError("Invalid MET API response: missing 'properties' field")
        
        properties = met_response['properties']
        if 'timeseries' not in properties:
            raise ValueError("Invalid MET API response: missing 'timeseries' field")
        
        timeseries = properties['timeseries']
        if not timeseries:
            raise ValueError("MET API response contains no timeseries data")
        
        logger.info(f"Processing {len(timeseries)} data points from MET API response")
        
        weather_data_points: List[WeatherDataPoint] = []
        
        for entry in timeseries:
            try:
                # Extract timestamp
                time_str = entry['time']
                timestamp = datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                
                # Extract instant weather data
                instant_data = entry['data']['instant']['details']
                
                # Extract required fields
                temperature = float(instant_data['air_temperature'])
                humidity = float(instant_data['relative_humidity'])
                wind_speed = float(instant_data['wind_speed'])
                
                # Create WeatherDataPoint
                data_point = WeatherDataPoint(
                    timestamp=timestamp,
                    temperature=temperature,
                    humidity=humidity,
                    wind_speed=wind_speed
                )
                
                weather_data_points.append(data_point)
                
            except KeyError as e:
                logger.warning(f"Skipping data point due to missing field: {e}")
                continue
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping data point due to conversion error: {e}")
                continue
        
        if not weather_data_points:
            raise ValueError("No valid weather data points could be extracted from MET API response")
        
        logger.info(f"Successfully transformed {len(weather_data_points)} data points")
        
        return WeatherData(data=weather_data_points)
        
    except Exception as e:
        logger.error(f"Error transforming MET API response: {e}")
        raise


def transform_frost_to_weather_data(frost_response: Dict[str, Any]) -> WeatherData:
    """
    Transform Frost API JSON response to WeatherData format.
    
    The Frost API returns observations in this structure:
    {
        "data": [
            {
                "referenceTime": "2026-02-05T00:00:00.000Z",
                "observations": [
                    {
                        "elementId": "air_temperature",
                        "value": 5.2
                    },
                    {
                        "elementId": "relative_humidity",
                        "value": 85.0
                    },
                    {
                        "elementId": "wind_speed",
                        "value": 3.5
                    }
                ]
            },
            ...
        ]
    }
    
    Args:
        frost_response: JSON response from Frost API as a dictionary
    
    Returns:
        WeatherData object containing the transformed data points
    
    Raises:
        ValueError: If the response format is invalid or missing required fields
    """
    try:
        # Extract the data array from the response
        if 'data' not in frost_response:
            raise ValueError("Invalid Frost API response: missing 'data' field")
        
        data_array = frost_response['data']
        if not data_array:
            raise ValueError("Frost API response contains no data")
        
        logger.info(f"Processing {len(data_array)} observations from Frost API response")
        
        # Frost can return the required elements split across multiple entries
        # (same referenceTime, different element/source). Merge by timestamp first.
        merged_by_time: Dict[str, Dict[str, float]] = {}

        for entry in data_array:
            try:
                time_str = entry['referenceTime']
                observations = entry.get('observations', [])

                bucket = merged_by_time.setdefault(time_str, {})
                for obs in observations:
                    element_id = _normalize_frost_element_id(obs.get('elementId', ''))
                    value = obs.get('value')
                    if value is not None:
                        bucket[element_id] = float(value)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping observation due to error: {e}")
                continue

        weather_data_points: List[WeatherDataPoint] = []
        required_elements = {'air_temperature', 'relative_humidity'}
        wind_fallback_count = 0

        for time_str in sorted(merged_by_time.keys()):
            values = merged_by_time[time_str]
            if not required_elements.issubset(values.keys()):
                logger.warning(f"Skipping observation at {time_str}: missing required elements")
                continue

            try:
                timestamp = datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                wind_val = values.get('wind_speed', None)
                if wind_val is None:
                    wind_fallback_count += 1
                    wind_val = 0.0
                data_point = WeatherDataPoint(
                    timestamp=timestamp,
                    temperature=values['air_temperature'],
                    humidity=values['relative_humidity'],
                    wind_speed=wind_val
                )
                weather_data_points.append(data_point)
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping merged observation at {time_str} due to error: {e}")
                continue
        
        if not weather_data_points:
            raise ValueError("No valid weather data points could be extracted from Frost API response")
        
        if wind_fallback_count > 0:
            logger.warning(
                f"Wind speed fallback used for {wind_fallback_count}/{len(weather_data_points)} observations. "
                f"({100*wind_fallback_count/len(weather_data_points):.1f}% using 0.0 default)"
            )
        
        logger.info(f"Successfully transformed {len(weather_data_points)} data points from Frost API")
        
        return WeatherData(data=weather_data_points)
        
    except Exception as e:
        logger.error(f"Error transforming Frost API response: {e}")
        raise


def fetch_and_transform_weather_data(latitude: float, longitude: float, altitude: int = 0) -> WeatherData:
    """
    Convenience function to fetch and transform weather data in one call.
    
    Args:
        latitude: Latitude coordinate (decimal degrees)
        longitude: Longitude coordinate (decimal degrees)
        altitude: Altitude in meters above sea level (optional)
    
    Returns:
        WeatherData object with transformed weather data
    
    Raises:
        requests.exceptions.RequestException: If the API request fails
        ValueError: If coordinates are invalid or response cannot be transformed
    """
    from frcm.met_integration.client import METClient
    
    with METClient() as client:
        met_response = client.fetch_weather_data(latitude, longitude, altitude)
        return transform_met_to_weather_data(met_response)
