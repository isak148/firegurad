#!/usr/bin/env python3
"""
Example script demonstrating how to use the weather harvester worker programmatically.

This script shows how to:
1. Create locations
2. Fetch weather data (or use mock data)
3. Compute fire risk
4. Save results

Note: This example uses mock data since actual API calls require internet access.
In production, the WeatherHarvester will fetch real data from api.met.no
"""

import datetime
from pathlib import Path
from frcm.worker.locations import Location, LocationConfig
from frcm.datamodel.model import WeatherData, WeatherDataPoint
from frcm.fireriskmodel.compute import compute


def create_mock_weather_data(location: Location, hours: int = 48) -> WeatherData:
    """
    Create mock weather data for testing purposes.
    
    In production, use WeatherHarvester.fetch_weather_data() instead:
        harvester = WeatherHarvester()
        weather_data = harvester.fetch_weather_data(location, hours=48)
    """
    print(f"Creating mock weather data for {location.name}...")
    
    # Generate mock data points (one per hour)
    base_time = datetime.datetime.now(datetime.timezone.utc)
    data_points = []
    
    for hour in range(hours):
        timestamp = base_time + datetime.timedelta(hours=hour)
        
        # Simple sinusoidal temperature variation
        import math
        temp = -5.0 + 10.0 * math.sin(hour * math.pi / 12)
        humidity = 70.0 + 15.0 * math.sin(hour * math.pi / 18)
        wind_speed = 2.0 + 1.5 * math.sin(hour * math.pi / 24)
        
        data_point = WeatherDataPoint(
            timestamp=timestamp,
            temperature=temp,
            humidity=humidity,
            wind_speed=wind_speed
        )
        data_points.append(data_point)
    
    return WeatherData(data=data_points)


def main():
    """Main example function"""
    print("="*60)
    print("Weather Harvester Worker - Example Usage")
    print("="*60)
    print()
    
    # Create output directory
    output_dir = Path("example_output")
    output_dir.mkdir(exist_ok=True)
    print(f"Output directory: {output_dir.absolute()}")
    print()
    
    # Define locations to monitor
    locations = [
        Location(name="Bergen", latitude=60.3913, longitude=5.3221, altitude=12),
        Location(name="Oslo", latitude=59.9139, longitude=10.7522, altitude=23),
    ]
    
    # Save location configuration
    config = LocationConfig(locations=locations)
    config_file = output_dir / "locations.json"
    config.save_to_json_file(str(config_file))
    print(f"Saved location configuration to: {config_file}")
    print()
    
    # Process each location
    for location in locations:
        print("-" * 60)
        print(f"Processing: {location.name}")
        print(f"Coordinates: lat={location.latitude}, lon={location.longitude}")
        print()
        
        # In production with internet access, use:
        # from frcm.worker.harvester import WeatherHarvester
        # harvester = WeatherHarvester()
        # weather_data = harvester.fetch_weather_data(location, hours=48)
        
        # For this example, use mock data:
        weather_data = create_mock_weather_data(location, hours=48)
        print(f"Generated {len(weather_data.data)} weather data points")
        
        # Save weather data
        weather_file = output_dir / f"{location.name.lower()}_weather.csv"
        weather_data.write_csv(weather_file)
        print(f"Saved weather data to: {weather_file}")
        
        # Compute fire risk
        print(f"Computing fire risk...")
        fire_risk = compute(weather_data)
        print(f"Computed {len(fire_risk.firerisks)} fire risk predictions")
        
        # Save fire risk predictions
        risk_file = output_dir / f"{location.name.lower()}_firerisk.csv"
        fire_risk.write_csv(risk_file)
        print(f"Saved fire risk to: {risk_file}")
        
        # Display sample results
        print()
        print("Sample results (first 5 entries):")
        print("Timestamp                     | TTF (hours)")
        print("-" * 60)
        for i, risk in enumerate(fire_risk.firerisks[:5]):
            print(f"{risk.timestamp.isoformat():29} | {risk.ttf:6.2f}")
        print()
    
    print("="*60)
    print("Example completed successfully!")
    print(f"All files saved to: {output_dir.absolute()}")
    print("="*60)


if __name__ == "__main__":
    main()
