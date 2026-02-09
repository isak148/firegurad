from frcm.datamodel.model import WeatherData, WeatherDataPoint, FireRisk, FireRiskPrediction
from frcm.fireriskmodel.compute import compute
from frcm.notification import NotificationService, NotificationConfig
from frcm.met_integration.client import METClient
from frcm.met_integration.transform import transform_met_to_weather_data, fetch_and_transform_weather_data
from frcm.fireriskmodel.compute_cached import compute_with_cache
import sys
import os
from pathlib import Path


def console_main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Wrong number of arguments provided! Please provide one reference to a CSV file with weatherdata to compute the fire risk")
        sys.exit(1)

    file = Path(sys.argv[1])
    wd = WeatherData.read_csv(file)

    if len(wd.data) == 0:
        print("Given file did not contain any data points! Please check the input format! Aborting...")
        sys.exit(1)

    print(f"Computing FireRisk for given data in '{file.absolute()}' ({len(wd.data)} datapoints)", end="\n\n")

    # Use cached computation by default
    risks = compute_with_cache(wd)

    # Setup notification service if enabled
    notification_config = NotificationConfig(
        enabled=os.getenv('FRCM_NOTIFICATIONS_ENABLED', 'false').lower() == 'true',
        broker_host=os.getenv('FRCM_MQTT_BROKER_HOST', 'localhost'),
        broker_port=int(os.getenv('FRCM_MQTT_BROKER_PORT', '1883')),
        topic=os.getenv('FRCM_MQTT_TOPIC', 'frcm/fire-danger'),
        username=os.getenv('FRCM_MQTT_USERNAME'),
        password=os.getenv('FRCM_MQTT_PASSWORD'),
        client_id=os.getenv('FRCM_MQTT_CLIENT_ID', 'frcm-notifier')
    )
    
    if notification_config.enabled:
        try:
            notifier = NotificationService(notification_config)
            notifier.publish_fire_risk_change(risks)
            notifier.disconnect()
            print("Fire danger notification published successfully")
        except Exception as e:
            print(f"Warning: Failed to publish notification: {e}")

    if len(sys.argv) == 3:
        output = Path(sys.argv[2])
        risks.write_csv(output)
        print(f"Calculated fire risks written to '{output.absolute()}'")
    else:
        print(risks)

