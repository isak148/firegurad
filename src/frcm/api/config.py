"""Configuration management for FRCM API."""
from decouple import config
from typing import List

class Settings:
    """API settings loaded from environment variables."""
    
    # API Keys - comma-separated list of valid API keys
    API_KEYS: List[str] = config("FRCM_API_KEYS", default="", cast=lambda v: [s.strip() for s in v.split(",") if s.strip()])
    
    # Server configuration
    HOST: str = config("FRCM_HOST", default="0.0.0.0")
    PORT: int = config("FRCM_PORT", default=8443, cast=int)
    
    # SSL/TLS configuration
    SSL_CERT_PATH: str = config("FRCM_SSL_CERT", default="./ssl/cert.pem")
    SSL_KEY_PATH: str = config("FRCM_SSL_KEY", default="./ssl/key.pem")
    
    # Security settings
    REQUIRE_HTTPS: bool = config("FRCM_REQUIRE_HTTPS", default=True, cast=bool)
    
    @property
    def is_auth_enabled(self) -> bool:
        """Check if authentication is enabled (has API keys configured)."""
        return len(self.API_KEYS) > 0

settings = Settings()
