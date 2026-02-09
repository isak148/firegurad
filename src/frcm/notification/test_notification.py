import pytest
from datetime import datetime
from frcm.notification.models import FireDangerLevel, NotificationConfig


class TestFireDangerLevel:
    """Test FireDangerLevel classification"""
    
    def test_low_danger_level(self):
        """Test LOW danger level for TTF > 60 minutes"""
        level = FireDangerLevel.from_ttf(61.0)
        assert level == FireDangerLevel.LOW
        
        level = FireDangerLevel.from_ttf(100.0)
        assert level == FireDangerLevel.LOW
    
    def test_moderate_danger_level(self):
        """Test MODERATE danger level for 30 < TTF <= 60 minutes"""
        level = FireDangerLevel.from_ttf(60.0)
        assert level == FireDangerLevel.MODERATE
        
        level = FireDangerLevel.from_ttf(45.0)
        assert level == FireDangerLevel.MODERATE
        
        level = FireDangerLevel.from_ttf(31.0)
        assert level == FireDangerLevel.MODERATE
    
    def test_high_danger_level(self):
        """Test HIGH danger level for 15 < TTF <= 30 minutes"""
        level = FireDangerLevel.from_ttf(30.0)
        assert level == FireDangerLevel.HIGH
        
        level = FireDangerLevel.from_ttf(20.0)
        assert level == FireDangerLevel.HIGH
        
        level = FireDangerLevel.from_ttf(16.0)
        assert level == FireDangerLevel.HIGH
    
    def test_very_high_danger_level(self):
        """Test VERY_HIGH danger level for TTF <= 15 minutes"""
        level = FireDangerLevel.from_ttf(15.0)
        assert level == FireDangerLevel.VERY_HIGH
        
        level = FireDangerLevel.from_ttf(10.0)
        assert level == FireDangerLevel.VERY_HIGH
        
        level = FireDangerLevel.from_ttf(5.0)
        assert level == FireDangerLevel.VERY_HIGH


class TestNotificationConfig:
    """Test NotificationConfig model"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = NotificationConfig()
        assert config.enabled is False
        assert config.broker_host == "localhost"
        assert config.broker_port == 1883
        assert config.topic == "frcm/fire-danger"
        assert config.username is None
        assert config.password is None
        assert config.client_id == "frcm-notifier"
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = NotificationConfig(
            enabled=True,
            broker_host="mqtt.example.com",
            broker_port=8883,
            topic="custom/topic",
            username="user",
            password="pass",
            client_id="custom-client"
        )
        assert config.enabled is True
        assert config.broker_host == "mqtt.example.com"
        assert config.broker_port == 8883
        assert config.topic == "custom/topic"
        assert config.username == "user"
        assert config.password == "pass"
        assert config.client_id == "custom-client"
