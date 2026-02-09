"""Authentication middleware for FRCM API."""
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from .config import settings

# API Key header for authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify the API key provided in the request header.
    
    Args:
        api_key: The API key from the X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If authentication is enabled and key is invalid or missing
    """
    # If no API keys are configured, allow all requests (authentication disabled)
    if not settings.is_auth_enabled:
        return "authentication_disabled"
    
    # If authentication is enabled, require a valid API key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
        )
    
    if api_key not in settings.API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    return api_key
