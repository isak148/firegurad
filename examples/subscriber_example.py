#!/usr/bin/env python
"""
Example MQTT subscriber for FRCM fire danger notifications.

This script subscribes to MQTT topics and displays fire danger alerts.
"""

import json
import sys

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Error: paho-mqtt is not installed.")
    print("Install it with: pip install paho-mqtt")
    sys.exit(1)


def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print("✓ Connected to MQTT broker")
        topic = userdata.get("topic", "frcm/fire-danger")
        client.subscribe(topic)
        print(f"✓ Subscribed to topic: {topic}")
        print("\nWaiting for fire danger notifications...\n")
    else:
        print(f"✗ Connection failed with code {rc}")


def on_message(client, userdata, msg):
    """Callback when a message is received"""
    try:
        payload = json.loads(msg.payload.decode())
        
        # Display notification
        print("=" * 60)
        print("🔥 FIRE DANGER NOTIFICATION")
        print("=" * 60)
        print(f"Timestamp:     {payload['timestamp']}")
        print(f"Danger Level:  {payload['danger_level']}")
        print(f"TTF (minutes): {payload['ttf_minutes']}")
        print(f"Message:       {payload['message']}")
        print("=" * 60)
        print()
        
    except json.JSONDecodeError:
        print(f"Received non-JSON message: {msg.payload.decode()}")
    except Exception as e:
        print(f"Error processing message: {e}")


def main():
    # Configuration
    broker_host = "localhost"
    broker_port = 1883
    topic = "frcm/fire-danger"
    
    # Allow command-line arguments
    if len(sys.argv) > 1:
        broker_host = sys.argv[1]
    if len(sys.argv) > 2:
        broker_port = int(sys.argv[2])
    if len(sys.argv) > 3:
        topic = sys.argv[3]
    
    print(f"FRCM Fire Danger Notification Subscriber")
    print(f"Broker: {broker_host}:{broker_port}")
    print(f"Topic:  {topic}\n")
    
    # Create MQTT client
    client = mqtt.Client(userdata={"topic": topic})
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        # Connect to broker
        client.connect(broker_host, broker_port, 60)
        
        # Start the loop
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n\nDisconnecting...")
        client.disconnect()
        print("Goodbye!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
