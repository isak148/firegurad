import json
import logging
from typing import Optional
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

from frcm.notification.models import FireDangerLevel, NotificationConfig
from frcm.datamodel.model import FireRiskPrediction

logger = logging.getLogger(__name__)


class NotificationService:
    """Service to publish fire danger notifications via MQTT"""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
        self.client: Optional[mqtt.Client] = None
        self.last_danger_level: Optional[FireDangerLevel] = None
        
        if config.enabled and not MQTT_AVAILABLE:
            raise ImportError(
                "paho-mqtt is not installed. Install it with: pip install paho-mqtt"
            )
        
        if config.enabled:
            self._setup_mqtt_client()
    
    def _setup_mqtt_client(self):
        """Initialize and configure MQTT client"""
        self.client = mqtt.Client(client_id=self.config.client_id)
        
        if self.config.username and self.config.password:
            self.client.username_pw_set(self.config.username, self.config.password)
        
        try:
            self.client.connect(self.config.broker_host, self.config.broker_port, 60)
            self.client.loop_start()
            logger.info(f"Connected to MQTT broker at {self.config.broker_host}:{self.config.broker_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    def publish_fire_risk_change(self, prediction: FireRiskPrediction):
        """
        Analyze fire risk prediction and publish notification if danger level changes
        
        Args:
            prediction: FireRiskPrediction containing fire risk data
        """
        if not self.config.enabled or not prediction.firerisks:
            return
        
        # Get the most recent fire risk
        latest_risk = prediction.firerisks[-1]
        current_danger_level = FireDangerLevel.from_ttf(latest_risk.ttf)
        
        # Check if danger level has changed
        if self.last_danger_level is None or current_danger_level != self.last_danger_level:
            self._publish_notification(latest_risk.timestamp, current_danger_level, latest_risk.ttf)
            self.last_danger_level = current_danger_level
    
    def _publish_notification(self, timestamp: datetime, danger_level: FireDangerLevel, ttf: float):
        """
        Publish notification message to MQTT broker
        
        Args:
            timestamp: Time of the fire risk assessment
            danger_level: Current fire danger level
            ttf: Time to flashover in minutes
        """
        if not self.client:
            return
        
        message = {
            "timestamp": timestamp.isoformat(),
            "danger_level": danger_level.value,
            "ttf_minutes": round(ttf, 2),
            "message": self._get_danger_message(danger_level)
        }
        
        try:
            result = self.client.publish(
                self.config.topic,
                json.dumps(message),
                qos=1,
                retain=True
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published fire danger change: {danger_level.value} (TTF: {ttf:.2f} min)")
            else:
                logger.error(f"Failed to publish message: {result.rc}")
        except Exception as e:
            logger.error(f"Error publishing notification: {e}")
    
    def _get_danger_message(self, level: FireDangerLevel) -> str:
        """Get human-readable message for danger level"""
        messages = {
            FireDangerLevel.LOW: "Fire danger is LOW - conditions are safe",
            FireDangerLevel.MODERATE: "Fire danger is MODERATE - exercise caution",
            FireDangerLevel.HIGH: "Fire danger is HIGH - be vigilant",
            FireDangerLevel.VERY_HIGH: "Fire danger is VERY HIGH - take immediate precautions"
        }
        return messages.get(level, "Unknown danger level")
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Disconnected from MQTT broker")
