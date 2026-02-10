#!/usr/bin/env python3
"""
Example script for the scheduled weather data harvester.

This script demonstrates how to set up and run the scheduled harvester
to fetch temperature, humidity, and wind speed from the MET API every minute.
"""

from frcm.worker.scheduled_harvester import ScheduledHarvester


def main():
    """
    Example: Run the scheduled harvester with custom configuration.
    
    This will fetch weather data every 60 seconds (1 minute) for all
    locations defined in locations_example.json and save the results
    to the 'output' directory.
    """
    
    print("="*70)
    print("FireGuard - Scheduled Weather Data Harvester Example")
    print("="*70)
    print()
    print("This example will:")
    print("  1. Load locations from 'locations_example.json'")
    print("  2. Fetch temperature, humidity, and wind speed from MET API")
    print("  3. Update every 60 seconds (1 minute)")
    print("  4. Save weather data and fire risk predictions to 'output/' directory")
    print()
    print("Press Ctrl+C to stop the harvester")
    print("="*70)
    print()
    
    try:
        # Create the scheduled harvester
        harvester = ScheduledHarvester(
            locations_file="locations_example.json",
            output_dir="./output",
            update_interval=60,      # Update every 60 seconds (1 minute)
            forecast_hours=48        # Fetch 48-hour forecast
        )
        
        # Run the harvester (this will run continuously)
        harvester.run()
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print()
        print("Please ensure 'locations_example.json' exists in the current directory.")
        print("You can create one with the following content:")
        print("""
{
  "locations": [
    {
      "name": "Bergen",
      "latitude": 60.3913,
      "longitude": 5.3221,
      "altitude": 12
    }
  ]
}
        """)
        return 1
    
    except KeyboardInterrupt:
        print()
        print("Harvester stopped by user")
        return 0
    
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
