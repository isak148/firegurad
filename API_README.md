# Fire Risk Prediction REST API

This REST API provides fire risk predictions (Time To Flashover - TTF) for any geographic location based on weather forecast data.

## Overview

The API calculates fire risk indicators using the dynamic fire risk model described in:

> R.D: Strand and L.M. Kristensen. [*An implementation, evaluation and validation of a dynamic fire and conflagration risk indicator for wooden homes*](https://doi.org/10.1016/j.procs.2024.05.195).

## Installation

Install the required dependencies:

```bash
pip install -e .
```

## Running the API Server

Start the API server using uvicorn:

```bash
python3 -m uvicorn frcm.api:app --host 0.0.0.0 --port 8000
```

Or use the convenience script:

```bash
python3 src/frcm/run_api.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Root Endpoint

**GET /** - API information and available endpoints

```bash
curl http://localhost:8000/
```

Response:
```json
{
  "name": "Fire Risk Prediction API",
  "version": "0.1.0",
  "description": "Calculate fire risk (time to flashover) for any location",
  "endpoints": {
    "predict": "/api/v1/predict"
  }
}
```

### Predict Fire Risk

**POST /api/v1/predict** - Calculate fire risk for given coordinates

Request body:
```json
{
  "latitude": 60.3913,
  "longitude": 5.3221,
  "days_ahead": 7
}
```

Parameters:
- `latitude` (float, required): Latitude coordinate (-90 to 90)
- `longitude` (float, required): Longitude coordinate (-180 to 180)
- `days_ahead` (int, optional): Number of days to predict (1-14, default: 7)
- `use_sample_data` (bool, query parameter): Use sample data for testing instead of fetching from API

Example request:

```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 60.3913,
    "longitude": 5.3221,
    "days_ahead": 7
  }'
```

Example with sample data (for testing):

```bash
curl -X POST 'http://localhost:8000/api/v1/predict?use_sample_data=true' \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 60.3913,
    "longitude": 5.3221,
    "days_ahead": 3
  }'
```

Response:
```json
{
  "latitude": 60.3913,
  "longitude": 5.3221,
  "predictions": [
    {
      "timestamp": "2026-01-07T00:00:00Z",
      "ttf": 6.072481167177002
    },
    {
      "timestamp": "2026-01-07T01:00:00Z",
      "ttf": 5.7243022443357905
    }
    // ... more predictions (hourly)
  ],
  "generated_at": "2026-02-09T10:15:00.123456Z"
}
```

### Health Check

**GET /health** - Check API health status

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy"
}
```

## Interactive API Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Understanding TTF (Time To Flashover)

The API returns TTF (Time To Flashover) values for each hour in the prediction period. TTF is a fire risk indicator measured in hours that represents how quickly a fire could develop to flashover conditions based on:

- Indoor humidity levels (calculated from outdoor weather conditions)
- Moisture content in wooden building materials
- Temperature and ventilation factors

**Lower TTF values indicate higher fire risk.**

## Weather Data Source

The API fetches weather forecast data from the Norwegian Meteorological Institute (met.no) API:
- https://api.met.no/weatherapi/locationforecast/2.0/

The API requires the following weather parameters:
- Temperature (°C)
- Relative humidity (%)
- Wind speed (m/s)

## Error Handling

The API returns appropriate HTTP status codes:

- `200 OK`: Successful prediction
- `400 Bad Request`: Invalid input parameters
- `404 Not Found`: No weather data available for location
- `503 Service Unavailable`: Unable to fetch weather data
- `500 Internal Server Error`: Error processing data

Example error response:
```json
{
  "detail": "Unable to fetch weather data: Connection timeout"
}
```

## Rate Limiting

The API uses the met.no weather API which has rate limits. For production use, consider:
- Implementing caching for repeated requests
- Adding rate limiting to the API
- Using authentication and API keys

## Development

The API is built with:
- **FastAPI**: Modern Python web framework
- **Pydantic**: Data validation using Python type annotations
- **uvicorn**: ASGI server
- **requests**: HTTP library for fetching weather data

## License

See [COPYING.txt](../COPYING.txt) for license information.
