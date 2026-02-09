# Examples

This directory contains example scripts demonstrating how to use the FRCM notification service.

## notification_example.py

Shows how to programmatically use the notification service to publish fire danger changes.

Usage:
```bash
python examples/notification_example.py
```

## subscriber_example.py

Shows how to subscribe to MQTT notifications and receive fire danger alerts in real-time.

Usage:
```bash
# Connect to localhost (default)
python examples/subscriber_example.py

# Connect to a specific broker
python examples/subscriber_example.py mqtt.example.com 1883 frcm/fire-danger
```

## Requirements

Both examples require `paho-mqtt` to be installed:
```bash
pip install paho-mqtt
```
