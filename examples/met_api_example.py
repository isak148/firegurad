#!/usr/bin/env python3
"""
Example script demonstrating MET API integration.

This script shows how to use the MET integration to fetch weather data
and compute fire risk for a specific location.
"""

from frcm import fetch_and_transform_weather_data, compute


def main():
    # Bergen coordinates (as an example)
    latitude = 60.39
    longitude = 5.32
    
    print(f"Fetching weather data for Bergen (lat: {latitude}, lon: {longitude})...")
    
    try:
        # Fetch and transform weather data from MET API
        weather_data = fetch_and_transform_weather_data(latitude, longitude)
        
        print(f"Successfully fetched {len(weather_data.data)} data points")
        print(f"First data point: {weather_data.data[0]}")
        
        # Compute fire risk
        print("\nComputing fire risk...")
        fire_risks = compute(weather_data)
        
        print(f"\nFire Risk Results:")
        print(fire_risks)
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
