"""
Weather data harvester for fetching data from api.met.no
"""
import datetime
import logging
from typing import Optional
import requests
from frcm.datamodel.model import WeatherData, WeatherDataPoint
from frcm.worker.locations import Location

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetNoAPIError(Exception):
    """Exception raised when MET Norway API returns an error"""
    pass


class WeatherHarvester:
    """
    Harvester for weather data from the Norwegian Meteorological Institute (MET Norway) API.
    
    API Documentation: https://api.met.no/weatherapi/locationforecast/2.0/documentation
    
    The API requires a User-Agent header identifying the application.
    """
    
    BASE_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
    USER_AGENT = "firegurad/0.1.0 github.com/isak148/firegurad"
    
    def __init__(self, user_agent: Optional[str] = None):
        """
        Initialize the weather harvester.
        
        Args:
            user_agent: Custom User-Agent string. If None, uses default.
        """
        self.user_agent = user_agent or self.USER_AGENT
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent
        })
    
    def fetch_weather_data(self, location: Location, hours: int = 48) -> WeatherData:
        """
        Fetch weather forecast data for a specific location from api.met.no
        
        Args:
            location: Location object with latitude and longitude
            hours: Number of hours to fetch (default: 48)
            
        Returns:
            WeatherData object containing the weather data points
            
        Raises:
            MetNoAPIError: If the API request fails
        """
        logger.info(f"Fetching weather data for {location.name} (lat={location.latitude}, lon={location.longitude})")
        
        params = {
            'lat': location.latitude,
            'lon': location.longitude,
        }
        
        if location.altitude > 0:
            params['altitude'] = location.altitude
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise MetNoAPIError(f"Failed to fetch weather data for {location.name}: {e}")
        
        try:
            data = response.json()
            weather_data = self._parse_met_response(data, hours)
            logger.info(f"Successfully fetched {len(weather_data.data)} weather data points for {location.name}")
            return weather_data
        except (KeyError, ValueError) as e:
            raise MetNoAPIError(f"Failed to parse MET API response: {e}")
    
    def _parse_met_response(self, data: dict, max_hours: int) -> WeatherData:
        """
        Parse the MET Norway API response into WeatherData format.
        
        The MET API returns data in this structure:
        {
          "properties": {
            "timeseries": [
              {
                "time": "2024-01-01T00:00:00Z",
                "data": {
                  "instant": {
                    "details": {
                      "air_temperature": -5.0,
                      "relative_humidity": 80.0,
                      "wind_speed": 2.5
                    }
                  }
                }
              },
              ...
            ]
          }
        }
        
        Args:
            data: Parsed JSON response from MET API
            max_hours: Maximum number of hours to extract
            
        Returns:
            WeatherData object
        """
        weather_points = []
        timeseries = data.get('properties', {}).get('timeseries', [])
        
        start_time = None
        for entry in timeseries:
            # Parse the timestamp
            timestamp = datetime.datetime.fromisoformat(entry['time'].replace('Z', '+00:00'))
            
            # Track start time to limit to max_hours
            if start_time is None:
                start_time = timestamp
            elif (timestamp - start_time).total_seconds() / 3600 > max_hours:
                break
            
            # Extract weather parameters from the instant details
            instant_details = entry.get('data', {}).get('instant', {}).get('details', {})
            
            # MET API uses these parameter names
            temperature = instant_details.get('air_temperature')
            humidity = instant_details.get('relative_humidity')
            wind_speed = instant_details.get('wind_speed')
            
            # Ensure all required parameters are present
            if temperature is not None and humidity is not None and wind_speed is not None:
                weather_point = WeatherDataPoint(
                    timestamp=timestamp,
                    temperature=float(temperature),
                    humidity=float(humidity),
                    wind_speed=float(wind_speed)
                )
                weather_points.append(weather_point)
        
        if not weather_points:
            raise MetNoAPIError("No valid weather data points found in API response")
        
        return WeatherData(data=weather_points)
