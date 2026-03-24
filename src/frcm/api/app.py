"""REST API endpoints for FRCM Fire Risk Calculation Model."""
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import datetime
import os
import logging
import requests

from frcm.datamodel.model import WeatherDataPoint, WeatherData, FireRiskPrediction
from frcm.fireriskmodel.compute import compute
from frcm.database import Database
from .auth import verify_api_key
from .config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="FRCM Fire Risk Calculation API",
    description="API for calculating fire risk predictions (Time to Flashover) from weather data",
    version="0.1.0",
    docs_url="/docs" if not settings.REQUIRE_HTTPS else None,  # Disable docs on HTTP
    redoc_url="/redoc" if not settings.REQUIRE_HTTPS else None,  # Disable redoc on HTTP
)

# Add CORS middleware to allow frontend requests
# WARNING: For production, configure FRCM_CORS_ORIGINS environment variable
# to specify only your frontend domain(s). Never use "*" in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "service": "FRCM Fire Risk Calculation API",
        "version": "0.1.0",
        "status": "running",
        "authentication": "enabled" if settings.is_auth_enabled else "disabled",
        "https": "required" if settings.REQUIRE_HTTPS else "optional"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/locations/search")
async def search_locations(
    q: str = Query(..., min_length=2, description="Location search query"),
    limit: int = Query(8, ge=1, le=20, description="Maximum number of locations to return")
):
    """Search locations from MET/Yr location catalog for use with forecasts."""
    try:
        response = requests.get(
            "https://www.yr.no/api/v0/locations/suggest",
            params={"language": "en", "q": q},
            headers={"User-Agent": "firegurad/0.1.0 github.com/isak148/firegurad"},
            timeout=10,
        )
        response.raise_for_status()

        payload = response.json()
        raw_locations = payload.get("_embedded", {}).get("location", [])

        locations = []
        for loc in raw_locations[:limit]:
            position = loc.get("position", {})
            country = loc.get("country", {})
            region = loc.get("region", {})

            lat = position.get("lat")
            lon = position.get("lon")
            if lat is None or lon is None:
                continue

            locations.append({
                "id": loc.get("id"),
                "name": loc.get("name"),
                "country": country.get("name"),
                "country_code": country.get("id"),
                "region": region.get("name"),
                "latitude": lat,
                "longitude": lon,
                "url_path": loc.get("urlPath"),
            })

        return {
            "query": q,
            "count": len(locations),
            "locations": locations,
        }
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Location search request timed out",
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Location search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Location search failed: {str(e)}",
        )

@app.post("/calculate", response_model=FireRiskPrediction, dependencies=[Depends(verify_api_key)])
async def calculate_fire_risk(weather_data: WeatherData):
    """
    Calculate fire risk predictions from weather data.
    
    Args:
        weather_data: Weather data containing temperature, humidity, wind speed, and timestamps
        
    Returns:
        Fire risk predictions with time to flashover (TTF) values
        
    Raises:
        HTTPException: If calculation fails or data is invalid
    """
    try:
        # Validate that we have data points
        if not weather_data.data or len(weather_data.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Weather data must contain at least one data point"
            )
        
        # Perform fire risk calculation
        result = compute(weather_data)
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input data: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {str(e)}"
        )

@app.get("/api-info")
async def api_info():
    """Get API information and usage instructions."""
    return {
        "endpoints": {
            "/": "API information",
            "/health": "Health check",
            "/locations/search": "Search locations from MET/Yr (GET)",
            "/calculate": "Calculate fire risk (POST) - requires authentication",
            "/historical": "Get historical weather data and fire risk (GET)",
            "/historical/stored": "Get database-stored historical data grouped by day (GET)",
            "/api-info": "API information and usage",
            "/docs": "Interactive API documentation (Swagger UI)" + (" - HTTPS only" if settings.REQUIRE_HTTPS else ""),
            "/redoc": "Alternative API documentation" + (" - HTTPS only" if settings.REQUIRE_HTTPS else "")
        },
        "authentication": {
            "enabled": settings.is_auth_enabled,
            "method": "API Key",
            "header": "X-API-Key",
            "description": "Include your API key in the X-API-Key header"
        },
        "input_format": {
            "weather_data": {
                "data": [
                    {
                        "timestamp": "ISO 8601 datetime string",
                        "temperature": "float (Celsius)",
                        "humidity": "float (relative humidity, 0-1)",
                        "wind_speed": "float (m/s)"
                    }
                ]
            }
        },
        "output_format": {
            "firerisks": [
                {
                    "timestamp": "ISO 8601 datetime string",
                    "ttf": "float (time to flashover in minutes)"
                }
            ]
        }
    }


@app.get("/historical")
async def get_historical_data(
    latitude: float = Query(..., description="Latitude coordinate", ge=-90, le=90),
    longitude: float = Query(..., description="Longitude coordinate", ge=-180, le=180),
    days: int = Query(7, description="Number of days of historical data", ge=1, le=30)
):
    """
    Get historical weather data and fire risk predictions for a location.
    
    This endpoint fetches historical weather observations from the MET Frost API
    and calculates fire risk predictions.
    
    Note: Requires FRCM_FROST_CLIENT_ID environment variable to be set.
    Get your Frost API client ID at: https://frost.met.no/auth/requestCredentials.html
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        days: Number of days of historical data (default: 7)
        
    Returns:
        Historical weather data with fire risk predictions
        
    Raises:
        HTTPException: If data cannot be fetched or Frost API is not configured
    """
    try:
        # Check if Frost API client ID is configured
        frost_client_id = os.environ.get('FRCM_FROST_CLIENT_ID')
        if not frost_client_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Historical data service not configured. FRCM_FROST_CLIENT_ID environment variable is required. Get your API key at https://frost.met.no/auth/requestCredentials.html"
            )
        
        # Calculate time range
        end_time = datetime.datetime.now(datetime.timezone.utc)
        start_time = end_time - datetime.timedelta(days=days)
        
        logger.info(f"Fetching historical data for lat={latitude}, lon={longitude}, days={days}")
        
        # Fetch historical data from Frost API
        from frcm.met_integration.frost_client import FrostClient
        from frcm.met_integration.transform import transform_frost_to_weather_data
        
        with FrostClient(client_id=frost_client_id) as frost_client:
            frost_response = frost_client.fetch_historical_observations(
                latitude=latitude,
                longitude=longitude,
                start_time=start_time,
                end_time=end_time
            )
            
            # Transform to WeatherData format
            weather_data = transform_frost_to_weather_data(frost_response)
        
        # Calculate fire risk
        fire_risk_prediction = compute(weather_data)
        
        # Format response with both weather data and fire risk
        response = {
            "latitude": latitude,
            "longitude": longitude,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "weather_data": [
                {
                    "timestamp": point.timestamp.isoformat(),
                    "temperature": point.temperature,
                    "humidity": point.humidity,
                    "wind_speed": point.wind_speed
                }
                for point in weather_data.data
            ],
            "fire_risk": [
                {
                    "timestamp": risk.timestamp.isoformat(),
                    "ttf": risk.ttf
                }
                for risk in fire_risk_prediction.firerisks
            ]
        }
        
        return response
        
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching historical data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch historical data: {str(e)}"
        )


@app.get("/historical/stored")
async def get_stored_historical_data(
    days: int = Query(7, description="Number of days of stored historical data", ge=1, le=90),
    location_name: Optional[str] = Query(None, description="Optional location filter")
):
    """Get stored historical weather snapshots from local database, grouped by day."""
    try:
        db_path = os.environ.get('FRCM_DATABASE_PATH', 'frcm_cache.db')
        db = Database(db_path)
        snapshots = db.get_historical_weather_data(location_name=location_name)
        db.close()

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        cutoff = now_utc - datetime.timedelta(days=days)

        grouped: dict[str, list[dict]] = {}

        for snapshot in snapshots:
            prediction = compute(snapshot)

            for weather_point, risk_point in zip(snapshot.data, prediction.firerisks):
                point_time = weather_point.timestamp
                if point_time.tzinfo is None:
                    point_time = point_time.replace(tzinfo=datetime.timezone.utc)

                if point_time < cutoff:
                    continue

                day_key = point_time.date().isoformat()
                grouped.setdefault(day_key, []).append({
                    "timestamp": point_time.isoformat(),
                    "temperature": weather_point.temperature,
                    "humidity": weather_point.humidity,
                    "wind_speed": weather_point.wind_speed,
                    "ttf": risk_point.ttf,
                })

        days_payload = []
        for day_key in sorted(grouped.keys()):
            entries = sorted(grouped[day_key], key=lambda entry: entry["timestamp"])
            days_payload.append({
                "date": day_key,
                "entries": entries,
            })

        total_entries = sum(len(day["entries"]) for day in days_payload)

        return {
            "location_name": location_name,
            "days": days_payload,
            "total_days": len(days_payload),
            "total_entries": total_entries,
        }
    except Exception as e:
        logger.error(f"Error fetching stored historical data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch stored historical data: {str(e)}"
        )
