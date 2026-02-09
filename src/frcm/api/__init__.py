"""API module for FRCM Fire Risk Calculation Model."""
# Import the main FastAPI app from prediction module
# This allows uvicorn to find the app at frcm.api:app
from frcm.api.prediction import app

__all__ = ["app"]
