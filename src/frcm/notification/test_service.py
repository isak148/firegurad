import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from frcm.notification.service import NotificationService, MQTT_AVAILABLE
from frcm.notification.models import FireDangerLevel, NotificationConfig
from frcm.datamodel.model import FireRisk, FireRiskPrediction


class TestNotificationService:
    """Test NotificationService functionality"""
    
    def test_service_disabled_by_default(self):
        """Test that service is disabled by default"""
        config = NotificationConfig(enabled=False)
        service = NotificationService(config)
        assert service.client is None
        assert service.last_danger_level is None
    
    @pytest.mark.skipif(not MQTT_AVAILABLE, reason="paho-mqtt not installed")
    @patch('frcm.notification.service.mqtt.Client')
    def test_service_initialization_with_auth(self, mock_client_class):
        """Test service initialization with authentication"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        config = NotificationConfig(
            enabled=True,
            broker_host="test.broker.com",
            broker_port=1883,
            username="testuser",
            password="testpass"
        )
        
        service = NotificationService(config)
        
        mock_client_class.assert_called_once_with(client_id="frcm-notifier")
        mock_client.username_pw_set.assert_called_once_with("testuser", "testpass")
        mock_client.connect.assert_called_once_with("test.broker.com", 1883, 60)
        mock_client.loop_start.assert_called_once()
    
    @pytest.mark.skipif(not MQTT_AVAILABLE, reason="paho-mqtt not installed")
    @patch('frcm.notification.service.mqtt.Client')
    def test_publish_fire_risk_change_first_time(self, mock_client_class):
        """Test publishing fire risk change for the first time"""
        mock_client = Mock()
        mock_publish_result = Mock()
        mock_publish_result.rc = 0  # MQTT_ERR_SUCCESS
        mock_client.publish.return_value = mock_publish_result
        mock_client_class.return_value = mock_client
        
        config = NotificationConfig(enabled=True)
        service = NotificationService(config)
        
        # Create fire risk prediction with VERY_HIGH danger (TTF = 10 minutes)
        fire_risks = [
            FireRisk(timestamp=datetime(2026, 1, 1, 12, 0), ttf=10.0)
        ]
        prediction = FireRiskPrediction(firerisks=fire_risks)
        
        service.publish_fire_risk_change(prediction)
        
        # Should publish because it's the first notification
        assert mock_client.publish.call_count == 1
        assert service.last_danger_level == FireDangerLevel.VERY_HIGH
    
    @pytest.mark.skipif(not MQTT_AVAILABLE, reason="paho-mqtt not installed")
    @patch('frcm.notification.service.mqtt.Client')
    def test_publish_fire_risk_change_level_changed(self, mock_client_class):
        """Test publishing when danger level changes"""
        mock_client = Mock()
        mock_publish_result = Mock()
        mock_publish_result.rc = 0
        mock_client.publish.return_value = mock_publish_result
        mock_client_class.return_value = mock_client
        
        config = NotificationConfig(enabled=True)
        service = NotificationService(config)
        
        # First prediction: HIGH danger (TTF = 20 minutes)
        prediction1 = FireRiskPrediction(firerisks=[
            FireRisk(timestamp=datetime(2026, 1, 1, 12, 0), ttf=20.0)
        ])
        service.publish_fire_risk_change(prediction1)
        
        # Second prediction: VERY_HIGH danger (TTF = 10 minutes)
        prediction2 = FireRiskPrediction(firerisks=[
            FireRisk(timestamp=datetime(2026, 1, 1, 13, 0), ttf=10.0)
        ])
        service.publish_fire_risk_change(prediction2)
        
        # Should publish twice because level changed
        assert mock_client.publish.call_count == 2
        assert service.last_danger_level == FireDangerLevel.VERY_HIGH
    
    @pytest.mark.skipif(not MQTT_AVAILABLE, reason="paho-mqtt not installed")
    @patch('frcm.notification.service.mqtt.Client')
    def test_no_publish_when_level_unchanged(self, mock_client_class):
        """Test no publishing when danger level remains the same"""
        mock_client = Mock()
        mock_publish_result = Mock()
        mock_publish_result.rc = 0
        mock_client.publish.return_value = mock_publish_result
        mock_client_class.return_value = mock_client
        
        config = NotificationConfig(enabled=True)
        service = NotificationService(config)
        
        # First prediction: HIGH danger (TTF = 20 minutes)
        prediction1 = FireRiskPrediction(firerisks=[
            FireRisk(timestamp=datetime(2026, 1, 1, 12, 0), ttf=20.0)
        ])
        service.publish_fire_risk_change(prediction1)
        
        # Second prediction: Still HIGH danger (TTF = 25 minutes)
        prediction2 = FireRiskPrediction(firerisks=[
            FireRisk(timestamp=datetime(2026, 1, 1, 13, 0), ttf=25.0)
        ])
        service.publish_fire_risk_change(prediction2)
        
        # Should publish only once because level didn't change
        assert mock_client.publish.call_count == 1
    
    def test_no_publish_when_disabled(self):
        """Test that no publishing occurs when service is disabled"""
        config = NotificationConfig(enabled=False)
        service = NotificationService(config)
        
        prediction = FireRiskPrediction(firerisks=[
            FireRisk(timestamp=datetime(2026, 1, 1, 12, 0), ttf=10.0)
        ])
        
        # Should not raise any exception
        service.publish_fire_risk_change(prediction)
        assert service.client is None
    
    @pytest.mark.skipif(not MQTT_AVAILABLE, reason="paho-mqtt not installed")
    @patch('frcm.notification.service.mqtt.Client')
    def test_disconnect(self, mock_client_class):
        """Test disconnecting from broker"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        config = NotificationConfig(enabled=True)
        service = NotificationService(config)
        service.disconnect()
        
        mock_client.loop_stop.assert_called_once()
        mock_client.disconnect.assert_called_once()
