"""
MET API Client for fetching weather data from Meteorologisk institutt.

This module provides a client for fetching weather forecast data from the
MET Locationforecast API (https://api.met.no/weatherapi/locationforecast/2.0/).
"""

import requests
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class METClient:
    """
    Client for interacting with the MET Locationforecast API.
    
    The MET API requires a proper User-Agent header as per their terms of service.
    See: https://api.met.no/doc/TermsOfService
    """
    
    BASE_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
    
    def __init__(self, user_agent: str = "firegurad/0.1.0 github.com/isak148/firegurad"):
        """
        Initialize the MET API client.
        
        Args:
            user_agent: User-Agent string to identify the application.
                       MET requires this to comply with their terms of service.
        """
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent
        })
    
    def fetch_weather_data(self, latitude: float, longitude: float, altitude: int = 0) -> Dict[str, Any]:
        """
        Fetch weather data for a specific location.
        
        Args:
            latitude: Latitude coordinate (decimal degrees)
            longitude: Longitude coordinate (decimal degrees)
            altitude: Altitude in meters above sea level (optional)
        
        Returns:
            JSON response from the MET API as a dictionary
        
        Raises:
            requests.exceptions.RequestException: If the API request fails
            ValueError: If coordinates are invalid
        """
        # Validate coordinates
        if not (-90 <= latitude <= 90):
            raise ValueError(f"Invalid latitude: {latitude}. Must be between -90 and 90.")
        if not (-180 <= longitude <= 180):
            raise ValueError(f"Invalid longitude: {longitude}. Must be between -180 and 180.")
        
        # Prepare request parameters
        params = {
            'lat': latitude,
            'lon': longitude,
            'altitude': altitude
        }
        
        logger.info(f"Fetching weather data for coordinates: lat={latitude}, lon={longitude}, alt={altitude}")
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Successfully fetched weather data. Status code: {response.status_code}")
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error("Request to MET API timed out")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from MET API: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from MET API: {e}")
            raise
    
    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
