#!/usr/bin/env python
"""
Example of using the FRCM notification service programmatically.

This example demonstrates how to:
1. Load weather data
2. Compute fire risks
3. Set up the notification service
4. Publish fire danger changes via MQTT
"""

from pathlib import Path
from frcm import WeatherData, compute
from frcm.notification import NotificationService, NotificationConfig

def main():
    # Load weather data
    data_file = Path("bergen_2026_01_09.csv")
    weather_data = WeatherData.read_csv(data_file)
    
    print(f"Loaded {len(weather_data.data)} weather data points")
    
    # Compute fire risks
    fire_risks = compute(weather_data)
    
    print(f"Computed {len(fire_risks.firerisks)} fire risk predictions")
    
    # Configure notification service
    config = NotificationConfig(
        enabled=True,
        broker_host="localhost",  # Use localhost for local testing
        broker_port=1883,
        topic="frcm/example/fire-danger",
        client_id="frcm-example"
    )
    
    # Create and use notification service
    print("\nSetting up notification service...")
    try:
        notifier = NotificationService(config)
        
        # Publish fire risk changes
        notifier.publish_fire_risk_change(fire_risks)
        
        print("✓ Fire danger notification published successfully!")
        print(f"  Topic: {config.topic}")
        print(f"  Latest TTF: {fire_risks.firerisks[-1].ttf:.2f} minutes")
        
        # Clean up
        notifier.disconnect()
        
    except ImportError:
        print("Error: paho-mqtt is not installed.")
        print("Install it with: pip install paho-mqtt")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
