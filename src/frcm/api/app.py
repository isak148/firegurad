"""REST API endpoints for FRCM Fire Risk Calculation Model."""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List
import datetime

from frcm.datamodel.model import WeatherDataPoint, WeatherData, FireRiskPrediction
from frcm.fireriskmodel.compute import compute
from .auth import verify_api_key
from .config import settings

app = FastAPI(
    title="FRCM Fire Risk Calculation API",
    description="API for calculating fire risk predictions (Time to Flashover) from weather data",
    version="0.1.0",
    docs_url="/docs" if not settings.REQUIRE_HTTPS else None,  # Disable docs on HTTP
    redoc_url="/redoc" if not settings.REQUIRE_HTTPS else None,  # Disable redoc on HTTP
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
            "/calculate": "Calculate fire risk (POST) - requires authentication",
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
