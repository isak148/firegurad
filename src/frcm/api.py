"""
REST API for fire risk prediction.
Provides endpoints for third-party developers to get fire danger predictions.
"""
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime
import requests
from pathlib import Path

from frcm.datamodel.model import WeatherData, WeatherDataPoint, FireRisk
from frcm.fireriskmodel.compute import compute


app = FastAPI(
    title="Fire Risk Prediction API",
    description="API for calculating fire risk (time to flashover) based on weather data",
    version="0.1.0"
)


class CoordinateRequest(BaseModel):
    """Request model for coordinate-based fire risk prediction."""
    latitude: float = Field(..., description="Latitude coordinate", ge=-90, le=90)
    longitude: float = Field(..., description="Longitude coordinate", ge=-180, le=180)
    days_ahead: int = Field(default=7, description="Number of days to predict ahead", ge=1, le=14)


class FireRiskResponse(BaseModel):
    """Response model for fire risk prediction."""
    timestamp: datetime.datetime
    ttf: float = Field(..., description="Time to flashover (fire risk indicator)")


class FireRiskPredictionResponse(BaseModel):
    """Response model containing all fire risk predictions."""
    latitude: float
    longitude: float
    predictions: List[FireRiskResponse]
    generated_at: datetime.datetime


def fetch_weather_data(latitude: float, longitude: float, days_ahead: int) -> WeatherData:
    """
    Fetch weather data from met.no API for the given coordinates.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        days_ahead: Number of days to fetch data for
        
    Returns:
        WeatherData object containing the weather forecast
        
    Raises:
        HTTPException: If weather data cannot be fetched
    """
    # met.no API endpoint for location forecast
    url = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
    
    headers = {
        "User-Agent": "FireRisk/0.1.0 github.com/isak148/firegurad"
    }
    
    params = {
        "lat": latitude,
        "lon": longitude
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Unable to fetch weather data: {str(e)}"
        )
    
    # Parse weather data from met.no response
    weather_points = []
    
    try:
        timeseries = data.get("properties", {}).get("timeseries", [])
        
        for entry in timeseries:
            timestamp_str = entry.get("time")
            timestamp = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            
            # Only include data within the requested time range
            max_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days_ahead)
            if timestamp > max_time:
                break
            
            instant_data = entry.get("data", {}).get("instant", {}).get("details", {})
            
            # Extract required weather parameters
            temperature = instant_data.get("air_temperature")
            humidity = instant_data.get("relative_humidity")
            wind_speed = instant_data.get("wind_speed")
            
            # Skip if any required data is missing
            if temperature is None or humidity is None or wind_speed is None:
                continue
            
            weather_point = WeatherDataPoint(
                timestamp=timestamp,
                temperature=temperature,
                humidity=humidity,
                wind_speed=wind_speed
            )
            weather_points.append(weather_point)
        
        if not weather_points:
            raise HTTPException(
                status_code=404,
                detail="No weather data available for the specified location and time range"
            )
        
        return WeatherData(data=weather_points)
        
    except (KeyError, ValueError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing weather data: {str(e)}"
        )


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": "Fire Risk Prediction API",
        "version": "0.1.0",
        "description": "Calculate fire risk (time to flashover) for any location",
        "endpoints": {
            "predict": "/api/v1/predict"
        }
    }


@app.post("/api/v1/predict", response_model=FireRiskPredictionResponse)
def predict_fire_risk(
    request: CoordinateRequest,
    use_sample_data: bool = Query(False, description="Use sample weather data instead of fetching from API (for testing)")
):
    """
    Predict fire risk (time to flashover) for the given coordinates.
    
    This endpoint fetches weather forecast data for the specified location
    and calculates the fire risk indicator (TTF - Time To Flashover) for
    multiple days ahead.
    
    Args:
        request: Coordinate request with latitude, longitude, and days_ahead
        use_sample_data: If True, uses sample data instead of fetching from API (for testing)
        
    Returns:
        FireRiskPredictionResponse with predictions for the requested period
        
    Raises:
        HTTPException: If weather data cannot be fetched or processed
    """
    # Use sample data for testing if requested
    if use_sample_data:
        # Load sample data from the example CSV
        sample_csv = Path(__file__).parent.parent.parent / "bergen_2026_01_09.csv"
        if sample_csv.exists():
            weather_data = WeatherData.read_csv(sample_csv)
        else:
            raise HTTPException(
                status_code=500,
                detail="Sample data file not found"
            )
    else:
        # Fetch weather data for the coordinates
        weather_data = fetch_weather_data(
            request.latitude,
            request.longitude,
            request.days_ahead
        )
    
    # Compute fire risk using the existing fire risk model
    fire_risk_prediction = compute(weather_data)
    
    # Convert to API response format
    predictions = [
        FireRiskResponse(
            timestamp=risk.timestamp,
            ttf=risk.ttf
        )
        for risk in fire_risk_prediction.firerisks
    ]
    
    return FireRiskPredictionResponse(
        latitude=request.latitude,
        longitude=request.longitude,
        predictions=predictions,
        generated_at=datetime.datetime.now(datetime.timezone.utc)
    )


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
