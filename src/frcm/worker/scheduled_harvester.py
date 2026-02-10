"""
Scheduled weather data harvester that fetches data at regular intervals.

This module provides a scheduled worker that automatically fetches weather data
(temperature, humidity, wind speed) from the MET API at configurable intervals.
"""
import time
import logging
import signal
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from decouple import config

from frcm.worker.harvester import WeatherHarvester, MetNoAPIError
from frcm.worker.locations import LocationConfig
from frcm.fireriskmodel.compute import compute

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScheduledHarvester:
    """
    Scheduled worker that fetches weather data at regular intervals.
    
    This worker fetches temperature, humidity, and wind speed data from the
    MET API and computes fire risk predictions on a schedule.
    """
    
    def __init__(
        self,
        locations_file: str,
        output_dir: str = ".",
        update_interval: int = 60,
        forecast_hours: int = 48
    ):
        """
        Initialize the scheduled harvester.
        
        Args:
            locations_file: Path to locations JSON configuration file
            output_dir: Directory to save output files
            update_interval: Update interval in seconds (default: 60 = 1 minute)
            forecast_hours: Number of hours to fetch in forecast (default: 48)
        """
        self.locations_file = Path(locations_file)
        self.output_dir = Path(output_dir)
        self.update_interval = update_interval
        self.forecast_hours = forecast_hours
        self.running = False
        
        # Validate inputs
        if not self.locations_file.exists():
            raise FileNotFoundError(f"Locations file not found: {self.locations_file}")
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load location configuration
        self.config = LocationConfig.from_json_file(str(self.locations_file))
        logger.info(f"Loaded {len(self.config.locations)} location(s) from {self.locations_file}")
        
        # Initialize harvester
        self.harvester = WeatherHarvester()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def fetch_and_process(self):
        """
        Fetch weather data and compute fire risk for all configured locations.
        
        This method fetches temperature, humidity, and wind speed from the MET API
        for each location and computes fire risk predictions.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{timestamp}] Starting data fetch cycle...")
        
        for location in self.config.locations:
            try:
                logger.info(f"Fetching weather data for {location.name}")
                
                # Fetch weather data (temperature, humidity, wind speed)
                weather_data = self.harvester.fetch_weather_data(
                    location, 
                    hours=self.forecast_hours
                )
                
                # Log what we fetched
                if weather_data.data:
                    first_point = weather_data.data[0]
                    logger.info(
                        f"  Temperature: {first_point.temperature}°C, "
                        f"Humidity: {first_point.humidity}%, "
                        f"Wind Speed: {first_point.wind_speed} m/s"
                    )
                
                logger.info(f"Fetched {len(weather_data.data)} weather data points")
                
                # Save raw weather data
                weather_csv = self.output_dir / f"{location.name.lower().replace(' ', '_')}_weather.csv"
                weather_data.write_csv(weather_csv)
                logger.info(f"Saved weather data to {weather_csv}")
                
                # Compute fire risk
                fire_risk = compute(weather_data)
                
                # Save fire risk prediction
                risk_csv = self.output_dir / f"{location.name.lower().replace(' ', '_')}_firerisk.csv"
                fire_risk.write_csv(risk_csv)
                logger.info(f"Saved fire risk prediction to {risk_csv}")
                
            except MetNoAPIError as e:
                logger.error(f"Failed to fetch weather data for {location.name}: {e}")
            except Exception as e:
                logger.error(f"Error processing {location.name}: {e}", exc_info=True)
        
        logger.info(f"Completed data fetch cycle at {timestamp}")
    
    def run(self):
        """
        Run the scheduled harvester continuously.
        
        Fetches weather data at the configured interval until stopped.
        """
        self.running = True
        logger.info(f"Starting scheduled harvester (update interval: {self.update_interval}s)")
        logger.info(f"Monitoring {len(self.config.locations)} location(s)")
        logger.info(f"Output directory: {self.output_dir.absolute()}")
        logger.info("Press Ctrl+C to stop")
        
        while self.running:
            try:
                self.fetch_and_process()
                
                if self.running:
                    logger.info(f"Waiting {self.update_interval} seconds until next update...")
                    time.sleep(self.update_interval)
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                if self.running:
                    logger.info(f"Retrying in {self.update_interval} seconds...")
                    time.sleep(self.update_interval)
        
        logger.info("Scheduled harvester stopped")
    
    def stop(self):
        """Stop the scheduled harvester."""
        self.running = False


def main():
    """Main entry point for the scheduled harvester CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Scheduled weather data harvester for MET API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  # Fetch data every minute (default)
  python -m frcm.worker.scheduled_harvester locations.json
  
  # Fetch data every 5 minutes
  python -m frcm.worker.scheduled_harvester locations.json --interval 300
  
  # Custom output directory
  python -m frcm.worker.scheduled_harvester locations.json --output /path/to/output

Environment variables (loaded from .env):
  FRCM_WORKER_UPDATE_INTERVAL - Update interval in seconds (default: 60)
  FRCM_WORKER_FORECAST_HOURS  - Hours to fetch in forecast (default: 48)
  FRCM_WORKER_OUTPUT_DIR      - Output directory (default: current directory)
        """
    )
    
    parser.add_argument(
        'locations',
        help='Path to locations.json configuration file'
    )
    parser.add_argument(
        '--output',
        default=config('FRCM_WORKER_OUTPUT_DIR', default='.'),
        help='Output directory for CSV files (default: current directory)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=config('FRCM_WORKER_UPDATE_INTERVAL', default=60, cast=int),
        help='Update interval in seconds (default: 60)'
    )
    parser.add_argument(
        '--forecast-hours',
        type=int,
        default=config('FRCM_WORKER_FORECAST_HOURS', default=48, cast=int),
        help='Number of hours to fetch in forecast (default: 48)'
    )
    
    args = parser.parse_args()
    
    try:
        harvester = ScheduledHarvester(
            locations_file=args.locations,
            output_dir=args.output,
            update_interval=args.interval,
            forecast_hours=args.forecast_hours
        )
        harvester.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
