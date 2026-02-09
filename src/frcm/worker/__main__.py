"""
Command-line interface for the weather data harvester worker
"""
import sys
import logging
from pathlib import Path
from frcm.worker.harvester import WeatherHarvester, MetNoAPIError
from frcm.worker.locations import LocationConfig
from frcm.fireriskmodel.compute import compute

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the worker CLI"""
    if len(sys.argv) < 2:
        print("Usage: python -m frcm.worker <locations.json> [output_dir]")
        print("\nExample locations.json:")
        print("""{
  "locations": [
    {
      "name": "Bergen",
      "latitude": 60.3913,
      "longitude": 5.3221,
      "altitude": 0
    }
  ]
}""")
        sys.exit(1)
    
    locations_file = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
    
    # Validate inputs
    if not locations_file.exists():
        logger.error(f"Locations file not found: {locations_file}")
        sys.exit(1)
    
    if not output_dir.exists():
        logger.error(f"Output directory not found: {output_dir}")
        sys.exit(1)
    
    # Load location configuration
    try:
        config = LocationConfig.from_json_file(str(locations_file))
        logger.info(f"Loaded {len(config.locations)} location(s) from {locations_file}")
    except Exception as e:
        logger.error(f"Failed to load locations configuration: {e}")
        sys.exit(1)
    
    # Initialize harvester
    harvester = WeatherHarvester()
    
    # Process each location
    for location in config.locations:
        try:
            logger.info(f"Processing location: {location.name}")
            
            # Fetch weather data
            weather_data = harvester.fetch_weather_data(location, hours=168)  # 7 days
            logger.info(f"Fetched {len(weather_data.data)} weather data points")
            
            # Save raw weather data
            weather_csv = output_dir / f"{location.name.lower().replace(' ', '_')}_weather.csv"
            weather_data.write_csv(weather_csv)
            logger.info(f"Saved weather data to {weather_csv}")
            
            # Compute fire risk
            logger.info(f"Computing fire risk for {location.name}")
            fire_risk = compute(weather_data)
            
            # Save fire risk prediction
            risk_csv = output_dir / f"{location.name.lower().replace(' ', '_')}_firerisk.csv"
            fire_risk.write_csv(risk_csv)
            logger.info(f"Saved fire risk prediction to {risk_csv}")
            
            logger.info(f"Successfully processed {location.name}\n")
            
        except MetNoAPIError as e:
            logger.error(f"Failed to fetch weather data for {location.name}: {e}")
        except Exception as e:
            logger.error(f"Error processing {location.name}: {e}")
    
    logger.info("Weather harvesting complete!")


if __name__ == "__main__":
    main()
