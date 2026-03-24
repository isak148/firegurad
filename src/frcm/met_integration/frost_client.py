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
    SOURCES_URL = "https://frost.met.no/sources/v0.jsonld"
    AVAILABLE_TS_URL = "https://frost.met.no/observations/availableTimeSeries/v0.jsonld"
    
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
        
        # Frost referencetime is most reliable at hour precision.
        # Example from Frost docs: 2010-01-01T12
        start_str = start_time.strftime('%Y-%m-%dT%H')
        end_str = end_time.strftime('%Y-%m-%dT%H')
        
        logger.info(f"Fetching historical weather data for coordinates: lat={latitude}, lon={longitude}")
        logger.info(f"Time range: {start_str} to {end_str}")

        merged_data: List[Dict[str, Any]] = []
        for element in elements:
            element_payload = self._fetch_observations_for_element(
                latitude=latitude,
                longitude=longitude,
                start_str=start_str,
                end_str=end_str,
                element=element,
            )
            merged_data.extend(element_payload.get('data', []))

        return {
            "data": merged_data,
        }

    def _fetch_observations_for_element(
        self,
        latitude: float,
        longitude: float,
        start_str: str,
        end_str: str,
        element: str,
    ) -> Dict[str, Any]:
        candidate_sources = self._resolve_candidate_source_ids(
            latitude=latitude,
            longitude=longitude,
            start_str=start_str,
            end_str=end_str,
            element=element,
        )

        last_error_detail = ""
        for source_id in candidate_sources:
            for use_hourly_resolution in (True, False):
                params = {
                    'referencetime': f'{start_str}/{end_str}',
                    'elements': element,
                    'sources': source_id,
                }
                if use_hourly_resolution:
                    params['timeresolutions'] = 'PT1H'

                try:
                    response = self.session.get(self.BASE_URL, params=params, timeout=30)
                    response.raise_for_status()
                    logger.info(
                        f"Fetched element={element} from source={source_id} "
                        f"(hourly={use_hourly_resolution}). Status code: {response.status_code}"
                    )
                    return response.json()
                except requests.exceptions.Timeout:
                    logger.error("Request to Frost API timed out")
                    raise
                except requests.exceptions.HTTPError as e:
                    response_text = self._extract_response_text(e)
                    status_code = e.response.status_code if e.response is not None else None

                    if status_code == 401:
                        raise ValueError("Invalid Frost API client ID. Get one at https://frost.met.no/auth/requestCredentials.html")

                    # 412 means this source/parameter combination has no matching series.
                    if status_code == 412:
                        last_error_detail = response_text or str(e)
                        logger.warning(
                            f"No timeseries for element={element}, source={source_id}, "
                            f"hourly={use_hourly_resolution}. Trying fallback."
                        )
                        continue

                    if response_text:
                        raise ValueError(f"Frost API error: {response_text}")
                    raise
                except requests.exceptions.RequestException as e:
                    logger.error(f"Error fetching data from Frost API: {e}")
                    raise

        detail = last_error_detail or (
            f"No available Frost time series found for element={element} in requested time range"
        )
        raise ValueError(f"Frost API error: {detail}")

    def _resolve_nearest_source_id(self, latitude: float, longitude: float, element: Optional[str] = None) -> str:
        """Resolve nearest Frost station source ID for given coordinates."""
        params = {
            'geometry': f'nearest(POINT({longitude} {latitude}))',
            'types': 'SensorSystem',
        }
        if element:
            params['elements'] = element

        try:
            response = self.session.get(self.SOURCES_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.Timeout:
            logger.error("Request to Frost sources API timed out")
            raise
        except requests.exceptions.HTTPError as e:
            response_text = ""
            if hasattr(e, 'response') and e.response is not None:
                try:
                    response_text = e.response.text
                except Exception:
                    response_text = ""
            logger.error(f"HTTP error from Frost sources API: {e}. Response body: {response_text}")
            if response_text:
                raise ValueError(f"Frost sources API error: {response_text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from Frost sources API: {e}")
            raise

        sources = payload.get('data', [])
        if not sources:
            raise ValueError("No nearby Frost source found for this location")

        source_id = sources[0].get('id')
        if not source_id:
            raise ValueError("Nearest Frost source response did not include source id")

        return source_id

    def _resolve_candidate_source_ids(
        self,
        latitude: float,
        longitude: float,
        start_str: str,
        end_str: str,
        element: str,
    ) -> List[str]:
        """Resolve candidate source IDs that likely have data for given element/time range."""
        candidate_ids: List[str] = []

        params = {
            'referencetime': f'{start_str}/{end_str}',
            'elements': element,
            'geometry': f'nearest(POINT({longitude} {latitude}))',
        }

        try:
            response = self.session.get(self.AVAILABLE_TS_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            for row in payload.get('data', []):
                source_id = row.get('sourceId') or row.get('source') or row.get('id')
                if not source_id:
                    continue
                source_id = str(source_id).split(':')[0]
                if source_id not in candidate_ids:
                    candidate_ids.append(source_id)
            if candidate_ids:
                return candidate_ids[:10]
        except requests.exceptions.RequestException as e:
            logger.warning(f"availableTimeSeries lookup failed for element={element}: {e}")

        # Fallback: at least try nearest source endpoint result.
        return [self._resolve_nearest_source_id(latitude=latitude, longitude=longitude, element=element)]

    @staticmethod
    def _extract_response_text(error: requests.exceptions.HTTPError) -> str:
        if hasattr(error, 'response') and error.response is not None:
            try:
                return error.response.text
            except Exception:
                return ""
        return ""
    
    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
