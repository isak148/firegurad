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


class FrostAPIError(Exception):
    """Structured Frost API error with status/message/reason fields."""

    def __init__(self, status_code: int, message: str, reason: str = ""):
        self.status_code = status_code
        self.message = message
        self.reason = reason
        detail = f"Frost API returned status code {status_code}. Message: {message}"
        if reason:
            detail = f"{detail}. Reason: {reason}"
        super().__init__(detail)


class FrostClient:
    """
    Client for interacting with the MET Frost API.
    
    The Frost API provides access to historical weather observations from MET Norway.
    An API client ID is required. Get yours at https://frost.met.no/auth/requestCredentials.html
    """
    
    BASE_URL = "https://frost.met.no/observations/v0.jsonld"
    SOURCES_URL = "https://frost.met.no/sources/v0.jsonld"
    AVAILABLE_TS_URL = "https://frost.met.no/observations/availableTimeSeries/v0.jsonld"

    ELEMENT_QUERY_VARIANTS = {
        "air_temperature": [
            "air_temperature",
            "mean(air_temperature PT1H)",
        ],
        "relative_humidity": [
            "relative_humidity",
            "mean(relative_humidity PT1H)",
        ],
        "wind_speed": [
            "wind_speed",
            "mean(wind_speed PT1H)",
        ],
    }
    
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

    def _request_frost_json(
        self,
        endpoint: str,
        parameters: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Request Frost endpoint using explicit endpoint/parameter style from MET examples.

        Equivalent to:
            r = requests.get(endpoint, parameters, auth=(client_id, ''))
            json = r.json()
            if r.status_code != 200: parse json['error']['message'/'reason']
        """
        response = self.session.get(
            endpoint,
            params=parameters,
            auth=(self.client_id, ''),
            timeout=timeout,
        )

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if response.status_code == 200:
            return payload

        error_obj = payload.get('error', {}) if isinstance(payload, dict) else {}
        message = error_obj.get('message') or response.reason or 'Unknown error'
        reason = error_obj.get('reason') or ''
        raise FrostAPIError(status_code=response.status_code, message=message, reason=reason)

    def _fetch_observations_for_element(
        self,
        latitude: float,
        longitude: float,
        start_str: str,
        end_str: str,
        element: str,
    ) -> Dict[str, Any]:
        last_error_detail = ""

        query_variants = self.ELEMENT_QUERY_VARIANTS.get(element, [element])
        logger.debug(f"Trying {len(query_variants)} variants for element={element}: {query_variants}")

        for requested_element in query_variants:
            candidate_sources = self._resolve_candidate_source_ids(
                latitude=latitude,
                longitude=longitude,
                start_str=start_str,
                end_str=end_str,
                element=requested_element,
            )

            logger.debug(f"Resolved {len(candidate_sources)} sources for element={requested_element}: {candidate_sources[:3]}...")

            for source_id in candidate_sources:
                for use_hourly_resolution in (True, False):
                    params = {
                        'referencetime': f'{start_str}/{end_str}',
                        'elements': requested_element,
                        'sources': source_id,
                    }
                    if use_hourly_resolution:
                        params['timeresolutions'] = 'PT1H'

                    try:
                        payload = self._request_frost_json(self.BASE_URL, params)
                        logger.info(
                            f"Fetched requested_element={requested_element} "
                            f"(canonical={element}) from source={source_id} "
                            f"(hourly={use_hourly_resolution}). Status code: 200"
                        )
                        return payload
                    except requests.exceptions.Timeout:
                        logger.error("Request to Frost API timed out")
                        raise
                    except FrostAPIError as e:
                        if e.status_code == 401:
                            raise ValueError("Invalid Frost API client ID. Get one at https://frost.met.no/auth/requestCredentials.html")

                        # 412 means this source/parameter combination has no matching series.
                        if e.status_code == 412:
                            last_error_detail = str(e)
                            logger.warning(
                                f"No timeseries for requested_element={requested_element} "
                                f"(canonical={element}), source={source_id}, "
                                f"hourly={use_hourly_resolution}. Trying fallback."
                            )
                            continue

                        raise ValueError(str(e))
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Error fetching data from Frost API: {e}")
                        raise

        detail = last_error_detail or (
            f"No available Frost time series found for element={element} in requested time range"
        )
        if element == 'wind_speed':
            logger.warning(
                f"WIND FALLBACK TRIGGERED: No Frost wind_speed series found at lat={latitude}, lon={longitude}, range={start_str}/{end_str}. "
                f"Proceeding with fallback wind_speed imputation (0.0) in transform layer."
            )
            return {"data": []}

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
            payload = self._request_frost_json(self.SOURCES_URL, params)
        except requests.exceptions.Timeout:
            logger.error("Request to Frost sources API timed out")
            raise
        except FrostAPIError as e:
            logger.error(f"HTTP error from Frost sources API: {e}")
            if e.status_code == 401:
                raise ValueError("Invalid Frost API client ID. Get one at https://frost.met.no/auth/requestCredentials.html")
            raise ValueError(str(e))
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

        # Strategy 1: Query availableTimeSeries with specific element
        params = {
            'referencetime': f'{start_str}/{end_str}',
            'elements': element,
            'geometry': f'nearest(POINT({longitude} {latitude}))',
        }

        try:
            payload = self._request_frost_json(self.AVAILABLE_TS_URL, params)
            for row in payload.get('data', []):
                source_id = row.get('sourceId') or row.get('source') or row.get('id')
                if not source_id:
                    continue
                source_id = str(source_id).split(':')[0]
                if source_id not in candidate_ids:
                    candidate_ids.append(source_id)
            if candidate_ids:
                logger.info(f"Found {len(candidate_ids)} sources with element={element}")
                return candidate_ids[:10]
        except (requests.exceptions.RequestException, FrostAPIError) as e:
            logger.warning(f"availableTimeSeries lookup failed for element={element}: {e}")

        # Strategy 2 (for locations with sparse element coverage): Query for all available sources
        # at this location, then try the element on those generic sources
        logger.info(f"Falling back to generic source lookup without element filter for {element}")
        params_generic = {
            'referencetime': f'{start_str}/{end_str}',
            'geometry': f'nearest(POINT({longitude} {latitude}))',
        }

        try:
            payload = self._request_frost_json(self.AVAILABLE_TS_URL, params_generic)
            for row in payload.get('data', []):
                source_id = row.get('sourceId') or row.get('source') or row.get('id')
                if not source_id:
                    continue
                source_id = str(source_id).split(':')[0]
                if source_id not in candidate_ids:
                    candidate_ids.append(source_id)
            if candidate_ids:
                logger.info(f"Found {len(candidate_ids)} generic nearby sources (no element filter)")
                return candidate_ids[:10]
        except (requests.exceptions.RequestException, FrostAPIError) as e:
            logger.warning(f"Generic availableTimeSeries lookup also failed: {e}")

        # Strategy 3: Fallback: at least try nearest source endpoint result.
        logger.info(f"Using nearest source fallback for element={element}")
        return [self._resolve_nearest_source_id(latitude=latitude, longitude=longitude, element=element)]

    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
