"""
Location configuration for weather data harvesting
"""
from typing import List
from pydantic import BaseModel


class Location(BaseModel):
    """Represents a geographic location for weather monitoring"""
    name: str
    latitude: float
    longitude: float
    altitude: int = 0  # meters above sea level
    
    def __str__(self) -> str:
        return f"{self.name} (lat={self.latitude}, lon={self.longitude})"


class LocationConfig(BaseModel):
    """Configuration containing multiple locations to monitor"""
    locations: List[Location]
    
    @classmethod
    def from_json_file(cls, filepath: str) -> 'LocationConfig':
        """Load location configuration from JSON file"""
        import json
        from pathlib import Path
        
        with open(Path(filepath), 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    def save_to_json_file(self, filepath: str):
        """Save location configuration to JSON file"""
        import json
        from pathlib import Path
        
        with open(Path(filepath), 'w') as f:
            json.dump(self.model_dump(), f, indent=2)
