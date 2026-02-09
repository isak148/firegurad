# MET Integration Module

This module provides integration with the Meteorologisk institutt (MET) Locationforecast API to automatically fetch weather data for fire risk calculations.

## Features

- **MET API Client**: Fetch weather forecasts from MET's Locationforecast API
- **Data Transformation**: Convert MET API responses to the WeatherData format used by the fire risk model
- **Comprehensive Error Handling**: Validation and error handling for API requests and data transformation
- **Full Test Coverage**: 20 unit tests covering all functionality

## Usage

### Basic Usage

```python
from frcm import fetch_and_transform_weather_data, compute

# Fetch weather data for Bergen, Norway
latitude = 60.39
longitude = 5.32

weather_data = fetch_and_transform_weather_data(latitude, longitude)

# Compute fire risk
fire_risks = compute(weather_data)
print(fire_risks)
```

### Using the Client Directly

```python
from frcm.met_integration.client import METClient
from frcm.met_integration.transform import transform_met_to_weather_data

# Create a client (optionally with custom User-Agent)
with METClient(user_agent="myapp/1.0.0") as client:
    # Fetch weather data
    met_response = client.fetch_weather_data(
        latitude=60.39,
        longitude=5.32,
        altitude=0  # optional, in meters
    )
    
    # Transform to WeatherData format
    weather_data = transform_met_to_weather_data(met_response)
```

## API Reference

### METClient

```python
class METClient(user_agent: str = "firegurad/0.1.0 github.com/isak148/firegurad")
```

Client for interacting with the MET Locationforecast API.

**Methods:**
- `fetch_weather_data(latitude: float, longitude: float, altitude: int = 0) -> Dict[str, Any]`: Fetch weather forecast data for a location
- Can be used as a context manager

### transform_met_to_weather_data

```python
def transform_met_to_weather_data(met_response: Dict[str, Any]) -> WeatherData
```

Transform MET API JSON response to WeatherData format.

**Parameters:**
- `met_response`: JSON response from MET API

**Returns:**
- `WeatherData` object with transformed weather data points

### fetch_and_transform_weather_data

```python
def fetch_and_transform_weather_data(
    latitude: float, 
    longitude: float, 
    altitude: int = 0
) -> WeatherData
```

Convenience function to fetch and transform weather data in one call.

## MET API Response Format

The MET Locationforecast API returns data in this structure:

```json
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
            }
        ]
    }
}
```

This is automatically transformed to the WeatherDataPoint format:
- `air_temperature` → `temperature`
- `relative_humidity` → `humidity`
- `wind_speed` → `wind_speed`
- `time` → `timestamp`

## Error Handling

The module handles various error conditions:
- Invalid coordinates (latitude/longitude out of range)
- Network errors (timeouts, connection failures)
- HTTP errors (404, 500, etc.)
- Invalid response format
- Missing required fields

## Testing

Run the test suite:

```bash
pytest tests/met_integration/ -v
```

## MET API Terms of Service

When using the MET API, you must comply with their terms of service:
- Always include a proper User-Agent header identifying your application
- See: https://api.met.no/doc/TermsOfService

## Example

See `examples/met_api_example.py` for a complete example of fetching weather data and computing fire risk.
