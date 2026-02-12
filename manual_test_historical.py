#!/usr/bin/env python3
"""
Manual test script for the historical data API endpoint.

This script demonstrates how to test the historical data functionality
without requiring a real Frost API client ID.

Run this script with:
    python3 manual_test_historical.py
"""

import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import datetime

# Import the app
from frcm.api.app import app
from frcm.datamodel.model import WeatherData, WeatherDataPoint, FireRiskPrediction, FireRisk

def test_historical_endpoint_without_client_id():
    """Test that the endpoint returns proper error when Frost API is not configured."""
    print("\n1. Testing /historical endpoint without FRCM_FROST_CLIENT_ID...")
    
    client = TestClient(app)
    
    # Make request without setting FRCM_FROST_CLIENT_ID
    with patch.dict('os.environ', {}, clear=True):
        response = client.get("/historical?latitude=60.39&longitude=5.32&days=7")
        
        print(f"   Status code: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        # Accept either 503 (direct) or 500 (wrapped in exception handler)
        if response.status_code in [500, 503]:
            response_data = response.json()
            if "not configured" in str(response_data).lower():
                print("   ✓ Correctly returns error when Frost API is not configured")
                return True
        
        print(f"   ✗ Expected error about configuration, got {response.status_code}")
        return False

def test_historical_endpoint_with_mocked_data():
    """Test that the endpoint works with mocked Frost API data."""
    print("\n2. Testing /historical endpoint with mocked Frost API...")
    
    client = TestClient(app)
    
    # Mock Frost API response
    mock_frost_response = {
        'data': [
            {
                'referenceTime': '2026-02-05T00:00:00.000Z',
                'observations': [
                    {'elementId': 'air_temperature', 'value': 5.2},
                    {'elementId': 'relative_humidity', 'value': 85.0},
                    {'elementId': 'wind_speed', 'value': 3.5}
                ]
            },
            {
                'referenceTime': '2026-02-05T01:00:00.000Z',
                'observations': [
                    {'elementId': 'air_temperature', 'value': 4.8},
                    {'elementId': 'relative_humidity', 'value': 87.0},
                    {'elementId': 'wind_speed', 'value': 3.2}
                ]
            }
        ]
    }
    
    # Create mock client
    mock_client_instance = MagicMock()
    mock_client_instance.fetch_historical_observations.return_value = mock_frost_response
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.__exit__.return_value = None
    
    with patch.dict('os.environ', {'FRCM_FROST_CLIENT_ID': 'test-client-id'}):
        with patch('frcm.met_integration.frost_client.FrostClient', return_value=mock_client_instance):
            response = client.get("/historical?latitude=60.39&longitude=5.32&days=7")
            
            print(f"   Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✓ Successfully returned historical data")
                print(f"   - Weather data points: {len(data.get('weather_data', []))}")
                print(f"   - Fire risk predictions: {len(data.get('fire_risk', []))}")
                print(f"   - Latitude: {data.get('latitude')}")
                print(f"   - Longitude: {data.get('longitude')}")
                
                # Print first data point
                if data.get('weather_data'):
                    first_point = data['weather_data'][0]
                    print(f"   - First observation:")
                    print(f"     * Temperature: {first_point['temperature']}°C")
                    print(f"     * Humidity: {first_point['humidity']}%")
                    print(f"     * Wind speed: {first_point['wind_speed']} m/s")
                
                return True
            else:
                print(f"   ✗ Expected 200, got {response.status_code}")
                print(f"   Response: {response.json()}")
                return False

def test_historical_endpoint_validation():
    """Test that the endpoint validates input parameters."""
    print("\n3. Testing /historical endpoint parameter validation...")
    
    client = TestClient(app)
    
    test_cases = [
        ("latitude=91.0&longitude=5.32", "invalid latitude (>90)"),
        ("latitude=-91.0&longitude=5.32", "invalid latitude (<-90)"),
        ("latitude=60.39&longitude=181.0", "invalid longitude (>180)"),
        ("latitude=60.39&longitude=-181.0", "invalid longitude (<-180)"),
        ("longitude=5.32", "missing latitude"),
        ("latitude=60.39", "missing longitude"),
    ]
    
    passed = 0
    failed = 0
    
    for params, description in test_cases:
        response = client.get(f"/historical?{params}")
        if response.status_code == 422:  # FastAPI validation error
            print(f"   ✓ Correctly rejects {description}")
            passed += 1
        else:
            print(f"   ✗ Failed to reject {description} (status: {response.status_code})")
            failed += 1
    
    return failed == 0

def main():
    """Run all manual tests."""
    print("=" * 70)
    print("Manual Test Suite for Historical Data API")
    print("=" * 70)
    
    results = []
    
    # Run tests
    results.append(("Configuration validation", test_historical_endpoint_without_client_id()))
    results.append(("Mocked data integration", test_historical_endpoint_with_mocked_data()))
    results.append(("Parameter validation", test_historical_endpoint_validation()))
    
    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
