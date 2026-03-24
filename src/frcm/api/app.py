"""REST API endpoints for FRCM Fire Risk Calculation Model."""
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import List, Optional
import datetime
import os
import logging
from pathlib import Path
import requests
from pydantic import BaseModel, Field

from frcm.datamodel.model import WeatherDataPoint, WeatherData, FireRiskPrediction
from frcm.fireriskmodel.compute import compute
from frcm.database import Database
from .auth import verify_api_key
from .config import settings

logger = logging.getLogger(__name__)
bearer_auth = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


def _is_valid_email(email: str) -> bool:
    """Basic email validation without external dependency."""
    if "@" not in email:
        return False
    local, _, domain = email.partition("@")
    return bool(local and domain and "." in domain)


def _resolve_database_path() -> str:
    """Resolve database path with persistent default and backward compatibility."""
    configured_path = os.environ.get("FRCM_DATABASE_PATH")
    if configured_path:
        return configured_path

    legacy_path = Path("frcm_cache.db")
    if legacy_path.exists():
        return str(legacy_path)

    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "frcm_cache.db")


def _get_database() -> Database:
    return Database(_resolve_database_path())


async def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_auth),
) -> dict:
    """Resolve authenticated user from bearer session token."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    db = _get_database()
    try:
        user = db.get_user_by_session_token(credentials.credentials)
    finally:
        db.close()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
        )

    return user

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


@app.post("/auth/register")
async def register_user(payload: RegisterRequest):
    """Create a user account with name, email and password."""
    if not _is_valid_email(payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format",
        )

    db = _get_database()
    try:
        user = db.create_user(payload.name, payload.email, payload.password)
        token = db.create_user_session(user["id"])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    finally:
        db.close()

    return {
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "created_at": user["created_at"],
        },
        "token": token,
        "token_type": "Bearer",
    }


@app.post("/auth/login")
async def login_user(payload: LoginRequest):
    """Login with email and password and receive bearer token."""
    db = _get_database()
    try:
        user = db.verify_user_credentials(payload.email, payload.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        token = db.create_user_session(user["id"])
    finally:
        db.close()

    return {
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "created_at": user["created_at"],
        },
        "token": token,
        "token_type": "Bearer",
    }


@app.get("/auth/me")
async def get_me(user: dict = Depends(get_authenticated_user)):
    """Return profile of currently authenticated user."""
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "created_at": user["created_at"],
    }


@app.get("/locations/search")
async def search_locations(
    q: str = Query(..., min_length=2, description="Location search query"),
    limit: int = Query(8, ge=1, le=20, description="Maximum number of locations to return"),
    country_code: Optional[str] = Query("NO", min_length=2, max_length=2, description="Optional country code filter, defaults to NO")
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

        wanted_country = country_code.upper() if country_code else None
        locations = []
        for loc in raw_locations[:limit]:
            position = loc.get("position", {})
            country = loc.get("country", {})
            region = loc.get("region", {})
            loc_country_code = country.get("id")

            if wanted_country and loc_country_code and loc_country_code.upper() != wanted_country:
                continue

            lat = position.get("lat")
            lon = position.get("lon")
            if lat is None or lon is None:
                continue

            locations.append({
                "id": loc.get("id"),
                "name": loc.get("name"),
                "country": country.get("name"),
                "country_code": loc_country_code,
                "region": region.get("name"),
                "latitude": lat,
                "longitude": lon,
                "url_path": loc.get("urlPath"),
            })

            if len(locations) >= limit:
                break

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
            "/auth/register": "Create user account with name/email/password (POST)",
            "/auth/login": "Login and receive bearer session token (POST)",
            "/auth/me": "Get current authenticated user profile (GET)",
            "/locations/search": "Search locations from MET/Yr (GET)",
            "/risk/current": "Get current fire risk TTF from backend model (GET)",
            "/risk/forecast": "Get forecast fire risk TTF series from backend model (GET)",
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


@app.get("/risk/current")
async def get_current_risk(
    latitude: float = Query(..., description="Latitude coordinate", ge=-90, le=90),
    longitude: float = Query(..., description="Longitude coordinate", ge=-180, le=180),
):
    """Get current TTF using backend weather preprocessing and fire risk model."""
    try:
        from frcm.met_integration.client import METClient
        from frcm.met_integration.transform import transform_met_to_weather_data

        with METClient() as met_client:
            met_response = met_client.fetch_weather_data(latitude=latitude, longitude=longitude)

        weather_data = transform_met_to_weather_data(met_response)
        fire_risk_prediction = compute(weather_data)

        if not fire_risk_prediction.firerisks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No fire risk data available for this location",
            )

        current = fire_risk_prediction.firerisks[0]
        return {
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": current.timestamp.isoformat(),
            "ttf": current.ttf,
            "model": "frcm-backend",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to fetch weather data for current risk: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error fetching current risk data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch current risk data: {str(e)}",
        )


@app.get("/risk/forecast")
async def get_forecast_risk(
    latitude: float = Query(..., description="Latitude coordinate", ge=-90, le=90),
    longitude: float = Query(..., description="Longitude coordinate", ge=-180, le=180),
    days: int = Query(7, description="Number of forecast days", ge=1, le=10),
):
    """Get forecast weather and TTF series using backend weather preprocessing and model."""
    try:
        from frcm.met_integration.client import METClient
        from frcm.met_integration.transform import transform_met_to_weather_data

        with METClient() as met_client:
            met_response = met_client.fetch_weather_data(latitude=latitude, longitude=longitude)

        weather_data = transform_met_to_weather_data(met_response)
        fire_risk_prediction = compute(weather_data)

        if not fire_risk_prediction.firerisks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No forecast fire risk data available for this location",
            )

        cutoff = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)

        weather_payload = []
        fire_risk_payload = []

        for point, risk in zip(weather_data.data, fire_risk_prediction.firerisks):
            point_time = point.timestamp
            if point_time.tzinfo is None:
                point_time = point_time.replace(tzinfo=datetime.timezone.utc)
            if point_time > cutoff:
                continue

            weather_payload.append(
                {
                    "timestamp": point_time.isoformat(),
                    "temperature": point.temperature,
                    "humidity": point.humidity,
                    "wind_speed": point.wind_speed,
                }
            )
            fire_risk_payload.append(
                {
                    "timestamp": point_time.isoformat(),
                    "ttf": risk.ttf,
                }
            )

        return {
            "latitude": latitude,
            "longitude": longitude,
            "days": days,
            "weather_data": weather_payload,
            "fire_risk": fire_risk_payload,
            "model": "frcm-backend",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to fetch weather data for forecast risk: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error fetching forecast risk data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch forecast risk data: {str(e)}",
        )


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
        db = Database(_resolve_database_path())
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
