from enum import Enum
from pydantic import BaseModel
from typing import Optional


class FireDangerLevel(str, Enum):
    """Fire danger levels based on time to flashover (TTF)"""
    LOW = "LOW"           # TTF > 60 minutes
    MODERATE = "MODERATE" # 30 < TTF <= 60 minutes
    HIGH = "HIGH"         # 15 < TTF <= 30 minutes
    VERY_HIGH = "VERY_HIGH" # TTF <= 15 minutes

    @classmethod
    def from_ttf(cls, ttf: float) -> 'FireDangerLevel':
        """Determine fire danger level from time to flashover (in minutes)"""
        if ttf > 60:
            return cls.LOW
        elif ttf > 30:
            return cls.MODERATE
        elif ttf > 15:
            return cls.HIGH
        else:
            return cls.VERY_HIGH


class NotificationConfig(BaseModel):
    """Configuration for notification service"""
    enabled: bool = False
    broker_host: str = "localhost"
    broker_port: int = 1883
    topic: str = "frcm/fire-danger"
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: str = "frcm-notifier"
