# Historical Weather Data Integration

This document describes the integration with the MET Frost API for fetching historical weather observations.

## Overview

The FireGuard application now includes support for fetching real historical weather data from the Norwegian Meteorological Institute (MET) Frost API, instead of relying on mock/generated data. This feature allows the web interface to display actual historical fire risk assessments based on real weather observations.

## Architecture

### Components

1. **FrostClient** (`src/frcm/met_integration/frost_client.py`)
   - Python client for the MET Frost API
   - Handles authentication using client ID
   - Fetches historical weather observations (temperature, humidity, wind speed)
   - Validates coordinates and handles errors

2. **Transform Function** (`src/frcm/met_integration/transform.py`)
   - `transform_frost_to_weather_data()` converts Frost API responses to WeatherData format
   - Maps Frost observation format to fire risk calculation input format

3. **API Endpoint** (`src/frcm/api/app.py`)
   - `/historical` endpoint serves historical data to frontend
   - Accepts latitude, longitude, and days parameters
   - Returns both weather data and calculated fire risk predictions

4. **Frontend Integration** (`index.html`)
   - Fetches historical data from backend API instead of generating mock data
   - Displays real observations with calculated fire risk indicators
   - Graceful error handling with user-friendly messages

## Setup

### 1. Get Frost API Credentials

To use historical weather data, you need a Frost API client ID:

1. Visit https://frost.met.no/auth/requestCredentials.html
2. Register for a free client ID
3. Save the client ID for configuration

### 2. Configure Environment

Add your Frost API client ID to the `.env` file:

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your Frost client ID
FRCM_FROST_CLIENT_ID=your-frost-client-id-here
```

### 3. Start the API Server

The historical data endpoint is part of the main FRCM API:

```bash
# Using Python
python3 -m frcm.api.server

# Or using the installed command
frcm-api
```

The API will start on port 8000 (or configured port) and the `/historical` endpoint will be available.

### 4. Open the Web Interface

Open `index.html` in a web browser. The historical data tab will now fetch real data from the Frost API.

## Usage

### API Endpoint

**Endpoint**: `GET /historical`

**Parameters**:
- `latitude` (float, required): Latitude coordinate (-90 to 90)
- `longitude` (float, required): Longitude coordinate (-180 to 180)
- `days` (int, optional): Number of days of historical data (1-30, default: 7)

**Example Request**:
```bash
curl "http://localhost:8000/historical?latitude=60.39&longitude=5.32&days=7"
```

**Response**:
```json
{
  "latitude": 60.39,
  "longitude": 5.32,
  "start_time": "2026-02-05T10:41:00+00:00",
  "end_time": "2026-02-12T10:41:00+00:00",
  "weather_data": [
    {
      "timestamp": "2026-02-05T00:00:00+00:00",
      "temperature": 5.2,
      "humidity": 85.0,
      "wind_speed": 3.5
    },
    ...
  ],
  "fire_risk": [
    {
      "timestamp": "2026-02-05T00:00:00+00:00",
      "ttf": 45.3
    },
    ...
  ]
}
```

### Programmatic Usage

```python
from frcm.met_integration.frost_client import FrostClient
from frcm.met_integration.transform import transform_frost_to_weather_data
from frcm.fireriskmodel.compute import compute
from datetime import datetime, timedelta
import os

# Get Frost API client ID from environment
client_id = os.environ['FRCM_FROST_CLIENT_ID']

# Define location and time range
latitude = 60.39
longitude = 5.32
end_time = datetime.now()
start_time = end_time - timedelta(days=7)

# Fetch historical data
with FrostClient(client_id=client_id) as client:
    frost_response = client.fetch_historical_observations(
        latitude=latitude,
        longitude=longitude,
        start_time=start_time,
        end_time=end_time
    )
    
    # Transform to WeatherData format
    weather_data = transform_frost_to_weather_data(frost_response)

# Calculate fire risk
fire_risk = compute(weather_data)

print(f"Fetched {len(weather_data.data)} historical observations")
print(f"Calculated {len(fire_risk.firerisks)} fire risk predictions")
```

## Error Handling

### Common Errors

1. **503 Service Unavailable**: Frost API client ID not configured
   - Solution: Set `FRCM_FROST_CLIENT_ID` environment variable

2. **401 Unauthorized**: Invalid Frost API client ID
   - Solution: Verify your client ID is correct and active

3. **Connection Error**: Cannot connect to backend API
   - Solution: Ensure the API server is running on the expected port

4. **No Data Available**: No weather stations near the location
   - Solution: Try a different location or time range

## Testing

Run the test suite:

```bash
# Test Frost client
python3 -m pytest tests/met_integration/test_frost_client.py -v

# Test transform functions
python3 -m pytest tests/met_integration/test_transform.py::TestTransformFrostToWeatherData -v

# Test all MET integration
python3 -m pytest tests/met_integration/ -v
```

## MET Frost API Reference

- **Documentation**: https://frost.met.no/
- **API Terms**: https://frost.met.no/termsofservice.html
- **Request Credentials**: https://frost.met.no/auth/requestCredentials.html

### Data Sources

The Frost API provides access to:
- Temperature observations from weather stations
- Relative humidity measurements
- Wind speed data
- Hourly resolution (configurable)

### Rate Limits

- Frost API has rate limits for free tier users
- Recommend caching results when possible
- Default 1-hour resolution reduces data volume

## Troubleshooting

### Frontend shows "Historical data service not configured"

This means the backend API cannot access the Frost API client ID.

**Solution**:
1. Set `FRCM_FROST_CLIENT_ID` in `.env` file
2. Restart the API server
3. Verify the environment variable is loaded: `echo $FRCM_FROST_CLIENT_ID`

### Backend returns empty data

The Frost API might not have data for your location or time range.

**Solution**:
1. Check if weather stations exist near your coordinates
2. Try a different time range
3. Use coordinates within Norway or Nordic region (best coverage)

### CORS errors in browser console

The frontend needs to connect to the backend API.

**Solution**:
1. Ensure API server is running
2. Check the `BACKEND_API_ENDPOINT` in `index.html` matches your API server
3. CORS is enabled by default in the API

## Future Improvements

Potential enhancements for the historical data feature:

1. **Caching**: Cache Frost API responses to reduce API calls
2. **Multiple Stations**: Aggregate data from multiple nearby weather stations
3. **Data Interpolation**: Fill gaps in historical data
4. **Configurable Resolution**: Allow different time resolutions (hourly, daily)
5. **Extended History**: Support longer historical periods (months, years)
6. **Export Functionality**: Download historical data as CSV

## Related Documentation

- [MET Integration README](README.md)
- [API Documentation](../../../API_README.md)
- [Main Project README](../../../README.md)
