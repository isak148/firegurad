"""
MET Frost API Client for fetching historical weather observations.

This module provides a client for fetching historical weather data from the
MET Frost API (https://frost.met.no/api.html).
"""

import requests
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FrostClient:
    """
    Client for interacting with the MET Frost API.
    
    The Frost API provides access to historical weather observations from MET Norway.
    An API client ID is required. Get yours at https://frost.met.no/auth/requestCredentials.html
    """
    
    BASE_URL = "https://frost.met.no/observations/v0.jsonld"
    
    def __init__(self, client_id: str, user_agent: str = "firegurad/0.1.0 github.com/isak148/firegurad"):
        """
        Initialize the Frost API client.
        
        Args:
            client_id: Frost API client ID (required for authentication)
            user_agent: User-Agent string to identify the application
        """
        self.client_id = client_id
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent
        })
        # Frost API uses HTTP Basic Auth with client_id as username (no password)
        self.session.auth = (self.client_id, '')
    
    def fetch_historical_observations(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
        elements: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Fetch historical weather observations for a specific location and time range.
        
        Args:
            latitude: Latitude coordinate (decimal degrees)
            longitude: Longitude coordinate (decimal degrees)
            start_time: Start of time range (datetime)
            end_time: End of time range (datetime)
            elements: List of weather elements to fetch. Defaults to temperature,
                     humidity, and wind speed.
        
        Returns:
            JSON response from the Frost API as a dictionary
        
        Raises:
            requests.exceptions.RequestException: If the API request fails
            ValueError: If parameters are invalid
        """
        # Validate coordinates
        if not (-90 <= latitude <= 90):
            raise ValueError(f"Invalid latitude: {latitude}. Must be between -90 and 90.")
        if not (-180 <= longitude <= 180):
            raise ValueError(f"Invalid longitude: {longitude}. Must be between -180 and 180.")
        
        # Default elements for fire risk calculation
        if elements is None:
            elements = [
                'air_temperature',
                'relative_humidity',
                'wind_speed'
            ]
        
        # Format timestamps for Frost API (ISO 8601)
        start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
        end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
        
        # Prepare request parameters
        # Frost API uses nearest station to the given coordinates
        params = {
            'referencetime': f'{start_str}/{end_str}',
            'elements': ','.join(elements),
            'geometry': f'nearest(POINT({longitude} {latitude}))',
            'timeresolutions': 'PT1H',  # Hourly data
        }
        
        logger.info(f"Fetching historical weather data for coordinates: lat={latitude}, lon={longitude}")
        logger.info(f"Time range: {start_str} to {end_str}")
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Successfully fetched historical data. Status code: {response.status_code}")
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error("Request to Frost API timed out")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from Frost API: {e}")
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 401:
                raise ValueError("Invalid Frost API client ID. Get one at https://frost.met.no/auth/requestCredentials.html")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from Frost API: {e}")
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
